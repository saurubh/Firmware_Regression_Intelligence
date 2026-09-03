"""
Firmware Regression Intelligence (FRI)

Investigation Engine

Coordinates firmware regression investigation for one Git repo
or a multi-repo BIOS workspace (submodules / pin-sets).
"""

from __future__ import annotations

import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

from fri.analyzer.bisect_planner import BisectPlanner
from fri.analyzer.candidate_engine import CandidateEngine
from fri.analyzer.diff_analyzer import DiffAnalyzer
from fri.analyzer.module_analyzer import ModuleAnalyzer
from fri.analyzer.triage import BootTriage
from fri.classifier.classifier import FirmwareClassifier
from fri.collector.git_collector import GitCollector, has_source_paths
from fri.collector.run_cache import InvestigationCache
from fri.collector.workspace import WorkspaceCollector
from fri.config import config
from fri.constants import HIGH_CONFIDENCE, OUTPUT_DIR
from fri.logger import logger
from fri.models import (
    Commit,
    RegressionCandidate,
    RegressionReport,
    RegressionStatistics,
    RepoWindow,
    WorkspacePlan,
)
from fri.parser.commit_parser import CommitParser
from fri.utils.progress import ProgressBar


@dataclass
class AnalysisOptions:
    workers: int = 1
    skip_binary_only_diffs: bool = True


class InvestigationEngine:
    def __init__(self, repo: str | None = None) -> None:
        self.repo = repo
        self.parser = CommitParser()
        self.classifier = FirmwareClassifier()
        self.diff = DiffAnalyzer()
        self.candidates = CandidateEngine()
        self.modules = ModuleAnalyzer()
        self.bisect = BisectPlanner()
        self.triage = BootTriage()
        self.workspace = WorkspaceCollector()

    def investigate(self, good, bad, failure, **kwargs) -> RegressionReport:
        if not self.repo:
            raise RuntimeError("Single-repo investigate() needs a repository path.")
        plan = WorkspacePlan(
            workspace=self.repo,
            good_label=str(good),
            bad_label=str(bad),
            windows=[
                RepoWindow(
                    name=_repo_label(self.repo),
                    path=self.repo,
                    good_sha=str(good),
                    bad_sha=str(bad),
                )
            ],
        )
        return self.investigate_plan(plan, failure, **kwargs)

    def investigate_workspace(self, workspace, good, bad, failure, **kwargs) -> RegressionReport:
        logger.info("Resolving the same good/bad tags in every Git repo (then gitlinks)...")
        plan = self.workspace.plan_from_workspace(workspace, good, bad)
        moved = sum(1 for item in plan.deltas if item.status == "changed")
        logger.info("Pin-set: %d repo(s) moved of %d listed.", moved, len(plan.deltas))
        return self.investigate_plan(plan, failure, **kwargs)

    def investigate_manifest(self, manifest, failure, **kwargs) -> RegressionReport:
        plan = self.workspace.plan_from_manifest(manifest)
        return self.investigate_plan(plan, failure, **kwargs)

    def investigate_gitman(self, gitman, good, bad, failure, **kwargs) -> RegressionReport:
        logger.info("Reading gitman.yml names, then walking the tree for other Git repos...")
        plan = self.workspace.plan_from_gitman(gitman, good, bad)
        moved = sum(1 for item in plan.deltas if item.status == "changed")
        logger.info("Pin-set: %d repo(s) moved of %d listed.", moved, len(plan.deltas))
        return self.investigate_plan(plan, failure, **kwargs)

    def investigate_plan(
        self,
        plan: WorkspacePlan,
        failure,
        workers: int | None = None,
        fast: bool = False,
        fresh: bool = False,
        cache_dir: str | None = None,
    ) -> RegressionReport:
        started = time.perf_counter()
        failure_key = failure.lower()
        profile = config.get_failure_profile(failure_key)
        options = _analysis_options(workers=workers, fast=fast)
        cache = InvestigationCache(
            Path(cache_dir) if cache_dir else OUTPUT_DIR / "cache",
            plan,
            failure_key,
        )
        if fresh:
            cache.reset()
        cache.load()

        report = RegressionReport(
            good_sha=plan.good_label,
            bad_sha=plan.bad_label,
            failure=failure_key,
            profile_description=profile.description if profile else "",
            related_topics=self._related_topics(failure_key),
            covered_topics=config.failure_names,
            workspace=plan.workspace,
            repo_deltas=plan.deltas,
        )

        all_commits = []
        regression_candidates: list[RegressionCandidate] = []
        count_by_repo: dict[str, int] = {}
        windows = [window for window in plan.windows if window.good_sha != window.bad_sha]
        logger.info(
            "Analyzing %d repo window(s): %s",
            len(windows),
            ", ".join(window.name for window in windows) or "(none)",
        )
        if options.workers > 1:
            logger.info("Parallel workers: %d", options.workers)
        if len(windows) == 1:
            logger.warning(
                "Only 1 repo window (%s). Nested clones such as Edk2, Intel, "
                "and Lenovo/* are not in this run. Use "
                "`fri investigate --gitman <tree>/gitman.yml` (not --repo / "
                "not --workspace alone) and FRI 2.6+.",
                windows[0].name,
            )

        for repo_index, window in enumerate(windows, start=1):
            logger.info(
                "Repo %d/%d: %s  %s..%s",
                repo_index,
                len(windows),
                window.name,
                window.good_sha[:8],
                window.bad_sha[:8],
            )
            try:
                collector = GitCollector(window.path)
                commits = collector.get_commits(window.good_sha, window.bad_sha)
            except Exception as exc:
                logger.warning("Skipping %s: %s", window.name, exc)
                continue
            count_by_repo[window.name] = len(commits)
            logger.info(
                "%s: %d commits between pins (not the grand total yet)",
                window.name,
                len(commits),
            )
            hits: list[tuple[Commit, RegressionCandidate]] = []
            pending_commits: list[Commit] = []
            for commit in commits:
                cached = cache.get(window.name, commit.sha)
                if cached is not None:
                    hits.append(cached)
                else:
                    pending_commits.append(commit)
            if hits:
                logger.info(
                    "  %s: resuming %d cached, %d still to analyze",
                    window.name,
                    len(hits),
                    len(pending_commits),
                )
                for cached_commit, cached_candidate in hits:
                    regression_candidates.append(cached_candidate)
                    all_commits.append(cached_commit)
            bar = ProgressBar(f"{repo_index}/{len(windows)} {window.name}", len(commits))
            done_count = len(hits)
            if done_count:
                bar.update(done_count, f"resumed {done_count}")
            if options.workers <= 1:
                for index, commit in enumerate(pending_commits, start=1):
                    try:
                        result = self._process_commit(
                            window,
                            collector,
                            commit,
                            failure_key,
                            options,
                            bar=bar,
                            index=done_count + index,
                        )
                        if result is None:
                            continue
                        commit, candidate = result
                        cache.put(window.name, commit, candidate)
                        regression_candidates.append(candidate)
                        all_commits.append(commit)
                    except Exception as exc:
                        logger.warning(
                            "Skipping %s %s: %s",
                            window.name,
                            commit.short_sha,
                            exc,
                        )
                        bar.tick(f"skip {commit.short_sha}")
            else:
                with ThreadPoolExecutor(max_workers=options.workers) as pool:
                    futures = {
                        pool.submit(
                            self._process_commit,
                            window,
                            collector,
                            commit,
                            failure_key,
                            options,
                        ): commit
                        for commit in pending_commits
                    }
                    pending = set(futures)
                    while pending:
                        finished, pending = wait(
                            pending,
                            timeout=15,
                            return_when=FIRST_COMPLETED,
                        )
                        if not finished:
                            waiting = [futures[item].short_sha for item in pending]
                            logger.info(
                                "Still analyzing %d %s commit(s): %s",
                                len(waiting),
                                window.name,
                                ", ".join(waiting[:8]),
                            )
                            continue
                        for future in finished:
                            commit = futures[future]
                            try:
                                result = future.result()
                                if result is None:
                                    bar.tick(f"skip {commit.short_sha}")
                                    continue
                                done_commit, candidate = result
                                cache.put(window.name, done_commit, candidate)
                                regression_candidates.append(candidate)
                                all_commits.append(done_commit)
                                bar.tick(f"done {done_commit.short_sha}")
                            except Exception as exc:
                                logger.warning(
                                    "Skipping %s %s: %s",
                                    window.name,
                                    commit.short_sha,
                                    exc,
                                )
                                bar.tick(f"skip {commit.short_sha}")
            bar.close()
            logger.info("  %s: finished %d commits", window.name, len(commits))

        logger.info(
            "Grand total: %d commits across %d repo(s)%s",
            sum(count_by_repo.values()),
            len(count_by_repo),
            (
                " — " + ", ".join(f"{name}={n}" for name, n in count_by_repo.items())
                if count_by_repo
                else ""
            ),
        )
        if sum(1 for c in regression_candidates if "Binary-only" in " ".join(c.evidence)) > 0:
            logger.info(
                "Binary-only commits scored from paths/message only (diff skipped for speed)."
            )

        for delta in report.repo_deltas:
            delta.commit_count = count_by_repo.get(delta.name, 0)

        report.commits = all_commits
        ranked = self.candidates.rank(regression_candidates)
        minimum = int(config.settings.get("analysis", {}).get("minimum_confidence", 25))
        visible = self.candidates.filter_noise(ranked, minimum_confidence=minimum)
        report.candidates = visible or ranked[:10]
        report.modules = self.modules.analyze(report.candidates)
        report.triage = self.triage.plan(report.candidates)
        report.bisect = self.bisect.plan(
            good_sha=plan.good_label,
            bad_sha=plan.bad_label,
            candidates=report.candidates,
            failure=failure_key,
            workspace=plan.workspace,
            deltas=plan.deltas,
        )

        hazard_commits = sum(1 for item in ranked if item.hazards)
        high = sum(1 for item in ranked if item.confidence >= HIGH_CONFIDENCE)
        report.statistics = RegressionStatistics(
            total_commits=len(all_commits),
            filtered_commits=max(len(ranked) - len(report.candidates), 0),
            candidate_commits=len(report.candidates),
            module_count=len(report.modules),
            execution_time=round(time.perf_counter() - started, 3),
            hazard_commits=hazard_commits,
            high_confidence=high,
            repo_count=len({window.name for window in plan.windows if window.good_sha != window.bad_sha}),
        )
        return report

    def _process_commit(
        self,
        window: RepoWindow,
        collector: GitCollector,
        commit: Commit,
        failure_key: str,
        options: AnalysisOptions,
        bar: ProgressBar | None = None,
        index: int | None = None,
    ) -> tuple[Commit, RegressionCandidate] | None:
        if bar is not None and index is not None:
            bar.update(index, f"files {commit.short_sha}")

        commit.repo_name = window.name
        commit.repo_path = window.path
        if not commit.files:
            commit.files = collector.changed_paths(commit)

        skip_diff = (
            options.skip_binary_only_diffs
            and commit.files
            and not has_source_paths(commit.files)
        )

        if bar is not None and index is not None:
            bar.update(
                index,
                f"diff {commit.short_sha} ({len(commit.files)} files)",
            )

        if skip_diff:
            diff_text = ""
        else:
            heartbeat = None
            if bar is not None and index is not None:
                heartbeat = lambda detail, i=index, progress=bar: progress.update(i, detail)
            diff_text = collector.get_diff(commit, heartbeat=heartbeat)

        diff = self.diff.analyze(diff_text)
        if not commit.files and diff.modified_files:
            commit.files = diff.modified_files
        commit.insertions = diff.added_lines
        commit.deletions = diff.removed_lines
        commit = self.parser.parse(commit)
        commit = self.classifier.classify(commit)
        candidate = self.candidates.evaluate(commit, failure_key, diff)
        candidate.evidence.insert(0, f"Repository: {window.name}")
        candidate.reasons.insert(
            0,
            f"Change is in '{window.name}' ({window.good_sha[:8]}..{window.bad_sha[:8]}).",
        )
        if skip_diff:
            candidate.evidence.append("Binary-only paths; diff skipped for speed")
        elif commit.is_merge_commit and not diff_text:
            candidate.evidence.append("Merge commit; full diff skipped for speed")
        return commit, candidate

    @staticmethod
    def _related_topics(failure: str) -> list[str]:
        profile = config.get_failure_profile(failure)
        if not profile:
            return []
        if profile.related:
            return [name for name in profile.related if name in config.failure_profiles]
        related = []
        for name, other in config.failure_profiles.items():
            if name == failure:
                continue
            if set(profile.domains) & set(other.domains):
                related.append(name)
        return sorted(related)[:16]


def _analysis_options(workers: int | None, fast: bool) -> AnalysisOptions:
    analysis = config.settings.get("analysis") or {}
    skip_binary = bool(analysis.get("skip_binary_only_diffs", True))
    default_workers = int(analysis.get("workers", 1))

    if fast:
        skip_binary = True
        cpu = os.cpu_count() or 4
        resolved_workers = max(4, min(cpu, 8))
    elif workers is not None:
        resolved_workers = max(0, int(workers))
    else:
        resolved_workers = default_workers

    if resolved_workers <= 1:
        resolved_workers = 1
    return AnalysisOptions(
        workers=resolved_workers,
        skip_binary_only_diffs=skip_binary,
    )


def _repo_label(path: str) -> str:
    from pathlib import Path

    name = Path(path).resolve().name
    return name or path

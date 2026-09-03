"""
Firmware Regression Intelligence (FRI)

Investigation Engine

Coordinates firmware regression investigation for one Git repo
or a multi-repo BIOS workspace (submodules / pin-sets).
"""

from __future__ import annotations

import time

from fri.analyzer.bisect_planner import BisectPlanner
from fri.analyzer.candidate_engine import CandidateEngine
from fri.analyzer.diff_analyzer import DiffAnalyzer
from fri.analyzer.module_analyzer import ModuleAnalyzer
from fri.analyzer.triage import BootTriage
from fri.classifier.classifier import FirmwareClassifier
from fri.collector.git_collector import GitCollector
from fri.collector.workspace import WorkspaceCollector
from fri.config import config
from fri.constants import HIGH_CONFIDENCE
from fri.logger import logger
from fri.models import (
    RegressionCandidate,
    RegressionReport,
    RegressionStatistics,
    RepoWindow,
    WorkspacePlan,
)
from fri.parser.commit_parser import CommitParser


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

    def investigate(self, good, bad, failure) -> RegressionReport:
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
        return self.investigate_plan(plan, failure)

    def investigate_workspace(self, workspace, good, bad, failure) -> RegressionReport:
        plan = self.workspace.plan_from_workspace(workspace, good, bad)
        return self.investigate_plan(plan, failure)

    def investigate_manifest(self, manifest, failure) -> RegressionReport:
        plan = self.workspace.plan_from_manifest(manifest)
        return self.investigate_plan(plan, failure)

    def investigate_plan(self, plan: WorkspacePlan, failure) -> RegressionReport:
        started = time.perf_counter()
        failure_key = failure.lower()
        profile = config.get_failure_profile(failure_key)

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

        for window in plan.windows:
            if window.good_sha == window.bad_sha:
                continue
            try:
                collector = GitCollector(window.path)
                commits = collector.get_commits(window.good_sha, window.bad_sha)
            except Exception as exc:
                logger.warning("Skipping %s: %s", window.name, exc)
                continue
            count_by_repo[window.name] = len(commits)
            for commit in commits:
                commit.repo_name = window.name
                commit.repo_path = window.path
                commit = self.parser.parse(commit)
                commit = self.classifier.classify(commit)
                diff_text = collector.get_diff(commit)
                diff = self.diff.analyze(diff_text)
                candidate = self.candidates.evaluate(commit, failure_key, diff)
                candidate.evidence.insert(0, f"Repository: {window.name}")
                candidate.reasons.insert(
                    0,
                    f"Change is in '{window.name}' ({window.good_sha[:8]}..{window.bad_sha[:8]}).",
                )
                regression_candidates.append(candidate)
                all_commits.append(commit)

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


def _repo_label(path: str) -> str:
    from pathlib import Path

    name = Path(path).resolve().name
    return name or path

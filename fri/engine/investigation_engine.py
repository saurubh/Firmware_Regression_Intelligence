"""
Firmware Regression Intelligence (FRI)

Investigation Engine

Coordinates the complete firmware regression investigation.
"""

from __future__ import annotations

import time

from fri.analyzer.bisect_planner import BisectPlanner
from fri.analyzer.candidate_engine import CandidateEngine
from fri.analyzer.diff_analyzer import DiffAnalyzer
from fri.analyzer.module_analyzer import ModuleAnalyzer
from fri.classifier.classifier import FirmwareClassifier
from fri.collector.git_collector import GitCollector
from fri.config import config
from fri.constants import HIGH_CONFIDENCE, OS_BOOT_RELATED_TOPICS, SUPPORTED_FAILURES
from fri.models import RegressionReport, RegressionStatistics
from fri.parser.commit_parser import CommitParser


class InvestigationEngine:
    def __init__(self, repo: str) -> None:
        self.collector = GitCollector(repo)
        self.parser = CommitParser()
        self.classifier = FirmwareClassifier()
        self.diff = DiffAnalyzer()
        self.candidates = CandidateEngine()
        self.modules = ModuleAnalyzer()
        self.bisect = BisectPlanner()

    def investigate(self, good, bad, failure) -> RegressionReport:
        started = time.perf_counter()
        failure_key = failure.lower()
        profile = config.get_failure_profile(failure_key)

        report = RegressionReport(
            good_sha=good,
            bad_sha=bad,
            failure=failure_key,
            profile_description=profile.description if profile else "",
            related_topics=self._related_topics(failure_key),
            covered_topics=list(SUPPORTED_FAILURES),
        )

        commits = self.collector.get_commits(good, bad)
        report.commits = commits
        regression_candidates = []

        for commit in commits:
            commit = self.parser.parse(commit)
            commit = self.classifier.classify(commit)
            diff_text = self.collector.get_diff(commit)
            diff = self.diff.analyze(diff_text)
            candidate = self.candidates.evaluate(commit, failure_key, diff)
            regression_candidates.append(candidate)

        ranked = self.candidates.rank(regression_candidates)
        minimum = int(config.settings.get("analysis", {}).get("minimum_confidence", 25))
        visible = self.candidates.filter_noise(ranked, minimum_confidence=minimum)
        report.candidates = visible or ranked[:10]

        report.modules = self.modules.analyze(report.candidates)
        report.bisect = self.bisect.plan(
            good_sha=good,
            bad_sha=bad,
            candidates=report.candidates,
            failure=failure_key,
        )

        hazard_commits = sum(1 for item in ranked if item.hazards)
        high = sum(1 for item in ranked if item.confidence >= HIGH_CONFIDENCE)
        report.statistics = RegressionStatistics(
            total_commits=len(commits),
            filtered_commits=max(len(ranked) - len(report.candidates), 0),
            candidate_commits=len(report.candidates),
            module_count=len(report.modules),
            execution_time=round(time.perf_counter() - started, 3),
            hazard_commits=hazard_commits,
            high_confidence=high,
        )
        return report

    @staticmethod
    def _related_topics(failure: str) -> list[str]:
        if failure == "os_boot":
            return list(OS_BOOT_RELATED_TOPICS)
        profile = config.get_failure_profile(failure)
        if not profile:
            return []
        related = []
        for name, other in config.failure_profiles.items():
            if name == failure:
                continue
            if set(profile.domains) & set(other.domains):
                related.append(name)
        return sorted(related)[:16]

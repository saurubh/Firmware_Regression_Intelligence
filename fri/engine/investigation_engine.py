"""
Firmware Regression Intelligence (FRI)

Investigation Engine

Coordinates the complete firmware regression investigation.

This class contains NO firmware-specific logic.
It orchestrates all analysis stages.
"""

from __future__ import annotations

from fri.analyzer.candidate_engine import CandidateEngine
from fri.analyzer.diff_analyzer import DiffAnalyzer
from fri.analyzer.module_analyzer import ModuleAnalyzer

from fri.classifier.classifier import FirmwareClassifier

from fri.collector.git_collector import GitCollector

from fri.parser.commit_parser import CommitParser

from fri.models import RegressionReport


class InvestigationEngine:

    def __init__(self, repo):

        self.collector = GitCollector(repo)

        self.parser = CommitParser()

        self.classifier = FirmwareClassifier()

        self.diff = DiffAnalyzer()

        self.candidates = CandidateEngine()

        self.modules = ModuleAnalyzer()

    # ----------------------------------------------------------

    def investigate(

        self,

        good,

        bad,

        failure

    ) -> RegressionReport:

        report = RegressionReport(

            good_sha=good,

            bad_sha=bad,

            failure=failure

        )

        #
        # Collect commits
        #
        commits = self.collector.get_commits(

            good,

            bad

        )

        report.commits = commits

        regression_candidates = []

        #
        # Analyze every commit
        #
        for commit in commits:

            #
            # Parse metadata
            #
            commit = self.parser.parse(commit)

            #
            # Firmware classification
            #
            commit = self.classifier.classify(commit)

            #
            # Diff
            #
            diff_text = self.collector.get_diff(commit)

            diff = self.diff.analyze(diff_text)

            #
            # Candidate
            #
            candidate = self.candidates.evaluate(

                commit,

                failure,

                diff

            )

            regression_candidates.append(

                candidate

            )

        #
        # Rank candidates
        #
        regression_candidates = self.candidates.rank(

            regression_candidates

        )

        report.candidates = regression_candidates

        #
        # Module aggregation
        #
        report.modules = self.modules.analyze(

            regression_candidates

        )

        return report

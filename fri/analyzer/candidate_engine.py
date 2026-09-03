"""
Firmware Regression Intelligence (FRI)

Candidate Engine

Builds regression candidates by combining

- Commit metadata
- Failure profile
- Diff evidence

Scoring is delegated to RegressionScorer.
"""

from __future__ import annotations

from fri.config import config
from fri.models import (
    Commit,
    RegressionCandidate,
    DiffEvidence,
)
from fri.scorer.regression_scorer import RegressionScorer


class CandidateEngine:
    """
    Builds regression candidates.

    This class assembles evidence and delegates scoring to
    RegressionScorer.
    """

    def __init__(self):

        self.failure_profiles = config.failure_profiles

        self.scorer = RegressionScorer()

    # ======================================================

    def evaluate(
        self,
        commit: Commit,
        failure: str,
        diff: DiffEvidence
    ) -> RegressionCandidate:

        #
        # Failure profile
        #
        profile = self.failure_profiles.get(
            failure.lower()
        )

        #
        # Candidate
        #
        candidate = RegressionCandidate(
            commit=commit
        )

        #
        # Score
        #
        return self.scorer.score(

            candidate=candidate,

            diff=diff,

            profile=profile

        )

    # ======================================================

    def rank(
        self,
        candidates: list[RegressionCandidate]
    ) -> list[RegressionCandidate]:
        """
        Sort candidates by confidence and assign ranks.
        """

        ranked = sorted(

            candidates,

            key=lambda c: (

                c.confidence,

                c.score

            ),

            reverse=True

        )

        for rank, candidate in enumerate(

            ranked,

            start=1

        ):

            candidate.rank = rank

        return ranked
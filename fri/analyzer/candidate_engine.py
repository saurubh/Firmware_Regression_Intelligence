"""
Firmware Regression Intelligence (FRI)

Candidate Engine

Builds regression candidates by combining commit metadata,
failure profile, and diff evidence. Scoring is delegated to
RegressionScorer.
"""

from __future__ import annotations

from fri.config import config
from fri.constants import LOW_CONFIDENCE
from fri.models import Commit, DiffEvidence, RegressionCandidate
from fri.scorer.regression_scorer import RegressionScorer


class CandidateEngine:
    """Assembles evidence and delegates scoring to RegressionScorer."""

    def __init__(self) -> None:
        self.failure_profiles = config.failure_profiles
        self.scorer = RegressionScorer()

    def evaluate(
        self,
        commit: Commit,
        failure: str,
        diff: DiffEvidence,
    ) -> RegressionCandidate:
        profile = self.failure_profiles.get(failure.lower())
        candidate = RegressionCandidate(commit=commit)
        return self.scorer.score(candidate=candidate, diff=diff, profile=profile)

    def rank(
        self,
        candidates: list[RegressionCandidate],
    ) -> list[RegressionCandidate]:
        ranked = sorted(
            candidates,
            key=lambda c: (c.score, c.signal_count, c.confidence),
            reverse=True,
        )
        peak = max((item.score for item in ranked), default=0)
        for rank, candidate in enumerate(ranked, start=1):
            candidate.rank = rank
            candidate.confidence = self.scorer.relative_confidence(
                candidate.score,
                peak,
            )
        return ranked

    def filter_noise(
        self,
        candidates: list[RegressionCandidate],
        minimum_confidence: int | None = None,
    ) -> list[RegressionCandidate]:
        threshold = (
            minimum_confidence
            if minimum_confidence is not None
            else int(config.settings.get("analysis", {}).get("minimum_confidence", LOW_CONFIDENCE))
        )
        return [item for item in candidates if item.confidence >= threshold]

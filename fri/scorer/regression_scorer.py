"""
Firmware Regression Intelligence (FRI)

Regression Scorer

Responsible only for assigning a score and confidence
to a RegressionCandidate.

No Git operations.
No parsing.
No report generation.
"""

from __future__ import annotations

from fri.models import (
    DiffEvidence,
    FailureProfile,
    RegressionCandidate,
)


class RegressionScorer:
    """
    Calculates candidate score and confidence.

    This class encapsulates all scoring heuristics so that
    CandidateEngine only builds evidence.
    """

    #
    # Weights
    #
    DOMAIN_MATCH = 30

    KEYWORD_MATCH = 3

    FIX_COMMIT = 8

    ENABLE_COMMIT = 10

    REVERT_COMMIT = 15

    MERGE_COMMIT = 5

    JIRA_PRESENT = 5

    LARGE_CHANGE = 15

    MEDIUM_CHANGE = 8

    MAX_DIFF_SCORE = 20

    # -----------------------------------------------------

    def score(
        self,
        candidate: RegressionCandidate,
        diff: DiffEvidence,
        profile: FailureProfile | None,
    ) -> RegressionCandidate:

        score = 0

        #
        # Failure profile
        #
        if profile:

            for domain in candidate.commit.domains:

                if domain in profile.domains:

                    score += self.DOMAIN_MATCH

                    candidate.matched_domains.append(domain)

                    candidate.reasons.append(
                        f"Domain '{domain}' matches failure profile."
                    )

        #
        # Firmware keywords
        #
        for keyword in diff.firmware_keywords:

            score += self.KEYWORD_MATCH

            candidate.matched_keywords.append(keyword)

            candidate.evidence.append(
                f"Firmware keyword: {keyword}"
            )

        #
        # Changed files
        #
        candidate.matched_files.extend(
            candidate.commit.files
        )

        #
        # Intent
        #
        score += self._intent_score(candidate)

        #
        # Merge commit
        #
        if candidate.commit.is_merge_commit:

            score += self.MERGE_COMMIT

            candidate.evidence.append(
                "Merge commit"
            )

        #
        # Jira
        #
        if candidate.commit.jira:

            score += self.JIRA_PRESENT

            candidate.evidence.append(
                f"Jira {candidate.commit.jira}"
            )

        #
        # Change size
        #
        score += self._change_size_score(candidate)

        #
        # Diff complexity
        #
        score += min(
            diff.score,
            self.MAX_DIFF_SCORE
        )

        #
        # Final score
        #
        candidate.score = score

        candidate.confidence = self._confidence(score)

        return candidate

    # -----------------------------------------------------

    def _intent_score(
        self,
        candidate: RegressionCandidate
    ) -> int:

        intent = candidate.commit.intent

        if intent == "Fix":

            candidate.evidence.append("Fix commit")

            return self.FIX_COMMIT

        if intent == "Enable":

            candidate.evidence.append(
                "Feature enablement"
            )

            return self.ENABLE_COMMIT

        if intent == "Revert":

            candidate.evidence.append(
                "Revert commit"
            )

            return self.REVERT_COMMIT

        return 0

    # -----------------------------------------------------

    def _change_size_score(
        self,
        candidate: RegressionCandidate
    ) -> int:

        changes = candidate.commit.total_changes

        if changes > 500:

            candidate.evidence.append(
                "Large code change"
            )

            return self.LARGE_CHANGE

        if changes > 100:

            candidate.evidence.append(
                "Medium code change"
            )

            return self.MEDIUM_CHANGE

        return 0

    # -----------------------------------------------------

    @staticmethod
    def _confidence(score: int) -> int:
        """
        Convert raw score into a normalized confidence.

        Current implementation clamps to 100.

        This method is intentionally separated so future
        statistical models or ML-based confidence estimation
        can replace the heuristic without changing callers.
        """

        return min(score, 100)

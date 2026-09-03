"""
Firmware Regression Intelligence (FRI)

Regression Scorer

Assigns a score and confidence to a RegressionCandidate using
independent signals so true regression commits rank above noise.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable

from fri.constants import DOC_NAMES, DOC_SUFFIXES
from fri.models import (
    DiffEvidence,
    FailureProfile,
    RegressionCandidate,
)
from fri.utils.matching import keyword_in_text, path_matches


class RegressionScorer:
    """Calculates candidate score and confidence from stacked evidence."""

    DOMAIN_MATCH = 28
    DOMAIN_EXTRA = 10
    MAX_DOMAIN_POINTS = 48
    PATH_MATCH = 22
    PROFILE_KEYWORD_MESSAGE = 14
    PROFILE_KEYWORD_DIFF = 10
    RISK_SIGNAL = 12
    HAZARD_HIGH = 18
    HAZARD_MEDIUM = 9
    HAZARD_CATEGORY_MATCH = 8
    BOOT_API = 16
    PCD_CHANGE = 6
    PROTOCOL_CHANGE = 4
    FIX_COMMIT = 8
    ENABLE_COMMIT = 12
    DISABLE_COMMIT = 12
    REVERT_COMMIT = 18
    WORKAROUND_COMMIT = 10
    MERGE_COMMIT = 4
    JIRA_PRESENT = 4
    LARGE_CHANGE = 10
    MEDIUM_CHANGE = 5
    MAX_GENERIC_KEYWORD = 8
    MAX_DIFF_SCORE = 24
    PHASE_MATCH = 26
    UNRELATED_PENALTY = 12
    DOCS_PENALTY = 25
    COMMENT_PENALTY = 18

    def score(
        self,
        candidate: RegressionCandidate,
        diff: DiffEvidence,
        profile: FailureProfile | None,
    ) -> RegressionCandidate:
        score = 0
        signals = 0
        commit = candidate.commit

        if self._is_docs_only(commit.files):
            diff.docs_only = True
            candidate.evidence.append("Documentation-only change")
            score -= self.DOCS_PENALTY

        if diff.comment_only:
            candidate.evidence.append("Comment-only diff")
            score -= self.COMMENT_PENALTY

        if profile:
            domain_hits = self._score_domains(candidate, profile)
            path_hits = self._score_paths(candidate, profile)
            keyword_hits = self._score_profile_keywords(candidate, diff, profile)
            risk_hits = self._score_risk_signals(candidate, diff, profile)
            score += domain_hits + path_hits + keyword_hits + risk_hits
            if domain_hits:
                signals += 1
            if path_hits:
                signals += 1
            if keyword_hits:
                signals += 1
            if risk_hits:
                signals += 1
            if (
                not (domain_hits or path_hits or keyword_hits)
                and commit.domains
                and profile.breadth != "wide"
            ):
                score -= self.UNRELATED_PENALTY
                candidate.reasons.append(
                    "No overlap with the selected failure profile; down-ranked."
                )
            if profile.phase and profile.phase != "all":
                if profile.phase in candidate.phases or profile.phase == candidate.primary_phase:
                    score += self.PHASE_MATCH
                    signals += 1
                    candidate.reasons.append(
                        f"Commit phase '{candidate.primary_phase}' matches failure '{profile.name}'."
                    )

        hazard_score, hazard_signals = self._score_hazards(candidate, diff, profile)
        score += hazard_score
        signals += hazard_signals

        if diff.boot_api_hits:
            api_score = min(len(diff.boot_api_hits) * self.BOOT_API, 48)
            if not self._boot_api_relevant(profile):
                api_score = min(api_score, 8)
            else:
                candidate.reasons.append(
                    "Commit touches firmware boot-services APIs used during OS handoff."
                )
            score += api_score
            signals += 1
            candidate.evidence.append(
                "Boot/OS-handoff APIs: " + ", ".join(diff.boot_api_hits[:8])
            )

        if diff.pcd_names:
            score += min(len(diff.pcd_names) * self.PCD_CHANGE, 18)
            signals += 1
            candidate.evidence.append(
                "PCD/UPD symbols: " + ", ".join(diff.pcd_names[:8])
            )

        if diff.protocol_hits:
            score += min(len(diff.protocol_hits) * self.PROTOCOL_CHANGE, 12)
            candidate.evidence.append(
                "Protocol/PPI GUIDs: " + ", ".join(diff.protocol_hits[:6])
            )

        score += self._intent_score(candidate)
        if commit.intent in {"Revert", "Enable", "Disable", "Fix", "Workaround"}:
            signals += 1

        if commit.is_merge_commit:
            score += self.MERGE_COMMIT
            candidate.evidence.append("Merge commit")

        if commit.jira:
            score += self.JIRA_PRESENT
            candidate.evidence.append(f"Jira {commit.jira}")

        score += self._change_size_score(candidate)
        score += min(diff.score, self.MAX_DIFF_SCORE)

        generic = self._generic_keyword_score(candidate, diff, profile)
        score += generic

        candidate.matched_files = list(commit.files)
        candidate.signal_count = signals
        candidate.score = max(score, 0)
        candidate.confidence = self.absolute_confidence(candidate.score)
        return candidate

    def _score_domains(
        self,
        candidate: RegressionCandidate,
        profile: FailureProfile,
    ) -> int:
        score = 0
        profile_domains = {item.lower() for item in profile.domains}
        hits = 0
        for domain in candidate.commit.domains:
            if domain.lower() not in profile_domains:
                continue
            hits += 1
            score += self.DOMAIN_MATCH if hits == 1 else self.DOMAIN_EXTRA
            candidate.matched_domains.append(domain)
            candidate.reasons.append(
                f"Domain '{domain}' matches failure profile '{profile.name}'."
            )
        return min(score, self.MAX_DOMAIN_POINTS)

    def _score_paths(
        self,
        candidate: RegressionCandidate,
        profile: FailureProfile,
    ) -> int:
        if not profile.path_patterns:
            return 0
        score = 0
        seen: set[str] = set()
        for path in candidate.commit.files:
            for pattern in profile.path_patterns:
                needle = pattern.lower()
                if needle and path_matches(path, needle) and path not in seen:
                    seen.add(path)
                    score += self.PATH_MATCH
                    candidate.matched_paths.append(path)
                    candidate.reasons.append(
                        f"Path '{path}' matches profile pattern '{pattern}'."
                    )
                    break
        return min(score, self.PATH_MATCH * 4)

    def _score_profile_keywords(
        self,
        candidate: RegressionCandidate,
        diff: DiffEvidence,
        profile: FailureProfile,
    ) -> int:
        if not profile.keywords:
            return 0

        message = candidate.commit.message.lower()
        blob = " ".join(diff.firmware_keywords + diff.tokens).lower()
        score = 0

        for keyword in profile.keywords:
            needle = keyword.lower()
            if self._contains_term(message, needle):
                score += self.PROFILE_KEYWORD_MESSAGE
                candidate.matched_keywords.append(keyword)
                candidate.evidence.append(f"Commit message keyword: {keyword}")
            elif self._contains_term(blob, needle):
                score += self.PROFILE_KEYWORD_DIFF
                candidate.matched_keywords.append(keyword)
                candidate.evidence.append(f"Diff keyword: {keyword}")

        # Deduplicate while preserving order
        candidate.matched_keywords = list(dict.fromkeys(candidate.matched_keywords))
        return min(score, 70)

    def _score_risk_signals(
        self,
        candidate: RegressionCandidate,
        diff: DiffEvidence,
        profile: FailureProfile,
    ) -> int:
        if not profile.risk_signals:
            return 0
        haystack = " ".join(
            [
                candidate.commit.message,
                " ".join(diff.firmware_keywords),
                " ".join(h.name for h in diff.hazards),
                " ".join(diff.boot_api_hits),
            ]
        ).lower()
        score = 0
        for signal in profile.risk_signals:
            if not isinstance(signal, str) or not signal:
                continue
            if keyword_in_text(haystack, signal):
                score += self.RISK_SIGNAL
                candidate.evidence.append(f"Risk signal: {signal}")
        return min(score, 48)

    def _score_hazards(
        self,
        candidate: RegressionCandidate,
        diff: DiffEvidence,
        profile: FailureProfile | None,
    ) -> tuple[int, int]:
        if not diff.hazards:
            return 0, 0

        profile_name = (profile.name if profile else "").lower()
        profile_domains = {item.lower() for item in (profile.domains if profile else [])}
        bootish = profile_name in {"os_boot", "boot", "linuxboot", "csm", "generic"}
        score = 0
        for hazard in diff.hazards:
            points = self.HAZARD_HIGH if hazard.severity == "high" else self.HAZARD_MEDIUM
            relevant = (
                not profile
                or profile.breadth == "wide"
                or hazard.category == "generic"
                or hazard.category == profile_name
                or hazard.category in profile_domains
                or (bootish and hazard.category in {"os_boot", "boot", "acpi"})
                or hazard.category == (profile.phase if profile else "")
            )
            if relevant:
                if profile and (
                    hazard.category == profile_name
                    or hazard.category in profile_domains
                    or (bootish and hazard.category in {"os_boot", "boot", "acpi"})
                ):
                    points += self.HAZARD_CATEGORY_MATCH
            else:
                points = 3
            score += points
            label = f"{hazard.severity.upper()} hazard: {hazard.name}"
            candidate.hazards.append(label)
            candidate.evidence.append(label)
            if hazard.detail:
                candidate.evidence.append(f"  ↳ {hazard.detail}")
            candidate.reasons.append(
                f"High-risk change '{hazard.name}' is a common cause of {hazard.category} regressions."
            )
        return min(score, 80), 1

    def _generic_keyword_score(
        self,
        candidate: RegressionCandidate,
        diff: DiffEvidence,
        profile: FailureProfile | None,
    ) -> int:
        profile_needles = {k.lower() for k in (profile.keywords if profile else [])}
        extra = 0
        for keyword in diff.firmware_keywords:
            if keyword.lower() in profile_needles:
                continue
            extra += 1
            if extra >= self.MAX_GENERIC_KEYWORD:
                break
        if extra:
            candidate.evidence.append(f"Additional firmware keywords: {extra}")
        return extra

    @staticmethod
    def _contains_term(haystack: str, needle: str) -> bool:
        if not needle:
            return False
        compacted = haystack.replace(" ", "")
        compacted_needle = needle.replace(" ", "")
        if len(needle) <= 4:
            return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None
        return needle in haystack or compacted_needle in compacted

    @staticmethod
    def _boot_api_relevant(profile: FailureProfile | None) -> bool:
        if profile is None:
            return True
        name = profile.name.lower()
        if name in {"os_boot", "boot", "linuxboot", "csm", "generic", "variable", "from_reset", "bds"}:
            return True
        return bool({"Boot", "BDS", "OSLoader", "LinuxBoot"} & set(profile.domains))

    def _intent_score(self, candidate: RegressionCandidate) -> int:
        intent = candidate.commit.intent
        mapping = {
            "Fix": ("Fix commit (often hides a nearby regression)", self.FIX_COMMIT),
            "Enable": ("Feature enablement", self.ENABLE_COMMIT),
            "Disable": ("Feature disablement", self.DISABLE_COMMIT),
            "Revert": ("Revert commit", self.REVERT_COMMIT),
            "Workaround": ("Workaround commit", self.WORKAROUND_COMMIT),
        }
        if intent in mapping:
            label, value = mapping[intent]
            candidate.evidence.append(label)
            return value
        return 0

    def _change_size_score(self, candidate: RegressionCandidate) -> int:
        if candidate.commit.total_changes > 500:
            candidate.evidence.append("Large code change")
            return self.LARGE_CHANGE
        if candidate.commit.total_changes > 100:
            candidate.evidence.append("Medium code change")
            return self.MEDIUM_CHANGE
        return 0

    @staticmethod
    def _is_docs_only(files: Iterable[str]) -> bool:
        paths = list(files)
        if not paths:
            return False
        for path in paths:
            lower = path.replace("\\", "/").lower()
            name = lower.rsplit("/", 1)[-1]
            if name in DOC_NAMES:
                continue
            if any(lower.endswith(suffix) for suffix in DOC_SUFFIXES):
                continue
            return False
        return True

    @staticmethod
    def absolute_confidence(score: int) -> int:
        """Per-commit curve that saturates slowly so mid-tier scores stay below 100."""
        curved = 100.0 * (1.0 - math.exp(-max(score, 0) / 140.0))
        return max(0, min(99, int(round(curved))))

    @staticmethod
    def relative_confidence(score: int, peak: int) -> int:
        """
        Spread confidence across an investigation so the top suspects
        are distinguishable instead of all clamping at 100.
        """
        if peak <= 0:
            return 0
        if score >= peak:
            return 100
        relative = 100.0 * score / peak
        absolute = 100.0 * (1.0 - math.exp(-score / 140.0))
        mixed = 0.72 * relative + 0.28 * absolute
        return max(0, min(100, int(round(mixed))))

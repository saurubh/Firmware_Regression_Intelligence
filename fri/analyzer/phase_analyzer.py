"""
Tag commits with UEFI boot phase and CPU vendor.

Phases run CPU-out-of-reset → OS. Vendor is inferred from Intel FSP/FIT/ME
versus AMD AGESA/PSP/NBIO paths — still firmware-repo only.
"""

from __future__ import annotations

from collections import defaultdict

from fri.config import config
from fri.models import DiffEvidence, RegressionCandidate
from fri.utils.matching import keyword_in_text, path_matches

_INTEL_MARKERS = (
    "fsp",
    "csme",
    "bootguard",
    "intelvtd",
    "pch",
    "iio",
    "txt",
    "fit",
    "mrc",
)
_AMD_MARKERS = (
    "agesa",
    "psp",
    "nbio",
    "smu",
    "ivrs",
    "ccp",
    "sev",
    "umc",
)


class PhaseAnalyzer:
    def tag(self, candidate: RegressionCandidate, diff: DiffEvidence) -> RegressionCandidate:
        commit = candidate.commit
        weights: dict[str, float] = defaultdict(float)
        blob = " ".join(
            [
                commit.message,
                " ".join(commit.keywords),
                " ".join(commit.files),
                " ".join(diff.firmware_keywords),
            ]
        )

        for phase in config.ordered_phases():
            for path in commit.files:
                for pattern in phase.paths:
                    if path_matches(path, pattern):
                        weights[phase.name] += 2.0 + min(len(pattern), 16) / 16.0
            for domain in commit.domains:
                if domain in phase.domains:
                    weights[phase.name] += 1.5
            for keyword in phase.keywords:
                if keyword_in_text(blob, keyword):
                    weights[phase.name] += 1.0

        ordered = sorted(weights, key=lambda name: (-weights[name], name))
        candidate.phases = ordered
        candidate.primary_phase = ordered[0] if ordered else "Unknown"
        candidate.vendor = self.detect_vendor(commit.files, blob)
        if candidate.primary_phase != "Unknown":
            spec = config.boot_phases.get(candidate.primary_phase)
            edge = spec.edge if spec else candidate.primary_phase
            candidate.reasons.append(
                f"Boot phase '{candidate.primary_phase}': {edge}"
            )
            candidate.evidence.append(
                f"Vendor hint: {candidate.vendor}; phase: {candidate.primary_phase}"
            )
        return candidate

    @staticmethod
    def detect_vendor(files: list[str], blob: str) -> str:
        haystack = (" ".join(files) + " " + blob).lower()
        intel = sum(1 for marker in _INTEL_MARKERS if marker in haystack)
        amd = sum(1 for marker in _AMD_MARKERS if marker in haystack)
        if intel > amd and intel > 0:
            return "intel"
        if amd > intel and amd > 0:
            return "amd"
        return "common"

"""
Turn phase-tagged candidates into an ordered reset→OS triage plan.
"""

from __future__ import annotations

import math
from collections import defaultdict

from fri.config import config
from fri.models import PhaseFinding, RegressionCandidate, TriagePlan


class BootTriage:
    def plan(self, candidates: list[RegressionCandidate]) -> TriagePlan:
        groups: dict[str, list[RegressionCandidate]] = defaultdict(list)
        vendor_votes: dict[str, int] = defaultdict(int)
        for candidate in candidates:
            phase = candidate.primary_phase or "Unknown"
            groups[phase].append(candidate)
            vendor_votes[candidate.vendor] += 1

        findings: list[PhaseFinding] = []
        for name, group in groups.items():
            spec = config.boot_phases.get(name)
            shas = {item.commit.sha for item in group}
            strength = sum(item.score for item in group) * math.sqrt(max(len(shas), 1))
            findings.append(
                PhaseFinding(
                    name=name,
                    order=spec.order if spec else 999,
                    confidence=0,
                    strength=round(strength, 3),
                    edge=spec.edge if spec else "",
                    description=spec.description if spec else "",
                    vendors=sorted({item.vendor for item in group}),
                    commits=[item.commit for item in group],
                    reasons=list(
                        dict.fromkeys(
                            reason for item in group for reason in item.reasons[:2]
                        )
                    )[:8],
                )
            )

        peak = max((item.strength for item in findings), default=0.0)
        for item in findings:
            item.confidence = (
                min(100, int(round(100.0 * item.strength / peak))) if peak else 0
            )
        findings.sort(key=lambda item: (-item.confidence, item.order))

        vendor = "common"
        if vendor_votes:
            vendor = max(vendor_votes, key=lambda key: vendor_votes[key])

        start = findings[0] if findings else None
        reason = ""
        if start and start.name != "Unknown":
            reason = (
                f"Start at '{start.name}' ({start.edge}). "
                f"{len(start.commits)} commit(s) in the good→bad window hit this phase"
                + (f" ({vendor} silicon)." if vendor != "common" else ".")
            )
        return TriagePlan(
            start_phase=start.name if start else "",
            start_reason=reason,
            vendor_hint=vendor,
            phases=findings,
        )

"""
Firmware Regression Intelligence (FRI)

Bisect Planner

Turns top-ranked candidates into a practical validation plan.
"""

from __future__ import annotations

from fri.models import BisectPlan, RegressionCandidate, ValidationStep


class BisectPlanner:
    def plan(
        self,
        good_sha: str,
        bad_sha: str,
        candidates: list[RegressionCandidate],
        failure: str,
    ) -> BisectPlan:
        commands = [
            f"git bisect start {bad_sha} {good_sha}",
            f"git bisect run ./repro-{failure}.sh",
            "git bisect reset",
        ]
        steps: list[ValidationStep] = []
        for index, candidate in enumerate(candidates[:8], start=1):
            subject = candidate.commit.subject[:90]
            minutes = 30 if candidate.confidence >= 80 else 45
            steps.append(
                ValidationStep(
                    priority=index,
                    commit=candidate.commit,
                    description=(
                        f"Flash/build {candidate.commit.short_sha} ({subject}) "
                        f"and reproduce '{failure}'. Confidence {candidate.confidence}%."
                    ),
                    estimated_minutes=minutes,
                )
            )
        return BisectPlan(
            good_sha=good_sha,
            bad_sha=bad_sha,
            commands=commands,
            steps=steps,
        )

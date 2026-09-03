"""
Firmware Regression Intelligence (FRI)

Bisect Planner

Turns top-ranked candidates into a practical validation plan.
"""

from __future__ import annotations

from pathlib import Path

from fri.models import BisectPlan, RegressionCandidate, RepoDelta, ValidationStep


class BisectPlanner:
    def plan(
        self,
        good_sha: str,
        bad_sha: str,
        candidates: list[RegressionCandidate],
        failure: str,
        workspace: str = "",
        deltas: list[RepoDelta] | None = None,
    ) -> BisectPlan:
        commands = self._commands(good_sha, bad_sha, failure, workspace, deltas or [])
        steps: list[ValidationStep] = []
        for index, candidate in enumerate(candidates[:8], start=1):
            subject = candidate.commit.subject[:90]
            minutes = 30 if candidate.confidence >= 80 else 45
            repo = candidate.commit.repo_name
            where = f" in {repo}" if repo else ""
            steps.append(
                ValidationStep(
                    priority=index,
                    commit=candidate.commit,
                    description=(
                        f"Flash/build {candidate.commit.short_sha}{where} ({subject}) "
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

    @staticmethod
    def _commands(
        good_sha: str,
        bad_sha: str,
        failure: str,
        workspace: str,
        deltas: list[RepoDelta],
    ) -> list[str]:
        moved = [item for item in deltas if item.status == "changed" and item.good_sha and item.bad_sha]
        if len(moved) <= 1:
            return [
                f"git bisect start {bad_sha} {good_sha}",
                f"git bisect run ./repro-{failure}.sh",
                "git bisect reset",
            ]
        commands = [
            "# A BIOS build is a pin-set. Bisect each moved repo separately;",
            "# do not bisect the superproject SHA as if it were one tree.",
        ]
        root = Path(workspace) if workspace else Path(".")
        for item in moved:
            repo_dir = item.path if Path(item.path).is_absolute() else str(root / item.path)
            commands.append(f"# {item.name}")
            commands.append(f"git -C {repo_dir} bisect start {item.bad_sha} {item.good_sha}")
            commands.append(f"git -C {repo_dir} bisect run ./repro-{failure}.sh")
            commands.append(f"git -C {repo_dir} bisect reset")
        return commands

"""
Firmware Regression Intelligence (FRI)

Console Report

Pretty prints investigation results.
"""

from __future__ import annotations

from fri.constants import PROJECT_NAME, VERSION


class ConsoleReport:

    def render(self, report):

        print()

        print("=" * 90)
        print(f"{PROJECT_NAME} v{VERSION}".center(90))
        print("=" * 90)

        print()

        print(f"Good Build : {report.good_sha}")
        print(f"Bad Build  : {report.bad_sha}")
        print(f"Failure    : {report.failure}")

        print()

        print("=" * 90)
        print("TOP REGRESSION CANDIDATES")
        print("=" * 90)

        print()

        if not report.candidates:

            print("No candidate commits found.")

        for idx, candidate in enumerate(
                report.candidates,
                start=1):

            commit = candidate.commit

            print(f"[{idx}] {commit.short_sha}")

            print(f"     Confidence : {candidate.confidence}%")
            print(f"     Author     : {commit.author}")
            print(f"     Jira       : {commit.jira}")
            print(f"     Intent     : {commit.intent}")
            print(f"     Domain     : {commit.primary_domain}")

            if candidate.matched_domains:

                print(
                    "     Domains    : "
                    + ", ".join(candidate.matched_domains)
                )

            print()

            if candidate.evidence:

                print("     Evidence")

                for item in candidate.evidence:

                    print(f"        ✓ {item}")

            print()

        print("=" * 90)
        print("MOST AFFECTED MODULES")
        print("=" * 90)

        print()

        for module in report.modules:

            print(
                f"{module.name:20}"
                f"{module.confidence:3}%"
            )

            print(
                f"   Commits : {len(module.commits)}"
            )

            if module.jiras:

                print(
                    "   Jira    : "
                    + ", ".join(module.jiras)
                )

            print()

        print("=" * 90)

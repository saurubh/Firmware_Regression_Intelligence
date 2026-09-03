"""
Firmware Regression Intelligence (FRI)

Console Report

Pretty prints investigation results.
"""

from __future__ import annotations

from fri.constants import PROJECT_NAME, VERSION


class ConsoleReport:
    def render(self, report, top: int = 10) -> None:
        print()
        print("=" * 90)
        print(f"{PROJECT_NAME} v{VERSION}".center(90))
        print("=" * 90)
        print()
        print(f"Good Build : {report.good_sha}")
        print(f"Bad Build  : {report.bad_sha}")
        print(f"Failure    : {report.failure}")
        if report.workspace:
            print(f"Workspace  : {report.workspace}")
        if report.profile_description:
            print()
            print(report.profile_description)
        stats = report.statistics
        print()
        print(
            f"Commits {stats.total_commits}  |  "
            f"Candidates {stats.candidate_commits}  |  "
            f"Hazards {stats.hazard_commits}  |  "
            f"High-confidence {stats.high_confidence}  |  "
            f"Repos {stats.repo_count}  |  "
            f"{stats.execution_time}s"
        )
        if report.repo_deltas:
            print()
            print("=" * 90)
            print("PIN-SET  (repos that moved between the two BIOS builds)")
            print("=" * 90)
            print()
            print(f"{'repo':<28} {'status':<10} {'via':<16} {'commits':<8} {'good':<12} {'bad':<12}")
            print("-" * 90)
            for delta in report.repo_deltas:
                via = f"{delta.good_source or '-'}/{delta.bad_source or '-'}"
                print(
                    f"{delta.name:<28} {delta.status:<10} {via:<16} {delta.commit_count:<8} "
                    f"{(delta.good_sha or '-'):<12.12} {(delta.bad_sha or '-'):<12.12}"
                )
        if report.related_topics:
            print()
            print("Related topics: " + ", ".join(report.related_topics))

        if report.triage and report.triage.phases:
            print()
            print("=" * 90)
            print("BOOT PHASE TRIAGE  (CPU reset → OS)")
            print("=" * 90)
            print()
            if report.triage.start_reason:
                print(report.triage.start_reason)
                print()
            for finding in report.triage.phases:
                print(
                    f"  {finding.order:3}  {finding.name:16} {finding.confidence:3}%  "
                    f"{finding.edge}"
                )
            print()

        print()
        print("=" * 90)
        print("TOP REGRESSION CANDIDATES")
        print("=" * 90)
        print()

        candidates = report.candidates[:top]
        if not candidates:
            print("No candidate commits found.")

        for idx, candidate in enumerate(candidates, start=1):
            commit = candidate.commit
            print(f"[{idx}] {commit.short_sha}   score={candidate.score}  signals={candidate.signal_count}")
            print(f"     Confidence : {candidate.confidence}%")
            if commit.repo_name:
                print(f"     Repo       : {commit.repo_name}")
            print(f"     Author     : {commit.author}")
            print(f"     Jira       : {commit.jira}")
            print(f"     Intent     : {commit.intent}")
            print(f"     Domain     : {commit.primary_domain}")
            print(f"     Phase      : {candidate.primary_phase} ({candidate.vendor})")
            print(f"     Subject    : {commit.subject}")
            if candidate.matched_domains:
                print("     Domains    : " + ", ".join(candidate.matched_domains))
            if candidate.matched_keywords:
                print("     Keywords   : " + ", ".join(candidate.matched_keywords[:12]))
            if candidate.hazards:
                print("     Hazards    : " + "; ".join(candidate.hazards[:6]))
            if candidate.reasons:
                print("     Why")
                for reason in candidate.reasons[:6]:
                    print(f"        • {reason}")
            if candidate.evidence:
                print("     Evidence")
                for item in candidate.evidence[:10]:
                    print(f"        ✓ {item}")
            print()

        print("=" * 90)
        print("MOST AFFECTED MODULES")
        print("=" * 90)
        print()
        for module in report.modules:
            print(f"{module.name:20}{module.confidence:3}%")
            print(f"   Commits : {len(module.commits)}")
            if module.jiras:
                print("   Jira    : " + ", ".join(module.jiras))
            print()

        if report.bisect and report.bisect.commands:
            print("=" * 90)
            print("GIT BISECT")
            print("=" * 90)
            print()
            for command in report.bisect.commands:
                print(f"  {command}")
            print()

        print("=" * 90)
        print("COVERED REGRESSION TOPICS")
        print("=" * 90)
        print()
        print(", ".join(report.covered_topics))
        print()
        print("=" * 90)

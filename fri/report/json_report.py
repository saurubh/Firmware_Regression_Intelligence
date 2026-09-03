"""
Firmware Regression Intelligence (FRI)

JSON Report Generator
"""

from __future__ import annotations

import json
from pathlib import Path

from fri.constants import JSON_REPORT


class JsonReport:
    """Serializes a RegressionReport into JSON."""

    def render(self, report, top: int = 10):
        output = Path(JSON_REPORT)
        output.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "good_sha": report.good_sha,
            "bad_sha": report.bad_sha,
            "failure": report.failure,
            "profile_description": report.profile_description,
            "related_topics": report.related_topics,
            "covered_topics": report.covered_topics,
            "triage": None,
            "generated_at": report.generated_at.isoformat(),
            "workspace": report.workspace,
            "repo_deltas": [
                {
                    "name": delta.name,
                    "path": delta.path,
                    "good_sha": delta.good_sha,
                    "bad_sha": delta.bad_sha,
                    "commit_count": delta.commit_count,
                    "status": delta.status,
                }
                for delta in report.repo_deltas
            ],
            "statistics": {
                "total_commits": report.statistics.total_commits,
                "filtered_commits": report.statistics.filtered_commits,
                "candidate_commits": report.statistics.candidate_commits,
                "module_count": report.statistics.module_count,
                "execution_time": report.statistics.execution_time,
                "hazard_commits": report.statistics.hazard_commits,
                "high_confidence": report.statistics.high_confidence,
                "repo_count": report.statistics.repo_count,
            },
            "commits": [],
            "candidates": [],
            "modules": [],
        }

        for commit in report.commits:
            data["commits"].append(
                {
                    "sha": commit.sha,
                    "short_sha": commit.short_sha,
                    "author": commit.author,
                    "email": commit.email,
                    "date": commit.date.isoformat(),
                    "message": commit.message,
                    "jira": commit.jira,
                    "merge_request": commit.merge_request,
                    "intent": commit.intent,
                    "primary_domain": commit.primary_domain,
                    "domains": commit.domains,
                    "keywords": commit.keywords,
                    "files": commit.files,
                    "insertions": commit.insertions,
                    "deletions": commit.deletions,
                    "total_changes": commit.total_changes,
                    "merge_commit": commit.is_merge_commit,
                    "repo_name": commit.repo_name,
                    "repo_path": commit.repo_path,
                }
            )

        for candidate in report.candidates[:top]:
            data["candidates"].append(
                {
                    "rank": candidate.rank,
                    "commit": candidate.commit.short_sha,
                    "sha": candidate.commit.sha,
                    "repo": candidate.commit.repo_name,
                    "subject": candidate.commit.subject,
                    "confidence": candidate.confidence,
                    "score": candidate.score,
                    "signal_count": candidate.signal_count,
                    "matched_domains": candidate.matched_domains,
                    "matched_keywords": candidate.matched_keywords,
                    "matched_files": candidate.matched_files,
                    "matched_paths": candidate.matched_paths,
                    "hazards": candidate.hazards,
                    "phases": candidate.phases,
                    "primary_phase": candidate.primary_phase,
                    "vendor": candidate.vendor,
                    "reasons": candidate.reasons,
                    "evidence": candidate.evidence,
                }
            )

        for module in report.modules:
            data["modules"].append(
                {
                    "name": module.name,
                    "confidence": module.confidence,
                    "strength": module.strength,
                    "commits": [commit.short_sha for commit in module.commits],
                    "jiras": module.jiras,
                    "authors": module.authors,
                    "files": module.files,
                    "reasons": module.reasons,
                }
            )

        if report.triage is not None:
            data["triage"] = {
                "start_phase": report.triage.start_phase,
                "start_reason": report.triage.start_reason,
                "vendor_hint": report.triage.vendor_hint,
                "phases": [
                    {
                        "name": finding.name,
                        "order": finding.order,
                        "confidence": finding.confidence,
                        "strength": finding.strength,
                        "edge": finding.edge,
                        "description": finding.description,
                        "vendors": finding.vendors,
                        "commits": [commit.short_sha for commit in finding.commits],
                    }
                    for finding in report.triage.phases
                ],
            }

        if report.bisect is not None:
            data["bisect"] = {
                "good_sha": report.bisect.good_sha,
                "bad_sha": report.bisect.bad_sha,
                "commands": report.bisect.commands,
                "steps": [
                    {
                        "priority": step.priority,
                        "commit": step.commit.short_sha,
                        "description": step.description,
                        "estimated_minutes": step.estimated_minutes,
                    }
                    for step in report.bisect.steps
                ],
            }

        with open(output, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=4, ensure_ascii=False)

        return output

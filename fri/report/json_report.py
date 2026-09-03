"""
Firmware Regression Intelligence (FRI)

JSON Report Generator
"""

from __future__ import annotations

import json
from pathlib import Path

from fri.constants import JSON_REPORT


class JsonReport:
    """
    Serializes a RegressionReport into JSON.

    Runtime-only objects (for example GitPython Commit objects)
    are intentionally excluded from serialization.
    """

    # ---------------------------------------------------------

    def render(self, report):

        output = Path(JSON_REPORT)

        output.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        data = {

            "good_sha": report.good_sha,

            "bad_sha": report.bad_sha,

            "failure": report.failure,

            "generated_at": report.generated_at.isoformat(),

            "commits": [],

            "candidates": [],

            "modules": []

        }

        # -----------------------------------------------------
        # Commits
        # -----------------------------------------------------

        for commit in report.commits:

            data["commits"].append({

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

                "merge_commit": commit.is_merge_commit

            })

        # -----------------------------------------------------
        # Candidates
        # -----------------------------------------------------

        for candidate in report.candidates:

            data["candidates"].append({

                "commit": candidate.commit.short_sha,

                "confidence": candidate.confidence,

                "score": candidate.score,

                "matched_domains": candidate.matched_domains,

                "matched_keywords": candidate.matched_keywords,

                "matched_files": candidate.matched_files,

                "reasons": candidate.reasons,

                "evidence": candidate.evidence

            })

        # -----------------------------------------------------
        # Modules
        # -----------------------------------------------------

        for module in report.modules:

            data["modules"].append({

                "name": module.name,

                "confidence": module.confidence,

                "commits": [

                    commit.short_sha

                    for commit in module.commits

                ],

                "jiras": module.jiras,

                "authors": module.authors,

                "files": module.files,

                "reasons": module.reasons

            })

        # -----------------------------------------------------
        # Bisect Plan
        # -----------------------------------------------------

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

                        "estimated_minutes": step.estimated_minutes

                    }

                    for step in report.bisect.steps

                ]

            }

        # -----------------------------------------------------
        # Write JSON
        # -----------------------------------------------------

        with open(
            output,
            "w",
            encoding="utf-8"
        ) as fp:

            json.dump(

                data,

                fp,

                indent=4,

                ensure_ascii=False

            )

        return output
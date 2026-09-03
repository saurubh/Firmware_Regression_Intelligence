"""
Firmware Regression Intelligence (FRI)

Module Analyzer

Aggregates regression candidates into firmware modules.

No printing.
No report generation.
"""

from __future__ import annotations

from collections import defaultdict

from fri.models import (
    ModuleCandidate,
    RegressionCandidate,
)


class ModuleAnalyzer:
    """
    Aggregates commit-level regression candidates
    into firmware module candidates.
    """

    # ======================================================

    def analyze(
        self,
        candidates: list[RegressionCandidate]
    ) -> list[ModuleCandidate]:

        groups = defaultdict(list)

        #
        # Group candidates by matched firmware domain.
        #
        for candidate in candidates:

            domains = (

                candidate.matched_domains

                if candidate.matched_domains

                else ["Unknown"]

            )

            for domain in domains:

                groups[domain].append(candidate)

        modules: list[ModuleCandidate] = []

        #
        # Aggregate every firmware module
        #
        for name, group in groups.items():

            modules.append(

                self._build_module(

                    name,

                    group

                )

            )

        modules.sort(

            key=lambda m: m.confidence,

            reverse=True

        )

        return modules

    # ======================================================

    def _build_module(

        self,

        name: str,

        candidates: list[RegressionCandidate]

    ) -> ModuleCandidate:

        commits = []

        commit_sha = set()

        jiras = set()

        merge_requests = set()

        authors = set()

        files = set()

        reasons = set()

        confidence = int(

            sum(

                c.confidence

                for c in candidates

            )

            /

            len(candidates)

        )

        for candidate in candidates:

            commit = candidate.commit

            if commit.sha not in commit_sha:

                commits.append(commit)

                commit_sha.add(commit.sha)

            if commit.jira:

                jiras.add(commit.jira)

            if commit.merge_request:

                merge_requests.add(

                    commit.merge_request

                )

            authors.add(

                commit.author

            )

            files.update(

                candidate.matched_files

            )

            reasons.update(

                candidate.reasons

            )

        return ModuleCandidate(

            name=name,

            confidence=confidence,

            commits=commits,

            jiras=sorted(jiras),

            merge_requests=sorted(

                merge_requests

            ),

            authors=sorted(authors),

            files=sorted(files),

            reasons=sorted(reasons)

        )
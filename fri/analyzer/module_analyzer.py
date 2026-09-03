"""
Firmware Regression Intelligence (FRI)

Module Analyzer

Aggregates regression candidates into firmware modules.
Confidence is evidence-weighted: independent corroborating commits
outrank a single lucky high-confidence commit.
"""

from __future__ import annotations

import math
from collections import defaultdict

from fri.models import ModuleCandidate, RegressionCandidate


class ModuleAnalyzer:
    def analyze(self, candidates: list[RegressionCandidate]) -> list[ModuleCandidate]:
        groups: dict[str, list[RegressionCandidate]] = defaultdict(list)
        for candidate in candidates:
            domains = candidate.matched_domains or ["Unknown"]
            for domain in domains:
                groups[domain].append(candidate)

        built = [self._build_module(name, group) for name, group in groups.items()]
        peak = max((module.strength for module in built), default=0.0)
        for module in built:
            if peak <= 0:
                module.confidence = 0
            else:
                module.confidence = max(
                    1, min(100, int(round(100.0 * module.strength / peak)))
                )
        built.sort(key=lambda module: (module.confidence, len(module.commits)), reverse=True)
        return built

    def _build_module(
        self,
        name: str,
        candidates: list[RegressionCandidate],
    ) -> ModuleCandidate:
        commits = []
        commit_sha: set[str] = set()
        jiras: set[str] = set()
        merge_requests: set[str] = set()
        authors: set[str] = set()
        files: set[str] = set()
        reasons: set[str] = set()
        total_score = 0

        for candidate in candidates:
            commit = candidate.commit
            total_score += candidate.score
            if commit.sha not in commit_sha:
                commits.append(commit)
                commit_sha.add(commit.sha)
            if commit.jira:
                jiras.add(commit.jira)
            if commit.merge_request:
                merge_requests.add(commit.merge_request)
            authors.add(commit.author)
            files.update(candidate.matched_files)
            reasons.update(candidate.reasons)

        n = max(len(commit_sha), 1)
        strength = total_score * math.sqrt(n)
        return ModuleCandidate(
            name=name,
            confidence=0,
            strength=round(strength, 3),
            commits=commits,
            jiras=sorted(jiras),
            merge_requests=sorted(merge_requests),
            authors=sorted(authors),
            files=sorted(files),
            reasons=sorted(reasons),
        )

"""
Firmware Regression Intelligence (FRI)

Firmware Classifier

Maps modified source files into firmware domains using the YAML taxonomy.
"""

from __future__ import annotations

from collections import defaultdict

from fri.config import config
from fri.models import Commit
from fri.utils.matching import compact_token, path_matches


class FirmwareClassifier:
    """Classifies commits into firmware domains. No scoring."""

    def __init__(self):
        self.domains = config.domains_spec
        self.keyword_domains = config.keyword_domains()

    def classify(self, commit: Commit) -> Commit:
        file_weights = self._classify_files(commit.files)
        keyword_weights = self._classify_keywords(commit.keywords)

        combined: dict[str, float] = defaultdict(float)
        for domain, weight in file_weights.items():
            combined[domain] += weight
        for domain, weight in keyword_weights.items():
            combined[domain] += weight * 0.5

        ordered = sorted(combined, key=lambda name: (-combined[name], name))
        commit.domains = ordered
        commit.primary_domain = ordered[0] if ordered else "Unknown"
        return commit

    def classify_files(self, files: list[str]) -> list[str]:
        weights = self._classify_files(files)
        return sorted(weights, key=lambda name: (-weights[name], name))

    def classify_keywords(self, keywords: list[str]) -> list[str]:
        weights = self._classify_keywords(keywords)
        return [name for name, _ in sorted(weights.items(), key=lambda item: -item[1])]

    def _classify_files(self, files: list[str]) -> dict[str, float]:
        weights: dict[str, float] = defaultdict(float)
        for filename in files:
            for spec in self.domains.values():
                best = 0.0
                for pattern in spec.paths:
                    if path_matches(filename, pattern):
                        best = max(best, 1.0 + min(len(pattern), 24) / 24.0)
                if best:
                    weights[spec.name] += best
        return dict(weights)

    def _classify_keywords(self, keywords: list[str]) -> dict[str, float]:
        weights: dict[str, float] = defaultdict(float)
        for keyword in keywords:
            domain = self.keyword_domains.get(compact_token(keyword))
            if domain:
                weights[domain] += 1.0
        return dict(weights)

    def summary(self, commit: Commit) -> str:
        if not commit.domains:
            return "Unknown"
        return ", ".join(commit.domains)

"""
Firmware Regression Intelligence (FRI)

Firmware Classifier

Maps modified source files into firmware domains.

This class contains no scoring logic. It only determines
which firmware domains are affected by a commit.
"""

from __future__ import annotations

from typing import Dict
from typing import List
from typing import Set

from fri.config import config
from fri.models import Commit


class FirmwareClassifier:
    """
    Classifies commits into firmware domains using
    configurable path mappings.
    """

    def __init__(self):

        self.rules: Dict[str, List[str]] = config.component_map

    # ======================================================
    # Public API
    # ======================================================

    def classify(self, commit: Commit) -> Commit:

        domains = self.classify_files(commit.files)

        commit.domains = domains

        if domains:

            #
            # Stable ordering
            #
            commit.primary_domain = domains[0]

        else:

            commit.primary_domain = "Unknown"

        return commit

    # ======================================================

    def classify_files(
        self,
        files: List[str]
    ) -> List[str]:

        matched: Set[str] = set()

        for filename in files:

            normalized = self._normalize(filename)

            for domain, patterns in self.rules.items():

                if self._matches(normalized, patterns):

                    matched.add(domain)

        return sorted(matched)

    # ======================================================

    def summary(self, commit: Commit) -> str:

        if not commit.domains:

            return "Unknown"

        return ", ".join(commit.domains)

    # ======================================================
    # Internal Helpers
    # ======================================================

    @staticmethod
    def _normalize(path: str) -> str:

        return (

            path

            .replace("\\", "/")

            .lower()

            .strip()

        )

    @staticmethod
    def _matches(
        filename: str,
        patterns: List[str]
    ) -> bool:

        for pattern in patterns:

            if pattern in filename:

                return True

        return False
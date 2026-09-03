"""
Firmware Regression Intelligence (FRI)

Diff Analyzer

Analyzes Git diffs and extracts firmware-relevant
signals used by the Candidate Engine.
"""

from __future__ import annotations

import re
from typing import Set

from fri.models import DiffEvidence


class DiffAnalyzer:
    """
    Extracts firmware evidence from Git diffs.

    This class does NOT rank commits.
    It only extracts evidence.
    """

    #
    # Firmware keywords
    #
    KEYWORDS = {

        "BOOT",
        "BOOTGUARD",
        "MEASUREDBOOT",
        "SECUREBOOT",

        "MRC",
        "MEMORY",
        "DIMM",
        "DDR",

        "PCI",
        "PCIE",
        "ACPI",
        "RAS",
        "NUMA",
        "SNC",
        "CXL",

        "FIT",
        "TPM",
        "PCR",

        "PEI",
        "DXE",
        "SMM",

        "POLICY",
        "PLATFORM",

        "SETUP",
        "VARIABLE",
        "PCD"
    }

    #
    # Regex
    #
    FUNCTION_REGEX = re.compile(

        r"^[\+\-].*?\b([A-Za-z_][A-Za-z0-9_]*)\s*\("

    )

    MACRO_REGEX = re.compile(

        r"^[\+\-]\s*#define\s+([A-Za-z0-9_]+)"

    )

    # ======================================================

    def analyze(
        self,
        diff_text: str
    ) -> DiffEvidence:

        evidence = DiffEvidence()

        if not diff_text:

            return evidence

        keywords: Set[str] = set()

        functions: Set[str] = set()

        macros: Set[str] = set()

        for line in diff_text.splitlines():

            #
            # Ignore diff headers
            #
            if line.startswith("+++") or line.startswith("---"):

                continue

            #
            # Added / Removed
            #
            if line.startswith("+"):

                evidence.added_lines += 1

            elif line.startswith("-"):

                evidence.removed_lines += 1

            upper = line.upper()

            #
            # Firmware keywords
            #
            for keyword in self.KEYWORDS:

                if keyword in upper:

                    keywords.add(keyword)

            #
            # Functions
            #
            match = self.FUNCTION_REGEX.match(line)

            if match:

                functions.add(

                    match.group(1)

                )

            #
            # Macros
            #
            match = self.MACRO_REGEX.match(line)

            if match:

                macros.add(

                    match.group(1)

                )

        #
        # Stable ordering
        #
        evidence.firmware_keywords = sorted(keywords)

        evidence.modified_functions = sorted(functions)

        evidence.modified_macros = sorted(macros)

        evidence.tokens = (

            evidence.firmware_keywords +

            evidence.modified_functions +

            evidence.modified_macros

        )

        #
        # Evidence score
        #
        evidence.score = self._score(evidence)

        return evidence

    # ======================================================

    @staticmethod
    def _score(
        evidence: DiffEvidence
    ) -> int:

        score = 0

        score += len(

            evidence.firmware_keywords

        ) * 5

        score += len(

            evidence.modified_functions

        ) * 3

        score += len(

            evidence.modified_macros

        ) * 2

        score += min(

            evidence.total_lines // 20,

            20

        )

        return score
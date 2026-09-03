"""
Firmware Regression Intelligence (FRI)

Diff Analyzer

Analyzes Git diffs and extracts firmware-relevant
signals used by the Candidate Engine.
"""

from __future__ import annotations

import re

from fri.analyzer.hazard_detector import HazardDetector
from fri.config import config
from fri.models import DiffEvidence
from fri.utils.matching import KeywordIndex


class DiffAnalyzer:
    """
    Extracts firmware evidence from Git diffs.

    This class does NOT rank commits.
    Keywords come from the YAML taxonomy.
    """

    FUNCTION_REGEX = re.compile(r"^[\+\-].*?\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")

    MACRO_REGEX = re.compile(r"^[\+\-]\s*#define\s+([A-Za-z0-9_]+)")

    FILE_HEADER = re.compile(r"^\+\+\+\s+b/(.+)$")

    def __init__(self) -> None:
        self.hazards = HazardDetector()
        self.keywords = config.keywords()
        self._keyword_index = KeywordIndex(self.keywords)

    def analyze(self, diff_text: str) -> DiffEvidence:
        evidence = DiffEvidence()

        if not diff_text:
            return evidence

        keywords: set[str] = set()
        functions: set[str] = set()
        macros: set[str] = set()
        files: set[str] = set()
        changed_chunks: list[str] = []
        hot_limit = 3000

        for line in diff_text.splitlines():
            file_match = self.FILE_HEADER.match(line)
            if file_match:
                files.add(file_match.group(1))
                continue

            if line.startswith("+++") or line.startswith("---"):
                continue

            if line.startswith("+"):
                evidence.added_lines += 1
            elif line.startswith("-"):
                evidence.removed_lines += 1
            else:
                continue

            if len(changed_chunks) < hot_limit:
                changed_chunks.append(line)
                match = self.FUNCTION_REGEX.match(line)
                if match:
                    functions.add(match.group(1))
                match = self.MACRO_REGEX.match(line)
                if match:
                    macros.add(match.group(1))

        changed = "\n".join(changed_chunks)
        keywords.update(self._keyword_index.find(changed))

        evidence.firmware_keywords = sorted(keywords)
        evidence.modified_functions = sorted(functions)
        evidence.modified_macros = sorted(macros)
        evidence.modified_files = sorted(files)
        evidence.tokens = (
            evidence.firmware_keywords
            + evidence.modified_functions
            + evidence.modified_macros
        )
        evidence.hazards = self.hazards.detect(changed)
        evidence.pcd_names = self.hazards.pcd_names(changed)
        evidence.protocol_hits = self.hazards.protocol_hits(changed)
        evidence.boot_api_hits = self.hazards.boot_api_hits(changed)
        evidence.comment_only = self.hazards.comment_only(changed)
        evidence.score = self._score(evidence)
        return evidence

    @staticmethod
    def _score(evidence: DiffEvidence) -> int:
        score = 0
        score += len(evidence.firmware_keywords) * 5
        score += len(evidence.modified_functions) * 3
        score += len(evidence.modified_macros) * 2
        score += min(evidence.total_lines // 20, 20)
        score += sum(12 if h.severity == "high" else 6 for h in evidence.hazards)
        score += min(len(evidence.boot_api_hits) * 8, 24)
        score += min(len(evidence.pcd_names) * 2, 10)
        if evidence.comment_only:
            score = max(0, score - 20)
        return score

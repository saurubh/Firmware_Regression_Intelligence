"""
Firmware Regression Intelligence (FRI)

Diff Analyzer

Analyzes Git diffs and extracts firmware-relevant
signals used by the Candidate Engine.
"""

from __future__ import annotations

import re

from fri.analyzer.hazard_detector import HazardDetector
from fri.models import DiffEvidence


class DiffAnalyzer:
    """
    Extracts firmware evidence from Git diffs.

    This class does NOT rank commits.
    It only extracts evidence.
    """

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
        "BDS",
        "POLICY",
        "PLATFORM",
        "SETUP",
        "VARIABLE",
        "PCD",
        "FSP",
        "UPD",
        "IOMMU",
        "VTD",
        "DMAR",
        "SMBIOS",
        "LINUXBOOT",
        "GRUB",
        "KERNEL",
        "EXITBOOTSERVICES",
        "GETMEMORYMAP",
        "LOADIMAGE",
        "STARTIMAGE",
        "BOOTORDER",
        "WATCHDOG",
        "IPMI",
        "BMC",
        "USB",
        "NVME",
        "PXE",
        "GOP",
        "CSM",
        "RESUME",
        "S3",
        "MICROCODE",
        "MADT",
        "SRAT",
        "DSDT",
        "KEXEC",
        "EFISTUB",
        "SHIM",
    }

    FUNCTION_REGEX = re.compile(r"^[\+\-].*?\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")

    MACRO_REGEX = re.compile(r"^[\+\-]\s*#define\s+([A-Za-z0-9_]+)")

    FILE_HEADER = re.compile(r"^\+\+\+\s+b/(.+)$")

    def __init__(self) -> None:
        self.hazards = HazardDetector()

    def analyze(self, diff_text: str) -> DiffEvidence:
        evidence = DiffEvidence()

        if not diff_text:
            return evidence

        keywords: set[str] = set()
        functions: set[str] = set()
        macros: set[str] = set()
        files: set[str] = set()

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

            upper = line.upper()

            for keyword in self.KEYWORDS:
                if re.search(
                    rf"(?<![A-Z0-9_]){re.escape(keyword)}(?![A-Z0-9_])",
                    upper,
                ):
                    keywords.add(keyword)

            match = self.FUNCTION_REGEX.match(line)
            if match:
                functions.add(match.group(1))

            match = self.MACRO_REGEX.match(line)
            if match:
                macros.add(match.group(1))

        evidence.firmware_keywords = sorted(keywords)
        evidence.modified_functions = sorted(functions)
        evidence.modified_macros = sorted(macros)
        evidence.modified_files = sorted(files)
        evidence.tokens = (
            evidence.firmware_keywords
            + evidence.modified_functions
            + evidence.modified_macros
        )
        evidence.hazards = self.hazards.detect(diff_text)
        evidence.pcd_names = self.hazards.pcd_names(diff_text)
        evidence.protocol_hits = self.hazards.protocol_hits(diff_text)
        evidence.boot_api_hits = self.hazards.boot_api_hits(diff_text)
        evidence.comment_only = self.hazards.comment_only(diff_text)
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

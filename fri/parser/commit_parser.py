"""
Firmware Regression Intelligence (FRI)

Commit Parser

Extracts structured metadata from firmware commit messages.
"""

from __future__ import annotations

import re

from fri.models import Commit


class CommitParser:
    """Parses firmware commit messages."""

    JIRA_PATTERNS = [
        re.compile(r"(UEFIRM-\d+)", re.IGNORECASE),
        re.compile(r"(LXPM-\d+)", re.IGNORECASE),
        re.compile(r"(BIOS-\d+)", re.IGNORECASE),
        re.compile(r"(BUG-\d+)", re.IGNORECASE),
        re.compile(r"(CVE-\d{4}-\d+)", re.IGNORECASE),
        re.compile(r"([A-Z][A-Z0-9]+-\d+)"),
    ]

    MR_PATTERN = re.compile(r"!(\d+)")

    INTENT_PATTERNS = {
        re.compile(r"\brevert\b", re.IGNORECASE): "Revert",
        re.compile(r"\bworkaround\b", re.IGNORECASE): "Workaround",
        re.compile(r"\bhotfix\b", re.IGNORECASE): "Fix",
        re.compile(r"\bfix\b", re.IGNORECASE): "Fix",
        re.compile(r"\bdisable\b", re.IGNORECASE): "Disable",
        re.compile(r"\benable\b", re.IGNORECASE): "Enable",
        re.compile(r"\bupdate\b", re.IGNORECASE): "Update",
        re.compile(r"\bremove\b", re.IGNORECASE): "Remove",
        re.compile(r"\bcleanup\b", re.IGNORECASE): "Cleanup",
        re.compile(r"\brefactor\b", re.IGNORECASE): "Refactor",
        re.compile(r"\bsupport\b", re.IGNORECASE): "Support",
        re.compile(r"\badd\b", re.IGNORECASE): "Add",
        re.compile(r"\bhangs?\b", re.IGNORECASE): "Hang",
        re.compile(r"\bpanic\b", re.IGNORECASE): "Panic",
    }

    FEATURE_KEYWORDS = {
        "TPM",
        "MRC",
        "RAS",
        "FIT",
        "PXE",
        "ACPI",
        "PCIE",
        "DDR",
        "DIMM",
        "NVME",
        "CXL",
        "BOOT",
        "SECURE BOOT",
        "MEASURED BOOT",
        "PLATFORM",
        "NUMA",
        "SNC",
        "OS BOOT",
        "EXITBOOTSERVICES",
        "LINUXBOOT",
        "GRUB",
        "KERNEL",
        "IOMMU",
        "VT-D",
        "SMBIOS",
        "FSP",
        "SMM",
        "S3",
        "WATCHDOG",
        "IPMI",
        "BMC",
        "USB",
        "GOP",
        "CSM",
        "PEI",
        "DXE",
        "BDS",
        "PCR",
        "SHIM",
        "KEXEC",
    }

    def parse(self, commit: Commit) -> Commit:
        message = commit.message
        upper = message.upper()
        commit.jira = self._parse_jira(message)
        commit.merge_request = self._parse_merge_request(message)
        commit.is_merge_commit = commit.is_merge_commit or message.startswith("Merge")
        commit.intent = self._parse_intent(message)
        commit.keywords = sorted(self._parse_keywords(upper))
        return commit

    def _parse_jira(self, message: str):
        for pattern in self.JIRA_PATTERNS:
            match = pattern.search(message)
            if match:
                return match.group(1)
        return None

    def _parse_merge_request(self, message: str):
        match = self.MR_PATTERN.search(message)
        if match:
            return match.group(1)
        return None

    def _parse_intent(self, message: str):
        for pattern, intent in self.INTENT_PATTERNS.items():
            if pattern.search(message):
                return intent
        return "Unknown"

    def _parse_keywords(self, message: str):
        keywords = set()
        for keyword in self.FEATURE_KEYWORDS:
            if keyword in message:
                keywords.add(keyword)
        return keywords

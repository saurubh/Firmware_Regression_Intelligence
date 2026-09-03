"""
Firmware Regression Intelligence (FRI)

Firmware Classifier

Maps modified source files into firmware domains.

This class contains no scoring logic. It only determines
which firmware domains are affected by a commit.
"""

from __future__ import annotations

from fri.config import config
from fri.models import Commit


class FirmwareClassifier:
    """
    Classifies commits into firmware domains using
    configurable path mappings and keyword hints.
    """

    KEYWORD_DOMAINS = {
        "ACPI": "ACPI",
        "SMBIOS": "SMBIOS",
        "LINUXBOOT": "LinuxBoot",
        "OS BOOT": "OSLoader",
        "EXITBOOTSERVICES": "OSLoader",
        "IOMMU": "IOMMU",
        "VT-D": "IOMMU",
        "TPM": "TPM",
        "SECURE BOOT": "Security",
        "MEASURED BOOT": "MeasuredBoot",
        "PCIE": "PCIe",
        "NVME": "Storage",
        "PXE": "Network",
        "MRC": "Memory",
        "FSP": "FSP",
        "SMM": "SMM",
        "GRUB": "OSLoader",
        "KERNEL": "OSLoader",
        "KEXEC": "LinuxBoot",
        "SHIM": "OSLoader",
        "BDS": "BDS",
        "PEI": "PEI",
        "DXE": "DXE",
        "WATCHDOG": "Watchdog",
        "IPMI": "IPMI",
        "BMC": "BMC",
        "GOP": "Graphics",
        "CSM": "CSM",
        "S3": "Resume",
        "NUMA": "NUMA",
        "CXL": "CXL",
        "FIT": "FIT",
        "USB": "USB",
        "RAS": "RAS",
    }

    def __init__(self):

        self.rules: dict[str, list[str]] = config.component_map

    # ======================================================
    # Public API
    # ======================================================

    def classify(self, commit: Commit) -> Commit:

        domains = self.classify_files(commit.files)
        domains.extend(self.classify_keywords(commit.keywords))
        # Preserve order while dropping duplicates
        commit.domains = list(dict.fromkeys(domains))

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
        files: list[str]
    ) -> list[str]:

        matched: set[str] = set()

        for filename in files:

            normalized = self._normalize(filename)

            for domain, patterns in self.rules.items():

                if self._matches(normalized, patterns):

                    matched.add(domain)

        return sorted(matched)

    def classify_keywords(self, keywords: list[str]) -> list[str]:
        matched: list[str] = []
        for keyword in keywords:
            domain = self.KEYWORD_DOMAINS.get(keyword.upper())
            if domain:
                matched.append(domain)
        return matched

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
        patterns: list[str]
    ) -> bool:

        for pattern in patterns:

            if pattern in filename:

                return True

        return False
"""
Firmware Regression Intelligence (FRI)

Hazard Detector

Finds high-risk firmware and OS-boot changes in unified diffs.
These signals are what typically *cause* regressions, as opposed
to generic keyword hits.
"""

from __future__ import annotations

import re

from fri.models import Hazard

# Each rule: (name, category, severity, regex)
_HAZARD_RULES = (
    (
        "ExitBootServices",
        "os_boot",
        "high",
        re.compile(r"ExitBootServices", re.IGNORECASE),
    ),
    (
        "GetMemoryMap",
        "os_boot",
        "high",
        re.compile(r"GetMemoryMap", re.IGNORECASE),
    ),
    (
        "SetVirtualAddressMap",
        "os_boot",
        "high",
        re.compile(r"SetVirtualAddressMap", re.IGNORECASE),
    ),
    (
        "LoadImage/StartImage",
        "os_boot",
        "high",
        re.compile(r"\b(LoadImage|StartImage)\b", re.IGNORECASE),
    ),
    (
        "BootOrder/Boot####",
        "os_boot",
        "high",
        re.compile(r"\b(BootOrder|BootNext|Boot####|OSIndications)\b", re.IGNORECASE),
    ),
    (
        "ReadyToBoot",
        "boot",
        "high",
        re.compile(r"ReadyToBoot|EVT_SIGNAL_EXIT_BOOT", re.IGNORECASE),
    ),
    (
        "ACPI table",
        "acpi",
        "high",
        re.compile(
            r"\b(DSDT|SSDT|MADT|APIC|SRAT|SLIT|HMAT|MCFG|DMAR|IVRS|FADT|HPET|RSDP|XSDT)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "IOMMU/VT-d",
        "iommu",
        "high",
        re.compile(r"\b(IOMMU|VT-?D|DMAR|IVRS|DmaRemap)\b", re.IGNORECASE),
    ),
    (
        "LinuxBoot/kexec/EFI stub",
        "os_boot",
        "high",
        re.compile(r"\b(LinuxBoot|kexec|EFIStub|efi_stub|bzImage|u-root)\b", re.IGNORECASE),
    ),
    (
        "GRUB/shim/systemd-boot",
        "os_boot",
        "high",
        re.compile(r"\b(grub|shim\.efi|systemd-boot|bootmgfw|winload)\b", re.IGNORECASE),
    ),
    (
        "PCD / UPD default",
        "generic",
        "high",
        re.compile(
            r"(PcdGet|PcdSet|PcdSetEx|gPatch|_PCD_VALUE_|UPD\b|FspsUpd|FspmUpd)",
            re.IGNORECASE,
        ),
    ),
    (
        "Timeout / stall",
        "generic",
        "medium",
        re.compile(r"\b(timeout|TimeOut|Stall\s*\(|MicroSecondDelay|NanoSecondDelay)\b", re.IGNORECASE),
    ),
    (
        "ASSERT / NULL",
        "generic",
        "medium",
        re.compile(r"\b(ASSERT\s*\(|NULL)\b"),
    ),
    (
        "Watchdog",
        "watchdog",
        "high",
        re.compile(r"\b(Watchdog|Wdt|TcoReset|WDT_)\b", re.IGNORECASE),
    ),
    (
        "Secure Boot policy",
        "security",
        "high",
        re.compile(r"\b(SecureBoot|EFI_IMAGE_SECURITY|dbx|Authenticate)\b", re.IGNORECASE),
    ),
    (
        "TPM/PCR",
        "tpm",
        "high",
        re.compile(r"\b(Tpm2|Tcg2|PCR|HashLogExtendEvent)\b", re.IGNORECASE),
    ),
    (
        "Runtime services",
        "os_boot",
        "high",
        re.compile(r"\b(gRT->|EfiRuntime|SetVirtualAddress|ResetSystem)\b"),
    ),
    (
        "Boot services table",
        "boot",
        "medium",
        re.compile(r"\b(gBS->|EfiBootServices)\b"),
    ),
    (
        "SMM/SMI",
        "smm",
        "high",
        re.compile(r"\b(Smm|SMI|Smram|SmmCommunicate)\b", re.IGNORECASE),
    ),
    (
        "Feature disable/enable",
        "generic",
        "medium",
        re.compile(r"\b(PcdGet.*Enable|FeaturePcd|FIXED_AT_BUILD).*(TRUE|FALSE|0|1)", re.IGNORECASE),
    ),
    (
        "Intel FSP-M / MemoryInit",
        "memory_init",
        "high",
        re.compile(r"\b(FspMemoryInit|FSP-M|FspmUpd|MemoryInit)\b", re.IGNORECASE),
    ),
    (
        "Intel FSP-T / TempRamInit",
        "sec",
        "high",
        re.compile(r"\b(TempRamInit|FSP-T|FsptUpd)\b", re.IGNORECASE),
    ),
    (
        "Intel FSP-S / SiliconInit",
        "silicon_init",
        "high",
        re.compile(r"\b(FspSiliconInit|FSP-S|FspsUpd|NotifyPhase)\b", re.IGNORECASE),
    ),
    (
        "Intel Boot Guard / ACM",
        "reset",
        "high",
        re.compile(r"\b(BootGuard|FIT|BPM_|KM_|GETSEC|ACM)\b"),
    ),
    (
        "AMD AGESA callout",
        "silicon_init",
        "high",
        re.compile(r"\bAmdInit(Reset|Early|Post|Env|Mid|Late)\b", re.IGNORECASE),
    ),
    (
        "AMD PSP / BIOS directory",
        "reset",
        "high",
        re.compile(r"\b(PSP|BiosDirectory|DirAddr)\b", re.IGNORECASE),
    ),
)

_PCD_RE = re.compile(
    r"\b(Pcd[A-Za-z0-9_]+|_PCD_VALUE_[A-Za-z0-9_]+|[A-Za-z0-9_]+Upd[A-Za-z0-9_]*)\b"
)

_PROTOCOL_RE = re.compile(
    r"\b(g[A-Za-z0-9_]+(Protocol|Ppi)Guid|EFI_[A-Z0-9_]+_PROTOCOL)\b"
)

_BOOT_API_RE = re.compile(
    r"\b("
    r"ExitBootServices|GetMemoryMap|LoadImage|StartImage|"
    r"SetVirtualAddressMap|CreateEventEx|ReadyToBoot|"
    r"LocateProtocol|InstallProtocolInterface|InstallConfigurationTable"
    r")\b",
    re.IGNORECASE,
)

_COMMENT_RE = re.compile(r"^[\+\-]\s*(//|\*|#|/\*|\*/)")


class HazardDetector:
    """Extract high-risk change markers from a unified diff."""

    def detect(self, diff_text: str) -> list[Hazard]:
        if not diff_text:
            return []

        blob = _changed_blob(diff_text)
        if not blob:
            return []

        found: dict[str, Hazard] = {}
        for name, category, severity, pattern in _HAZARD_RULES:
            match = pattern.search(blob)
            if not match:
                continue
            start = match.start()
            line_start = blob.rfind("\n", 0, start) + 1
            line_end = blob.find("\n", match.end())
            snippet = blob[line_start : line_end if line_end != -1 else len(blob)]
            found[name] = Hazard(
                name=name,
                category=category,
                severity=severity,
                detail=snippet.lstrip("+-").strip()[:160],
            )
        return list(found.values())

    def pcd_names(self, diff_text: str) -> list[str]:
        names: set[str] = set()
        for match in _PCD_RE.finditer(_changed_blob(diff_text)):
            names.add(match.group(1))
        return sorted(names)

    def protocol_hits(self, diff_text: str) -> list[str]:
        hits: set[str] = set()
        for match in _PROTOCOL_RE.finditer(_changed_blob(diff_text)):
            hits.add(match.group(1))
        return sorted(hits)

    def boot_api_hits(self, diff_text: str) -> list[str]:
        hits: set[str] = set()
        for match in _BOOT_API_RE.finditer(_changed_blob(diff_text)):
            hits.add(match.group(1))
        return sorted(hits)

    def comment_only(self, diff_text: str) -> bool:
        changed = list(_changed_lines(diff_text))
        if not changed:
            return False
        code_lines = [line for line in changed if not _COMMENT_RE.match(line)]
        return len(code_lines) == 0


def _changed_lines(diff_text: str):
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") or line.startswith("-"):
            yield line


def _changed_blob(diff_text: str) -> str:
    return "\n".join(_changed_lines(diff_text))

"""
Firmware Regression Intelligence (FRI)

Project-wide constants.

This file intentionally contains only constants.
Do not place business logic here.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_NAME = "Firmware Regression Intelligence"

SHORT_NAME = "FRI"

VERSION = "2.0.0"

ROOT_DIR = Path(__file__).resolve().parent.parent

CONFIG_DIR = ROOT_DIR / "config"

OUTPUT_DIR = ROOT_DIR / "output"

LOG_DIR = ROOT_DIR / "logs"

TEMPLATE_DIR = ROOT_DIR / "templates"

COMPONENT_MAP = CONFIG_DIR / "component_map.yaml"

FAILURE_PROFILE = CONFIG_DIR / "failure_profiles.yaml"

CONFIG_FILE = CONFIG_DIR / "config.yaml"

HTML_REPORT = OUTPUT_DIR / "report.html"

JSON_REPORT = OUTPUT_DIR / "report.json"

LOG_FILE = LOG_DIR / "fri.log"

# Firmware / silicon boot (SEC → PEI → DXE → BDS)
FAILURE_BOOT = "boot"

# Firmware-to-OS handoff (Linux, Windows, LinuxBoot, GRUB, EFI stub)
FAILURE_OS_BOOT = "os_boot"

FAILURE_MEMORY = "memory"
FAILURE_PCIE = "pcie"
FAILURE_NETWORK = "network"
FAILURE_STORAGE = "storage"
FAILURE_SECURITY = "security"
FAILURE_POWER = "power"
FAILURE_ACPI = "acpi"
FAILURE_RAS = "ras"
FAILURE_CXL = "cxl"
FAILURE_TPM = "tpm"
FAILURE_SMM = "smm"
FAILURE_USB = "usb"
FAILURE_GRAPHICS = "graphics"
FAILURE_BMC = "bmc"
FAILURE_THERMAL = "thermal"
FAILURE_RESUME = "resume"
FAILURE_SMBIOS = "smbios"
FAILURE_CPU = "cpu"
FAILURE_FIT = "fit"
FAILURE_MEASURED_BOOT = "measured_boot"
FAILURE_SECURE_BOOT = "secure_boot"
FAILURE_WATCHDOG = "watchdog"
FAILURE_SERIAL = "serial"
FAILURE_IPMI = "ipmi"
FAILURE_ME = "me"
FAILURE_GPIO = "gpio"
FAILURE_VARIABLE = "variable"
FAILURE_CAPSULE = "capsule"
FAILURE_IOMMU = "iommu"
FAILURE_NUMA = "numa"
FAILURE_CSM = "csm"
FAILURE_LINUXBOOT = "linuxboot"
FAILURE_FSP = "fsp"
FAILURE_GENERIC = "generic"

SUPPORTED_FAILURES = (
    FAILURE_BOOT,
    FAILURE_OS_BOOT,
    FAILURE_MEMORY,
    FAILURE_PCIE,
    FAILURE_NETWORK,
    FAILURE_STORAGE,
    FAILURE_SECURITY,
    FAILURE_POWER,
    FAILURE_ACPI,
    FAILURE_RAS,
    FAILURE_CXL,
    FAILURE_TPM,
    FAILURE_SMM,
    FAILURE_USB,
    FAILURE_GRAPHICS,
    FAILURE_BMC,
    FAILURE_THERMAL,
    FAILURE_RESUME,
    FAILURE_SMBIOS,
    FAILURE_CPU,
    FAILURE_FIT,
    FAILURE_MEASURED_BOOT,
    FAILURE_SECURE_BOOT,
    FAILURE_WATCHDOG,
    FAILURE_SERIAL,
    FAILURE_IPMI,
    FAILURE_ME,
    FAILURE_GPIO,
    FAILURE_VARIABLE,
    FAILURE_CAPSULE,
    FAILURE_IOMMU,
    FAILURE_NUMA,
    FAILURE_CSM,
    FAILURE_LINUXBOOT,
    FAILURE_FSP,
    FAILURE_GENERIC,
)

# Topics that commonly co-occur with OS boot failures.
OS_BOOT_RELATED_TOPICS = (
    FAILURE_BOOT,
    FAILURE_ACPI,
    FAILURE_SMBIOS,
    FAILURE_IOMMU,
    FAILURE_MEMORY,
    FAILURE_PCIE,
    FAILURE_VARIABLE,
    FAILURE_GRAPHICS,
    FAILURE_STORAGE,
    FAILURE_NETWORK,
    FAILURE_LINUXBOOT,
    FAILURE_SECURE_BOOT,
    FAILURE_MEASURED_BOOT,
    FAILURE_NUMA,
    FAILURE_CSM,
    FAILURE_SERIAL,
)

MAX_CONFIDENCE = 100
HIGH_CONFIDENCE = 80
MEDIUM_CONFIDENCE = 60
LOW_CONFIDENCE = 30

DOC_SUFFIXES = (
    ".md",
    ".rst",
    ".txt",
    ".html",
    ".htm",
    ".adoc",
)

DOC_NAMES = (
    "changelog",
    "readme",
    "license",
    "authors",
    "notice",
    "copying",
)

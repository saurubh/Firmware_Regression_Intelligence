"""
Firmware Regression Intelligence (FRI)

Project-wide constants.

Failure topics and firmware keywords live in YAML under config/.
Do not add new --failure names here.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_NAME = "Firmware Regression Intelligence"

SHORT_NAME = "FRI"

VERSION = "2.6.1"

ROOT_DIR = Path(__file__).resolve().parent.parent

CONFIG_DIR = ROOT_DIR / "config"

OUTPUT_DIR = ROOT_DIR / "output"

LOG_DIR = ROOT_DIR / "logs"

TEMPLATE_DIR = ROOT_DIR / "templates"

COMPONENT_MAP = CONFIG_DIR / "component_map.yaml"

BOOT_PHASES = CONFIG_DIR / "boot_phases.yaml"

FAILURE_PROFILE = CONFIG_DIR / "failure_profiles.yaml"

CONFIG_FILE = CONFIG_DIR / "config.yaml"

HTML_REPORT = OUTPUT_DIR / "report.html"

JSON_REPORT = OUTPUT_DIR / "report.json"

LOG_FILE = LOG_DIR / "fri.log"

FAILURE_BOOT = "boot"
FAILURE_OS_BOOT = "os_boot"

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

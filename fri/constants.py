"""
Firmware Regression Intelligence (FRI)

Project-wide constants.

This file intentionally contains only constants.
Do not place business logic here.
"""

from __future__ import annotations

from pathlib import Path

# ==========================================================
# Project Information
# ==========================================================

PROJECT_NAME = "Firmware Regression Intelligence"

SHORT_NAME = "FRI"

VERSION = "1.0.0"

# ==========================================================
# Paths
# ==========================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

CONFIG_DIR = ROOT_DIR / "config"

OUTPUT_DIR = ROOT_DIR / "output"

LOG_DIR = ROOT_DIR / "logs"

TEMPLATE_DIR = ROOT_DIR / "templates"

# ==========================================================
# Default Files
# ==========================================================

COMPONENT_MAP = CONFIG_DIR / "component_map.yaml"

FAILURE_PROFILE = CONFIG_DIR / "failure_profiles.yaml"

CONFIG_FILE = CONFIG_DIR / "config.yaml"

# ==========================================================
# Report Files
# ==========================================================

HTML_REPORT = OUTPUT_DIR / "report.html"

JSON_REPORT = OUTPUT_DIR / "report.json"

LOG_FILE = LOG_DIR / "fri.log"

# ==========================================================
# Failure Types
# ==========================================================

FAILURE_BOOT = "boot"

FAILURE_MEMORY = "memory"

FAILURE_PCIE = "pcie"

FAILURE_NETWORK = "network"

FAILURE_STORAGE = "storage"

FAILURE_SECURITY = "security"

FAILURE_POWER = "power"

SUPPORTED_FAILURES = (

    FAILURE_BOOT,

    FAILURE_MEMORY,

    FAILURE_PCIE,

    FAILURE_NETWORK,

    FAILURE_STORAGE,

    FAILURE_SECURITY,

    FAILURE_POWER,

)

# ==========================================================
# Confidence
# ==========================================================

MAX_CONFIDENCE = 100

HIGH_CONFIDENCE = 80

MEDIUM_CONFIDENCE = 60

LOW_CONFIDENCE = 30

"""
Firmware Regression Intelligence (FRI)

Command Line Interface
"""

from __future__ import annotations

import argparse

from fri.config import config
from fri.constants import PROJECT_NAME, VERSION


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fri",
        description=PROJECT_NAME,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    investigate = subparsers.add_parser(
        "investigate",
        help="Investigate a firmware or OS-boot regression",
    )
    investigate.add_argument("--repo", required=True, help="Path to Git repository")
    investigate.add_argument("--good", required=True, help="Known-good build, tag or commit")
    investigate.add_argument("--bad", required=True, help="Known-bad build, tag or commit")
    investigate.add_argument(
        "--failure",
        required=True,
        choices=config.failure_names,
        help="Regression failure profile from config/failure_profiles.yaml",
    )
    investigate.add_argument("--top", type=int, default=10, help="Maximum number of candidates")
    investigate.add_argument("--html", action="store_true", help="Generate HTML dashboard")
    investigate.add_argument("--json", action="store_true", help="Generate JSON report")
    investigate.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    subparsers.add_parser("doctor", help="Validate FRI installation and list profiles")
    subparsers.add_parser("config", help="Display loaded configuration")
    subparsers.add_parser(
        "topics",
        help="List every regression topic FRI can analyze",
    )
    subparsers.add_parser(
        "phases",
        help="List CPU-reset-to-OS boot phases used for triage",
    )
    return parser

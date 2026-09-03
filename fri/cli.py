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
        help="Investigate a firmware regression (one repo or a BIOS workspace)",
    )
    source = investigate.add_mutually_exclusive_group(required=True)
    source.add_argument("--repo", help="Single Git repository")
    source.add_argument(
        "--workspace",
        help="BIOS superproject (.gitmodules + nested Git clones). "
        "For a gitman tree (Edk2, Intel, Lenovo, …) use --gitman instead.",
    )
    source.add_argument(
        "--gitman",
        help="gitman.yml: investigate every sources[].name clone (and other "
        "Git worktrees under location). Required for Birch Stream gitman trees.",
    )
    source.add_argument(
        "--manifest",
        help="YAML pin-set listing each repo's good and bad SHA",
    )
    investigate.add_argument(
        "--good",
        help="Known-good BIOS tag, branch or commit. "
        "With --workspace or --gitman, this same name is looked up in every listed repo.",
    )
    investigate.add_argument(
        "--bad",
        help="Known-bad BIOS tag, branch or commit. "
        "With --workspace or --gitman, this same name is looked up in every listed repo.",
    )
    investigate.add_argument(
        "--failure",
        required=True,
        choices=config.failure_names,
        help="Regression failure profile from config/failure_profiles.yaml",
    )
    investigate.add_argument("--top", type=int, default=10, help="Maximum number of candidates")
    investigate.add_argument(
        "--workers",
        type=int,
        default=None,
        metavar="N",
        help="Parallel commit analysis threads (default from config; 1 = sequential)",
    )
    investigate.add_argument(
        "--fast",
        action="store_true",
        help="Faster run: parallel workers + skip diffs on binary-only commits",
    )
    investigate.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore saved progress and re-analyze every commit (default is resume)",
    )
    investigate.add_argument("--html", action="store_true", help="Generate HTML dashboard")
    investigate.add_argument("--json", action="store_true", help="Generate JSON report")
    investigate.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    pins = subparsers.add_parser(
        "pins",
        help="Show which submodules/repos moved between two BIOS builds",
    )
    pin_src = pins.add_mutually_exclusive_group(required=True)
    pin_src.add_argument("--workspace", help="BIOS superproject path")
    pin_src.add_argument(
        "--gitman",
        help="gitman.yml listing Edk2/Intel/Lenovo folders",
    )
    pins.add_argument(
        "--good",
        required=True,
        help="Known-good tag or commit (searched in each sub-repo, then gitlink)",
    )
    pins.add_argument(
        "--bad",
        required=True,
        help="Known-bad tag or commit (searched in each sub-repo, then gitlink)",
    )

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

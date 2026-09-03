"""
Firmware Regression Intelligence (FRI)

Application Entry Point
"""

from __future__ import annotations

import sys

from fri.cli import build_parser
from fri.engine.investigation_engine import InvestigationEngine
from fri.logger import logger
from fri.report.console_report import ConsoleReport
from fri.report.html_report import HtmlReport
from fri.report.json_report import JsonReport


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "doctor":
        return _doctor()

    if args.command == "config":
        from fri.config import config

        print(config.settings)
        return 0

    if args.command == "topics":
        return _topics()

    if args.command == "phases":
        return _phases()

    if args.command != "investigate":
        print("Unknown command.")
        return 1

    logger.info("=" * 80)
    logger.info("Firmware Regression Intelligence")
    logger.info("=" * 80)
    logger.info("Repository   : %s", args.repo)
    logger.info("Good Build   : %s", args.good)
    logger.info("Bad Build    : %s", args.bad)
    logger.info("Failure Type : %s", args.failure)

    try:
        report = InvestigationEngine(args.repo).investigate(
            good=args.good,
            bad=args.bad,
            failure=args.failure,
        )
        ConsoleReport().render(report, top=args.top)
        if args.html:
            output = HtmlReport().render(report, top=args.top)
            logger.info("HTML report : %s", output)
        if args.json:
            output = JsonReport().render(report, top=args.top)
            logger.info("JSON report : %s", output)
        logger.info("Investigation completed successfully.")
        return 0
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        return 130
    except Exception:
        logger.exception("Unexpected failure.")
        return 1


def _doctor() -> int:
    from fri.config import config
    from fri.constants import PROJECT_NAME, VERSION

    print(f"{PROJECT_NAME} {VERSION}")
    print("FRI installation looks healthy.")
    print(f"Loaded {len(config.failure_profiles)} failure profiles:")
    for name in sorted(config.failure_profiles):
        profile = config.failure_profiles[name]
        print(f"  - {name:16}  domains={len(profile.domains)} keywords={len(profile.keywords)}")
    print(f"Firmware domains: {', '.join(config.domains())}")
    print(f"Boot phases: {', '.join(p.name for p in config.ordered_phases())}")
    return 0


def _topics() -> int:
    from fri.config import config

    print("Regression topics (use with --failure):")
    print()
    for name, profile in sorted(config.failure_profiles.items()):
        description = profile.description.split(".")[0].strip()
        print(f"  {name}")
        if description:
            print(f"      {description}.")
        print(f"      subsystems: {', '.join(profile.domains)}")
        print()
    return 0


def _phases() -> int:
    from fri.config import config

    print("Boot phases from CPU out of reset to OS (fri investigate --failure from_reset):")
    print()
    for phase in config.ordered_phases():
        vendors = ", ".join(phase.vendors)
        print(f"  {phase.order:3}  {phase.name}")
        print(f"       {phase.edge}")
        if phase.description:
            print(f"       {phase.description.split('.')[0].strip()}.")
        print(f"       vendors: {vendors}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

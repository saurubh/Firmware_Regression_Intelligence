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


# ==========================================================
# Main
# ==========================================================

def main() -> int:
    """
    FRI application entry point.
    """

    args = build_parser().parse_args()

    #
    # Future CLI commands
    #
    if hasattr(args, "command"):

        if args.command == "doctor":

            print("FRI installation looks healthy.")

            return 0

        if args.command == "config":

            from fri.config import config

            print(config.settings)

            return 0

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

        #
        # Investigation
        #
        report = InvestigationEngine(

            args.repo

        ).investigate(

            good=args.good,

            bad=args.bad,

            failure=args.failure

        )

        #
        # Console
        #
        ConsoleReport().render(report)

        #
        # HTML
        #
        if args.html:

            output = HtmlReport().render(report)

            logger.info(

                "HTML report : %s",

                output

            )

        #
        # JSON
        #
        if args.json:

            output = JsonReport().render(report)

            logger.info(

                "JSON report : %s",

                output

            )

        logger.info(

            "Investigation completed successfully."

        )

        return 0

    except KeyboardInterrupt:

        logger.warning(

            "Interrupted by user."

        )

        return 130

    except Exception:

        logger.exception(

            "Unexpected failure."

        )

        return 1


# ==========================================================

if __name__ == "__main__":

    sys.exit(main())
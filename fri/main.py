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

    if args.command == "pins":
        return _pins(
            workspace=args.workspace,
            gitman=getattr(args, "gitman", None),
            good=args.good,
            bad=args.bad,
        )

    if args.command != "investigate":
        print("Unknown command.")
        return 1

    if args.repo and (not args.good or not args.bad):
        print("--good and --bad are required with --repo.")
        return 2
    if args.workspace and (not args.good or not args.bad):
        print("--good and --bad are required with --workspace.")
        return 2
    if args.gitman and (not args.good or not args.bad):
        print("--good and --bad are required with --gitman.")
        return 2

    if args.verbose:
        logger.setLevel("DEBUG")

    logger.info("=" * 80)
    logger.info("Firmware Regression Intelligence")
    logger.info("=" * 80)
    logger.info("Failure Type : %s", args.failure)

    try:
        engine = InvestigationEngine(args.repo)
        if args.manifest:
            logger.info("Manifest     : %s", args.manifest)
            report = engine.investigate_manifest(args.manifest, args.failure)
        elif args.gitman:
            logger.info("gitman.yml   : %s", args.gitman)
            logger.info("Good Build   : %s", args.good)
            logger.info("Bad Build    : %s", args.bad)
            report = engine.investigate_gitman(
                args.gitman, args.good, args.bad, args.failure
            )
        elif args.workspace:
            logger.info("Workspace    : %s", args.workspace)
            logger.info("Good Build   : %s", args.good)
            logger.info("Bad Build    : %s", args.bad)
            report = engine.investigate_workspace(
                args.workspace, args.good, args.bad, args.failure
            )
        else:
            logger.info("Repository   : %s", args.repo)
            logger.info("Good Build   : %s", args.good)
            logger.info("Bad Build    : %s", args.bad)
            report = engine.investigate(
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


def _pins(
    workspace: str | None,
    good: str,
    bad: str,
    gitman: str | None = None,
) -> int:
    from fri.collector.workspace import WorkspaceCollector

    collector = WorkspaceCollector()
    if gitman:
        plan = collector.plan_from_gitman(gitman, good, bad)
    else:
        plan = collector.plan_from_workspace(workspace, good, bad)
    print(f"Workspace : {plan.workspace}")
    print(f"Good      : {plan.good_label}")
    print(f"Bad       : {plan.bad_label}")
    print()
    print(f"{'repo':<28} {'status':<10} {'via':<16} {'good':<12} {'bad':<12}")
    print("-" * 80)
    for delta in plan.deltas:
        via = f"{delta.good_source or '-'}/{delta.bad_source or '-'}"
        print(
            f"{delta.name:<28} {delta.status:<10} {via:<16} "
            f"{(delta.good_sha or '-'):<12.12} {(delta.bad_sha or '-'):<12.12}"
        )
    moved = [item for item in plan.deltas if item.status == "changed"]
    print()
    print(f"{len(moved)} repo(s) moved. Investigate with:")
    if gitman:
        print(
            f"  fri investigate --gitman {gitman} "
            f"--good {good} --bad {bad} --failure from_reset"
        )
    else:
        print(
            f"  fri investigate --workspace {workspace} "
            f"--good {good} --bad {bad} --failure from_reset"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

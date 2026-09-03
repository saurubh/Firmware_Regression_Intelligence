from fri.cli import build_parser
from fri.constants import FAILURE_OS_BOOT, VERSION


def test_investigate_accepts_os_boot():
    parser = build_parser()
    args = parser.parse_args(
        [
            "investigate",
            "--repo",
            ".",
            "--good",
            "HEAD~1",
            "--bad",
            "HEAD",
            "--failure",
            "os_boot",
        ]
    )
    assert args.failure == FAILURE_OS_BOOT
    assert args.command == "investigate"


def test_topics_command_exists():
    parser = build_parser()
    args = parser.parse_args(["topics"])
    assert args.command == "topics"


def test_version_flag():
    parser = build_parser()
    try:
        parser.parse_args(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("expected version to exit")


def test_package_version():
    assert VERSION.startswith("2.")

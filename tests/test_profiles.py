from fri.cli import build_parser
from fri.config import config


def test_failure_choices_are_loaded_from_yaml():
    parser = build_parser()
    investigate = parser._subparsers._group_actions[0].choices["investigate"]
    action = next(item for item in investigate._actions if "--failure" in item.option_strings)
    assert set(action.choices) == set(config.failure_profiles)
    assert "os_boot" in action.choices
    assert "clock" in action.choices
    assert "virtualization" in action.choices


def test_os_boot_profile_covers_handoff_surfaces():
    profile = config.get_failure_profile("os_boot")
    assert profile is not None
    joined_keywords = " ".join(profile.keywords).lower()
    for needle in (
        "exitbootservices",
        "getmemorymap",
        "linuxboot",
        "grub",
        "acpi",
        "bootorder",
        "iommu",
    ):
        assert needle in joined_keywords
    assert "BDS" in profile.domains
    assert "ACPI" in profile.domains
    assert "OSLoader" in profile.domains
    assert "acpi" in profile.related


def test_profiles_expose_matchers():
    for name, profile in config.failure_profiles.items():
        assert profile.domains, name
        assert profile.keywords, name
        assert profile.description, name


def test_taxonomy_keywords_unify_secure_boot_spellings():
    compact = {item.replace(" ", "").replace("-", "").upper() for item in config.keywords()}
    assert "SECUREBOOT" in compact
    assert "EXITBOOTSERVICES" in compact

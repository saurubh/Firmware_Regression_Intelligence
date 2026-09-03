from fri.config import config
from fri.constants import SUPPORTED_FAILURES


def test_every_constant_has_a_yaml_profile():
    loaded = set(config.failure_profiles)
    expected = set(SUPPORTED_FAILURES)
    assert expected == loaded


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
    assert any("bds" in path.lower() for path in profile.path_patterns)


def test_profiles_expose_matchers():
    for name, profile in config.failure_profiles.items():
        assert profile.domains, name
        assert profile.keywords, name
        assert profile.description, name

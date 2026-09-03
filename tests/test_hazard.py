from fri.analyzer.diff_analyzer import DiffAnalyzer
from fri.analyzer.hazard_detector import HazardDetector

DIFF = """
--- a/MdeModulePkg/Universal/BdsDxe/BdsEntry.c
+++ b/MdeModulePkg/Universal/BdsDxe/BdsEntry.c
@@
-  Status = gBS->ExitBootServices (ImageHandle, MapKey);
+  Status = gBS->ExitBootServices (ImageHandle, MapKey + 1);
+  PcdSet32S (PcdPlatformBootTimeout, 0);
+  InstallConfigurationTable (&gEfiAcpiTableGuid, Dsdt);
"""


def test_detects_os_boot_hazards():
    hazards = HazardDetector().detect(DIFF)
    names = {item.name for item in hazards}
    assert "ExitBootServices" in names
    assert "PCD / UPD default" in names
    assert "ACPI table" in names


def test_diff_analyzer_collects_boot_apis():
    evidence = DiffAnalyzer().analyze(DIFF)
    assert "ExitBootServices" in evidence.boot_api_hits
    assert evidence.hazards
    assert evidence.score > 0
    assert "EXITBOOTSERVICES" in evidence.firmware_keywords


def test_comment_only_diff():
    diff = """
--- a/File.c
+++ b/File.c
@@
-  // old comment
+  // new comment
"""
    evidence = DiffAnalyzer().analyze(diff)
    assert evidence.comment_only is True


def test_large_diff_analyzes_in_under_two_seconds():
    import time

    line = "+  Status = HelperFunction(ImageHandle);\n"
    blob = "+++ b/MdeModulePkg/BdsDxe/BdsEntry.c\n" + (line * 25000)
    started = time.perf_counter()
    evidence = DiffAnalyzer().analyze(blob)
    elapsed = time.perf_counter() - started
    assert evidence.added_lines == 25000
    assert elapsed < 2.0, elapsed


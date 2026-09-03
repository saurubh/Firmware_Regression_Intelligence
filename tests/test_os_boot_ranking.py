from fri.analyzer.diff_analyzer import DiffAnalyzer
from fri.classifier.classifier import FirmwareClassifier
from fri.config import config
from fri.models import RegressionCandidate
from fri.parser.commit_parser import CommitParser
from fri.scorer.regression_scorer import RegressionScorer
from tests.helpers import make_commit


def _score(message: str, files: list[str], diff: str, failure: str) -> RegressionCandidate:
    commit = make_commit(message=message, files=files, insertions=40, deletions=10)
    commit = CommitParser().parse(commit)
    commit = FirmwareClassifier().classify(commit)
    evidence = DiffAnalyzer().analyze(diff)
    candidate = RegressionCandidate(commit=commit)
    profile = config.get_failure_profile(failure)
    return RegressionScorer().score(candidate, evidence, profile)


OS_BOOT_DIFF = """
--- a/MdeModulePkg/Universal/BdsDxe/BdsEntry.c
+++ b/MdeModulePkg/Universal/BdsDxe/BdsEntry.c
@@
+  Status = gBS->ExitBootServices (ImageHandle, MapKey);
+  gBS->GetMemoryMap (&Size, MemoryMap, &MapKey, &DescriptorSize, &DescriptorVersion);
"""

MRC_DIFF = """
--- a/Silicon/Memory/MrcTrain.c
+++ b/Silicon/Memory/MrcTrain.c
@@
+  MrcSetTiming (Ddr5, 4800);
"""

DOCS_DIFF = """
--- a/README.md
+++ b/README.md
@@
+Updated the user guide.
"""


def test_os_boot_commit_outranks_unrelated_and_docs():
    os_boot = _score(
        "Fix OS boot hang after ExitBootServices",
        ["MdeModulePkg/Universal/BdsDxe/BdsEntry.c"],
        OS_BOOT_DIFF,
        "os_boot",
    )
    memory = _score(
        "Tune MRC DDR5 training",
        ["Silicon/Memory/MrcTrain.c"],
        MRC_DIFF,
        "os_boot",
    )
    docs = _score(
        "Docs: update README",
        ["README.md"],
        DOCS_DIFF,
        "os_boot",
    )
    assert os_boot.confidence > memory.confidence
    assert os_boot.confidence > docs.confidence
    assert os_boot.hazards
    assert os_boot.score > memory.score


def test_memory_profile_prefers_mrc_commit():
    os_boot = _score(
        "Fix OS boot hang after ExitBootServices",
        ["MdeModulePkg/Universal/BdsDxe/BdsEntry.c"],
        OS_BOOT_DIFF,
        "memory",
    )
    memory = _score(
        "Tune MRC DDR5 training",
        ["Silicon/Memory/MrcTrain.c"],
        MRC_DIFF,
        "memory",
    )
    assert memory.confidence > os_boot.confidence


def test_linuxboot_topic_matches_payload_paths():
    candidate = _score(
        "LinuxBoot payload: fix kexec into target kernel",
        ["Payload/LinuxBoot/main.c"],
        """
--- a/Payload/LinuxBoot/main.c
+++ b/Payload/LinuxBoot/main.c
@@
+  kexec_load (bzImage);
""",
        "linuxboot",
    )
    assert candidate.matched_paths or candidate.matched_domains
    assert candidate.confidence >= 50

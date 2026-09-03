from fri.classifier.classifier import FirmwareClassifier
from fri.parser.commit_parser import CommitParser
from tests.helpers import make_commit


def test_parses_os_boot_intent_and_keywords():
    commit = make_commit(
        message="Revert BIOS-99: ExitBootServices timeout breaks Linux OS boot"
    )
    parsed = CommitParser().parse(commit)
    assert parsed.intent == "Revert"
    assert parsed.jira == "BIOS-99"
    assert "BOOT" in parsed.keywords


def test_memory_path_is_not_classified_as_me():
    commit = make_commit(files=["Silicon/Memory/MrcTrain.c"])
    classified = FirmwareClassifier().classify(commit)
    assert "Memory" in classified.domains
    assert "ME" not in classified.domains


def test_classifier_maps_bds_and_acpi_paths():
    commit = make_commit(
        files=[
            "MdeModulePkg/Universal/BdsDxe/BdsEntry.c",
            "Platform/AcpiPlatform/Dsdt.asl",
        ]
    )
    classified = FirmwareClassifier().classify(commit)
    assert "BDS" in classified.domains
    assert "ACPI" in classified.domains

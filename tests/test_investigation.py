from pathlib import Path

from git import Repo

from fri.collector.git_collector import _is_source
from fri.engine.investigation_engine import InvestigationEngine
from fri.main import _doctor, _topics


def test_end_to_end_os_boot_investigation(tmp_path: Path):
    repo = Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "FRI").release()
    repo.config_writer().set_value("user", "email", "fri@example.com").release()

    good = tmp_path / "MdeModulePkg" / "Universal" / "BdsDxe"
    good.mkdir(parents=True)
    source = good / "BdsEntry.c"
    source.write_text("void BdsEntry(void) { }\n", encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text("docs\n", encoding="utf-8")
    repo.index.add(["MdeModulePkg/Universal/BdsDxe/BdsEntry.c", "README.md"])
    repo.index.commit("GOOD: initial firmware")

    source.write_text(
        "void BdsEntry(void) { gBS->ExitBootServices(ImageHandle, MapKey); }\n",
        encoding="utf-8",
    )
    repo.index.add(["MdeModulePkg/Universal/BdsDxe/BdsEntry.c"])
    repo.index.commit("BIOS-42: Linux OS boot hangs in ExitBootServices")

    readme.write_text("docs updated\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("Docs: refresh README")

    report = InvestigationEngine(str(tmp_path)).investigate(
        good="HEAD~2",
        bad="HEAD",
        failure="os_boot",
    )
    assert report.failure == "os_boot"
    assert report.statistics.total_commits == 2
    assert report.candidates
    top = report.candidates[0]
    assert "ExitBootServices" in top.commit.message or top.hazards
    assert top.commit.subject.startswith("BIOS-42")
    assert report.bisect is not None
    assert report.covered_topics
    assert "acpi" in report.related_topics


def test_source_filter_skips_firmware_binaries():
    assert _is_source("MdeModulePkg/BdsDxe/BdsEntry.c")
    assert _is_source("PlatformPkg/AcpiTables/Dsdt.asl")
    assert not _is_source("Fsp/Fsp.fd")
    assert not _is_source("Microcode/ucode.bin")
    assert not _is_source("Build/BIOS.efi")


def test_doctor_and_topics_commands(capsys):
    assert _doctor() == 0
    assert _topics() == 0
    output = capsys.readouterr().out
    assert "os_boot" in output
    assert "linuxboot" in output

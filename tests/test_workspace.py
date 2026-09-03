from pathlib import Path

from git import Repo

from fri.collector.workspace import WorkspaceCollector
from fri.engine.investigation_engine import InvestigationEngine
from fri.main import _pins
from fri.report.json_report import JsonReport


def _init_repo(path: Path) -> Repo:
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(path)
    repo.config_writer().set_value("user", "name", "FRI").release()
    repo.config_writer().set_value("user", "email", "fri@example.com").release()
    return repo


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _bios_workspace(tmp_path: Path) -> tuple[Path, str, str]:
    """Platform superproject with an edk2 submodule that moved between builds."""
    edk2 = tmp_path / "edk2_upstream"
    edk_repo = _init_repo(edk2)
    _write(edk2 / "MdeModulePkg" / "Universal" / "BdsDxe" / "BdsEntry.c", "void BdsEntry(void) { }\n")
    edk_repo.index.add(["MdeModulePkg/Universal/BdsDxe/BdsEntry.c"])
    edk_repo.index.commit("edk2: good BDS")
    good_edk = edk_repo.head.commit.hexsha

    ws = tmp_path / "platform"
    plat = _init_repo(ws)
    plat.git.config("protocol.file.allow", "always")
    _write(ws / "PlatformPkg" / "Platform.c", "void PlatformInit(void) { }\n")
    plat.index.add(["PlatformPkg/Platform.c"])
    plat.index.commit("platform: initial")
    plat.git.submodule("add", str(edk2.resolve()), "edk2")
    plat.index.commit("platform: pin good edk2")
    good_ws = plat.head.commit.hexsha

    nested = Repo(ws / "edk2")
    nested.git.config("user.name", "FRI")
    nested.git.config("user.email", "fri@example.com")
    bds = ws / "edk2" / "MdeModulePkg" / "Universal" / "BdsDxe" / "BdsEntry.c"
    bds.write_text(
        "void BdsEntry(void) { gBS->ExitBootServices(ImageHandle, MapKey); }\n",
        encoding="utf-8",
    )
    nested.git.add("MdeModulePkg/Universal/BdsDxe/BdsEntry.c")
    nested.index.commit("BIOS-99: ExitBootServices hang")
    plat.git.add("edk2")

    _write(ws / "PlatformPkg" / "AcpiTables" / "Dsdt.asl", "DefinitionBlock (\"DSDT.aml\", \"DSDT\", 2, \"OEM\", \"TBL\", 1) {}\n")
    plat.git.add("PlatformPkg/AcpiTables/Dsdt.asl")
    plat.index.commit("BIOS-100: ACPI DSDT and edk2 pin bump")
    bad_ws = plat.head.commit.hexsha
    assert good_edk != nested.head.commit.hexsha
    return ws, good_ws, bad_ws


def test_pins_discovers_moved_submodule(tmp_path: Path):
    ws, good, bad = _bios_workspace(tmp_path)
    plan = WorkspaceCollector().plan_from_workspace(str(ws), good, bad)
    names = {delta.name: delta for delta in plan.deltas}
    assert "edk2" in names
    assert names["edk2"].status == "changed"
    assert names["edk2"].good_sha != names["edk2"].bad_sha
    moved = [window.name for window in plan.windows if window.changed]
    assert "edk2" in moved


def test_workspace_investigation_ranks_both_repos(tmp_path: Path):
    ws, good, bad = _bios_workspace(tmp_path)
    report = InvestigationEngine().investigate_workspace(str(ws), good, bad, "os_boot")
    repos = {commit.repo_name for commit in report.commits}
    assert "edk2" in repos
    assert report.statistics.repo_count >= 2
    assert any(candidate.commit.repo_name == "edk2" for candidate in report.candidates)
    assert report.bisect is not None
    assert any("edk2" in command or "pin-set" in command for command in report.bisect.commands)
    output = JsonReport().render(report, top=10)
    text = output.read_text(encoding="utf-8")
    assert "repo_deltas" in text
    assert "edk2" in text


def test_manifest_explicit_repos(tmp_path: Path):
    first = tmp_path / "intel"
    intel = _init_repo(first)
    _write(first / "IntelFsp2Pkg" / "FspmWrapperPeim.c", "void FspMemoryInit(void) { }\n")
    intel.index.add(["IntelFsp2Pkg/FspmWrapperPeim.c"])
    intel.index.commit("intel: good FSP-M")
    good_intel = intel.head.commit.hexsha
    _write(first / "IntelFsp2Pkg" / "FspmWrapperPeim.c", "void FspMemoryInit(void) { FspMemoryInit(FspmUpd); }\n")
    intel.index.add(["IntelFsp2Pkg/FspmWrapperPeim.c"])
    intel.index.commit("intel: FSP-M timeout")
    bad_intel = intel.head.commit.hexsha

    second = tmp_path / "edk2"
    edk = _init_repo(second)
    _write(second / "README.md", "edk2\n")
    edk.index.add(["README.md"])
    edk.index.commit("edk2 docs")
    same = edk.head.commit.hexsha

    manifest = tmp_path / "pins.yaml"
    manifest.write_text(
        f"""
workspace: {tmp_path}
good: unused
bad: unused
repos:
  - name: Intel
    path: intel
    good: {good_intel}
    bad: {bad_intel}
  - name: edk2
    path: edk2
    good: {same}
    bad: {same}
""",
        encoding="utf-8",
    )
    report = InvestigationEngine().investigate_manifest(str(manifest), "memory_init")
    assert report.statistics.repo_count == 1
    assert all(commit.repo_name == "Intel" for commit in report.commits)
    deltas = {item.name: item.status for item in report.repo_deltas}
    assert deltas["Intel"] == "changed"
    assert deltas["edk2"] == "unchanged"


def test_pins_command(tmp_path: Path, capsys):
    ws, good, bad = _bios_workspace(tmp_path)
    assert _pins(str(ws), good, bad) == 0
    output = capsys.readouterr().out
    assert "edk2" in output
    assert "changed" in output

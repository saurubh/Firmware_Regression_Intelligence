from pathlib import Path

from git import Repo

from fri.collector.workspace import WorkspaceCollector
from fri.engine.investigation_engine import InvestigationEngine


def _init_repo(path: Path) -> Repo:
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(path)
    repo.config_writer().set_value("user", "name", "FRI").release()
    repo.config_writer().set_value("user", "email", "fri@example.com").release()
    return repo


def test_gitman_reads_source_names_and_same_tags(tmp_path: Path):
    edk = _init_repo(tmp_path / "Edk2")
    (tmp_path / "Edk2" / "MdeModulePkg").mkdir()
    (tmp_path / "Edk2" / "MdeModulePkg" / "Bds.c").write_text("void Bds(void) {}\n", encoding="utf-8")
    edk.index.add(["MdeModulePkg/Bds.c"])
    edk.index.commit("edk2 good")
    edk.create_tag("GOOD_BUILD")
    (tmp_path / "Edk2" / "MdeModulePkg" / "Bds.c").write_text(
        "void Bds(void) { ExitBootServices(); }\n",
        encoding="utf-8",
    )
    edk.index.add(["MdeModulePkg/Bds.c"])
    edk.index.commit("edk2 bad os boot")
    edk.create_tag("BAD_BUILD")

    intel = _init_repo(tmp_path / "Intel")
    (tmp_path / "Intel" / "IntelFsp2Pkg").mkdir()
    (tmp_path / "Intel" / "IntelFsp2Pkg" / "Fsp.c").write_text("void Fsp(void) {}\n", encoding="utf-8")
    intel.index.add(["IntelFsp2Pkg/Fsp.c"])
    intel.index.commit("intel good")
    intel.create_tag("GOOD_BUILD")
    intel.create_tag("BAD_BUILD")

    platform = _init_repo(tmp_path)
    (tmp_path / "Platform.c").write_text("void Platform(void) {}\n", encoding="utf-8")
    platform.index.add(["Platform.c"])
    platform.index.commit("platform good")
    platform.create_tag("GOOD_BUILD")
    (tmp_path / "Platform.c").write_text("void Platform(void) { Acpi(); }\n", encoding="utf-8")
    platform.index.add(["Platform.c"])
    platform.index.commit("platform bad")
    platform.create_tag("BAD_BUILD")

    gitman = tmp_path / "gitman.yml"
    gitman.write_text(
        """
location: .
sources:
  - name: Edk2
    repo: unused
    rev: unused
  - name: Intel
    repo: unused
    rev: unused
  - name: Lenovo/Base
    repo: unused
    rev: unused
""",
        encoding="utf-8",
    )

    plan = WorkspaceCollector().plan_from_gitman(str(gitman), "GOOD_BUILD", "BAD_BUILD")
    names = [delta.name for delta in plan.deltas]
    assert "Edk2" in names
    assert "Intel" in names
    assert "Lenovo/Base" in names
    by_name = {delta.name: delta for delta in plan.deltas}
    assert by_name["Edk2"].status == "changed"
    assert by_name["Edk2"].good_source == "tag"
    assert by_name["Intel"].status == "unchanged"
    assert by_name["Lenovo/Base"].status == "missing"

    agesa = _init_repo(tmp_path / "AgesaPkg")
    (tmp_path / "AgesaPkg" / "AmdInit.c").write_text("void AmdInit(void) {}\n", encoding="utf-8")
    agesa.index.add(["AmdInit.c"])
    agesa.index.commit("agesa good")
    agesa.create_tag("GOOD_BUILD")
    (tmp_path / "AgesaPkg" / "AmdInit.c").write_text("void AmdInitPost(void) {}\n", encoding="utf-8")
    agesa.index.add(["AmdInit.c"])
    agesa.index.commit("agesa bad")
    agesa.create_tag("BAD_BUILD")

    plan = WorkspaceCollector().plan_from_gitman(str(gitman), "GOOD_BUILD", "BAD_BUILD")
    names = [delta.name for delta in plan.deltas]
    assert "Edk2" in names
    assert "AgesaPkg" in names
    by_name = {delta.name: delta for delta in plan.deltas}
    assert by_name["AgesaPkg"].status == "changed"
    assert by_name["AgesaPkg"].good_source == "tag"

    report = InvestigationEngine().investigate_gitman(
        str(gitman), "GOOD_BUILD", "BAD_BUILD", "os_boot"
    )
    repos = {commit.repo_name for commit in report.commits}
    assert "Edk2" in repos
    assert "AgesaPkg" in repos
    assert report.statistics.repo_count == 3
    assert report.statistics.total_commits == len(report.commits)


def test_cli_accepts_gitman_flag():
    from fri.cli import build_parser

    args = build_parser().parse_args(
        [
            "investigate",
            "--gitman",
            "gitman.yml",
            "--good",
            "G",
            "--bad",
            "B",
            "--failure",
            "os_boot",
        ]
    )
    assert args.gitman == "gitman.yml"
    pins = build_parser().parse_args(
        ["pins", "--gitman", "gitman.yml", "--good", "G", "--bad", "B"]
    )
    assert pins.gitman == "gitman.yml"


def test_gitman_uses_shared_at_suffix_in_nested_repos(tmp_path: Path):
    full_good = "IHE117Y_1.41_01@BirchStreamReferenceBuild@good"
    full_bad = "IHE119A_1.50_01@BirchStreamReferenceBuild@bad"
    shared_good = "@BirchStreamReferenceBuild@good"
    shared_bad = "@BirchStreamReferenceBuild@bad"

    platform = _init_repo(tmp_path)
    (tmp_path / "Platform.c").write_text("void P(void) {}\n", encoding="utf-8")
    platform.index.add(["Platform.c"])
    platform.index.commit("platform good")
    platform.create_tag(full_good)
    (tmp_path / "Platform.c").write_text("void P(void) { x(); }\n", encoding="utf-8")
    platform.index.add(["Platform.c"])
    platform.index.commit("platform bad")
    platform.create_tag(full_bad)

    edk = _init_repo(tmp_path / "Edk2")
    (tmp_path / "Edk2" / "Bds.c").write_text("void Bds(void) {}\n", encoding="utf-8")
    edk.index.add(["Bds.c"])
    edk.index.commit("edk good")
    edk.create_tag(shared_good)
    (tmp_path / "Edk2" / "Bds.c").write_text("void Bds(void) { ExitBootServices(); }\n", encoding="utf-8")
    edk.index.add(["Bds.c"])
    edk.index.commit("edk bad")
    edk.create_tag(shared_bad)

    gitman = tmp_path / "gitman.yml"
    gitman.write_text("location: .\nsources:\n  - name: Edk2\n", encoding="utf-8")
    plan = WorkspaceCollector().plan_from_gitman(str(gitman), full_good, full_bad)
    by_name = {delta.name: delta for delta in plan.deltas}
    assert by_name["Edk2"].status == "changed"
    assert by_name["Edk2"].good_source == "tag"
    platform_delta = next(item for item in plan.deltas if item.path == ".")
    assert platform_delta.status == "changed"
    assert platform_delta.good_source == "tag"

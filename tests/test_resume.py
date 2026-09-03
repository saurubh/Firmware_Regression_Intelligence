from pathlib import Path

from git import Repo

from fri.cli import build_parser
from fri.engine.investigation_engine import InvestigationEngine


def _tiny_repo(tmp_path: Path) -> Path:
    repo = Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "FRI").release()
    repo.config_writer().set_value("user", "email", "fri@example.com").release()
    pkg = tmp_path / "MdeModulePkg" / "Universal" / "BdsDxe"
    pkg.mkdir(parents=True)
    source = pkg / "BdsEntry.c"
    source.write_text("void BdsEntry(void) { }\n", encoding="utf-8")
    repo.index.add(["MdeModulePkg/Universal/BdsDxe/BdsEntry.c"])
    repo.index.commit("GOOD: initial firmware")
    source.write_text(
        "void BdsEntry(void) { gBS->ExitBootServices(ImageHandle, MapKey); }\n",
        encoding="utf-8",
    )
    repo.index.add(["MdeModulePkg/Universal/BdsDxe/BdsEntry.c"])
    repo.index.commit("BIOS-42: Linux OS boot hangs in ExitBootServices")
    return tmp_path


def test_second_run_resumes_cached_commits(tmp_path: Path):
    repo = _tiny_repo(tmp_path / "tree")
    cache = tmp_path / "cache"
    first = InvestigationEngine(str(repo)).investigate(
        good="HEAD~1",
        bad="HEAD",
        failure="os_boot",
        workers=1,
        cache_dir=str(cache),
    )
    assert first.statistics.total_commits == 1
    jsonl = list(cache.glob("*/*.jsonl"))
    assert jsonl

    second = InvestigationEngine(str(repo)).investigate(
        good="HEAD~1",
        bad="HEAD",
        failure="os_boot",
        workers=1,
        cache_dir=str(cache),
    )
    assert second.statistics.total_commits == 1
    assert second.candidates[0].commit.sha == first.candidates[0].commit.sha


def test_fresh_ignores_resume_cache(tmp_path: Path):
    repo = _tiny_repo(tmp_path / "tree")
    cache = tmp_path / "cache"
    InvestigationEngine(str(repo)).investigate(
        good="HEAD~1",
        bad="HEAD",
        failure="os_boot",
        workers=1,
        cache_dir=str(cache),
    )
    assert list(cache.glob("*/*.jsonl"))
    InvestigationEngine(str(repo)).investigate(
        good="HEAD~1",
        bad="HEAD",
        failure="os_boot",
        workers=1,
        cache_dir=str(cache),
        fresh=True,
    )
    jsonl = list(cache.glob("*/*.jsonl"))
    assert jsonl
    lines = jsonl[0].read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1


def test_cli_fresh_flag():
    args = build_parser().parse_args(
        [
            "investigate",
            "--repo",
            ".",
            "--good",
            "G",
            "--bad",
            "B",
            "--failure",
            "os_boot",
            "--fresh",
        ]
    )
    assert args.fresh is True

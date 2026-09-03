from pathlib import Path

from git import Repo

from fri.analyzer.diff_analyzer import DiffAnalyzer
from fri.analyzer.phase_analyzer import PhaseAnalyzer
from fri.classifier.classifier import FirmwareClassifier
from fri.config import config
from fri.engine.investigation_engine import InvestigationEngine
from fri.models import RegressionCandidate
from fri.parser.commit_parser import CommitParser
from tests.helpers import make_commit


def test_boot_phases_cover_reset_to_os():
    names = [phase.name for phase in config.ordered_phases()]
    for required in (
        "reset",
        "sec",
        "pei",
        "memory_init",
        "silicon_init",
        "dxe",
        "bds",
        "os_handoff",
        "runtime",
        "resume",
        "recovery",
    ):
        assert required in names
    assert names.index("reset") < names.index("os_handoff")


def test_cli_exposes_phase_failures():
    from fri.cli import build_parser

    parser = build_parser()
    investigate = parser._subparsers._group_actions[0].choices["investigate"]
    action = next(item for item in investigate._actions if "--failure" in item.option_strings)
    for name in ("from_reset", "memory_init", "sec", "amd_agesa", "intel_bootguard"):
        assert name in action.choices


def test_intel_fsp_m_tags_memory_init():
    commit = make_commit(
        message="FSP-M MemoryInit timeout on DDR5 RMT",
        files=["IntelFsp2Pkg/FspmWrapperPeim/FspmWrapperPeim.c"],
    )
    commit = CommitParser().parse(commit)
    commit = FirmwareClassifier().classify(commit)
    diff = DiffAnalyzer().analyze(
        """
--- a/IntelFsp2Pkg/FspmWrapperPeim/FspmWrapperPeim.c
+++ b/IntelFsp2Pkg/FspmWrapperPeim/FspmWrapperPeim.c
@@
+  Status = FspMemoryInit (FspmUpd);
"""
    )
    candidate = PhaseAnalyzer().tag(RegressionCandidate(commit=commit), diff)
    assert candidate.primary_phase == "memory_init"
    assert candidate.vendor == "intel"


def test_amd_agesa_tags_silicon_or_memory():
    commit = make_commit(
        message="AGESA AmdInitPost UMC training",
        files=["AgesaModulePkg/AmdInitPost.c"],
    )
    commit = CommitParser().parse(commit)
    commit = FirmwareClassifier().classify(commit)
    diff = DiffAnalyzer().analyze(
        """
--- a/AgesaModulePkg/AmdInitPost.c
+++ b/AgesaModulePkg/AmdInitPost.c
@@
+  AmdInitPost (UmC);
"""
    )
    candidate = PhaseAnalyzer().tag(RegressionCandidate(commit=commit), diff)
    assert candidate.primary_phase in {"memory_init", "silicon_init"}
    assert candidate.vendor == "amd"


def test_from_reset_investigation_triages_memory_phase(tmp_path: Path):
    repo = Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "FRI").release()
    repo.config_writer().set_value("user", "email", "fri@example.com").release()
    pei = tmp_path / "IntelFsp2Pkg" / "FspmWrapperPeim"
    pei.mkdir(parents=True)
    source = pei / "FspmWrapperPeim.c"
    source.write_text("void Fspm(void) {}\n", encoding="utf-8")
    repo.index.add(["IntelFsp2Pkg/FspmWrapperPeim/FspmWrapperPeim.c"])
    repo.index.commit("GOOD")
    source.write_text("void Fspm(void) { FspMemoryInit(FspmUpd); }\n", encoding="utf-8")
    repo.index.add(["IntelFsp2Pkg/FspmWrapperPeim/FspmWrapperPeim.c"])
    repo.index.commit("Hang after reset in FSP-M MemoryInit")

    report = InvestigationEngine(str(tmp_path)).investigate(
        good="HEAD~1",
        bad="HEAD",
        failure="from_reset",
    )
    assert report.triage is not None
    assert report.triage.start_phase == "memory_init"
    assert report.candidates[0].vendor == "intel"

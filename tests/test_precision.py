from fri.analyzer.candidate_engine import CandidateEngine
from fri.analyzer.module_analyzer import ModuleAnalyzer
from fri.classifier.classifier import FirmwareClassifier
from fri.models import RegressionCandidate
from fri.parser.commit_parser import CommitParser
from fri.scorer.regression_scorer import RegressionScorer
from tests.helpers import make_commit


def test_primary_domain_is_evidence_weighted_not_alphabetical():
    commit = make_commit(
        files=[
            "Platform/AcpiPlatform/Dsdt.asl",
            "Platform/AcpiPlatform/Ssdt.asl",
            "Platform/AcpiPlatform/Madt.c",
            "SecurityPkg/Library/FitLib.c",
        ]
    )
    classified = FirmwareClassifier().classify(commit)
    assert classified.primary_domain == "ACPI"
    assert "FIT" in classified.domains


def test_relative_ranking_spreads_top_candidates():
    strong = RegressionCandidate(commit=make_commit(sha="1" * 40, message="strong"))
    strong.score = 200
    strong.signal_count = 5
    weak = RegressionCandidate(commit=make_commit(sha="2" * 40, message="weak"))
    weak.score = 80
    weak.signal_count = 2
    also_strong = RegressionCandidate(commit=make_commit(sha="3" * 40, message="also"))
    also_strong.score = 170
    also_strong.signal_count = 4

    ranked = CandidateEngine().rank([weak, strong, also_strong])
    assert ranked[0].commit.sha.startswith("1")
    assert ranked[0].confidence == 100
    assert ranked[1].confidence < ranked[0].confidence
    assert ranked[2].confidence < ranked[1].confidence
    assert ranked[1].confidence > 70


def test_absolute_confidence_does_not_clip_distinct_scores_to_100():
    high = RegressionScorer.absolute_confidence(240)
    mid = RegressionScorer.absolute_confidence(90)
    assert high < 100
    assert high > mid


def test_module_confidence_rewards_corroborating_commits():
    lucky = RegressionCandidate(commit=make_commit(sha="a" * 40, message="lucky"))
    lucky.score = 100
    lucky.confidence = 100
    lucky.matched_domains = ["FIT"]

    crowd = []
    for index in range(5):
        item = RegressionCandidate(
            commit=make_commit(sha=str(index) * 40, message=f"c{index}")
        )
        item.score = 90
        item.confidence = 90
        item.matched_domains = ["Memory"]
        crowd.append(item)

    modules = ModuleAnalyzer().analyze([lucky, *crowd])
    by_name = {module.name: module for module in modules}
    assert by_name["Memory"].confidence > by_name["FIT"].confidence


def test_parser_uses_taxonomy_keywords():
    parsed = CommitParser().parse(
        make_commit(message="Enable SecureBoot measured boot on ExitBootServices")
    )
    compact = {item.replace(" ", "").replace("-", "").upper() for item in parsed.keywords}
    assert "SECUREBOOT" in compact
    assert "EXITBOOTSERVICES" in compact

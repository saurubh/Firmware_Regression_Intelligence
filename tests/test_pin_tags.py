from pathlib import Path

from fri.collector.pin_tags import labels_for_repo, shared_pin_tag


def test_shared_pin_tag_keeps_from_first_at():
    full = (
        "IHE117Y_1.41_01@BirchStreamReferenceBuild@20260224@3545.P.03@2025.47@FW25-5"
    )
    assert (
        shared_pin_tag(full)
        == "@BirchStreamReferenceBuild@20260224@3545.P.03@2025.47@FW25-5"
    )
    assert shared_pin_tag("@already/shared") == "@already/shared"
    assert shared_pin_tag("plain-tag") == "plain-tag"


def test_labels_for_repo_full_on_root_shared_elsewhere(tmp_path: Path):
    root = tmp_path / "birchstream-ih"
    other = root / "Edk2"
    root.mkdir()
    other.mkdir()
    good = "IHE117Y_1.41_01@BirchStreamReferenceBuild@x"
    bad = "IHE119A_1.50_01@BirchStreamReferenceBuild@y"
    g, b, is_root = labels_for_repo(root, root, good, bad)
    assert is_root
    assert g == good and b == bad
    g, b, is_root = labels_for_repo(root, other, good, bad)
    assert not is_root
    assert g == "@BirchStreamReferenceBuild@x"
    assert b == "@BirchStreamReferenceBuild@y"

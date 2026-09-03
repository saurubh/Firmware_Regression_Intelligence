"""Map --good/--bad tags onto the platform repo vs every other Git clone."""

from __future__ import annotations

from pathlib import Path


def shared_pin_tag(label: str) -> str:
    """
    Platform BIOS tags look like:
      IHE117Y_1.41_01@BirchStreamReferenceBuild@20260224@3545.P.03@2025.47@FW25-5
    Other clones (edk2, Intel, AMD, vendor) carry the suffix from the first @:
      @BirchStreamReferenceBuild@20260224@3545.P.03@2025.47@FW25-5
    """
    text = (label or "").strip()
    at = text.find("@")
    if at <= 0:
        return text
    return text[at:]


def labels_for_repo(root: Path, repo_dir: Path, good: str, bad: str) -> tuple[str, str, bool]:
    """Full tags on the workspace/gitman root; shared suffix everywhere else."""
    is_root = repo_dir.resolve() == Path(root).resolve()
    if is_root:
        return good, bad, True
    return shared_pin_tag(good), shared_pin_tag(bad), False

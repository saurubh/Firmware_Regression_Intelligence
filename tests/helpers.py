"""Synthetic commit helpers for FRI tests."""

from __future__ import annotations

from datetime import datetime

from fri.models import Commit


def make_commit(
    sha: str = "a" * 40,
    message: str = "Update platform",
    files: list[str] | None = None,
    insertions: int = 20,
    deletions: int = 5,
    author: str = "tester",
    **kwargs,
) -> Commit:
    return Commit(
        sha=sha,
        short_sha=sha[:8],
        author=author,
        email="tester@example.com",
        date=datetime(2026, 1, 1),
        message=message,
        files=files or ["PlatformPkg/Platform.c"],
        insertions=insertions,
        deletions=deletions,
        **kwargs,
    )

"""
Path and keyword matching with token / directory boundaries.

Raw substring matching over-classifies as the domain list grows
(`me` inside `memory`, `pci` inside `pcie`, `boot` inside `secureboot`).
"""

from __future__ import annotations

import re


def compact_token(text: str) -> str:
    """SECURE BOOT, SecureBoot, and SECUREBOOT all become SECUREBOOT."""
    return re.sub(r"[^A-Za-z0-9]+", "", text).upper()


def keyword_in_text(text: str, keyword: str) -> bool:
    if not text or not keyword:
        return False
    if re.search(
        rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])",
        text,
        flags=re.IGNORECASE,
    ):
        return True
    compact_keyword = compact_token(keyword)
    if len(compact_keyword) < 3:
        return False
    compact_text = compact_token(text)
    if len(compact_keyword) >= 6:
        return compact_keyword in compact_text
    return (
        re.search(
            rf"(?<![A-Z0-9]){re.escape(compact_keyword)}(?![A-Z0-9])",
            compact_text,
        )
        is not None
    )


def path_matches(path: str, pattern: str) -> bool:
    """
    Match a domain/profile path pattern against a file path.

    * Patterns with `/` are directory needles (`/me/` does not match `memory`).
    * Bare tokens match a path segment, a file stem, or CamelCase (`MrcTrain`, `BdsDxe`).
    """
    if not path or not pattern:
        return False

    raw = path.replace("\\", "/").strip()
    needle = pattern.replace("\\", "/").strip().lower()
    if not needle:
        return False

    padded = "/" + raw.lower().strip("/") + "/"

    if "/" in needle:
        if not needle.startswith("/"):
            needle = "/" + needle
        if not needle.endswith("/"):
            needle = needle + "/"
        return needle in padded

    token = needle.strip("/")
    for segment in raw.split("/"):
        if _segment_matches(segment, token):
            return True
    return False


def _segment_matches(segment: str, token: str) -> bool:
    stem = segment.rsplit(".", 1)[0]
    if stem.lower() == token:
        return True
    if stem.lower().startswith(token):
        rest = stem[len(token) :]
        if not rest or rest[0].isupper() or rest[0] in "_-":
            return True
    for index, chunk in enumerate(_camel_chunks(stem)):
        if chunk.lower() != token:
            continue
        # "boot" in SecureBoot is a generic trailing chunk, not a Boot domain hit.
        if token in _GENERIC_CHUNKS and index > 0:
            continue
        return True
    return False


_GENERIC_CHUNKS = {"boot", "lib", "pkg", "inc", "src", "test"}


def _camel_chunks(stem: str) -> list[str]:
    return re.findall(
        r"[A-Z]+(?=[A-Z][a-z]|[^A-Za-z]|$)|[A-Z]?[a-z]+|[0-9]+",
        stem,
    )

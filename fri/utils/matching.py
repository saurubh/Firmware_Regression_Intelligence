"""
Path and keyword matching with token / directory boundaries.

Raw substring matching over-classifies as the domain list grows
(`me` inside `memory`, `pci` inside `pcie`, `boot` inside `secureboot`).
"""

from __future__ import annotations

import re
from collections.abc import Iterable


def compact_token(text: str) -> str:
    """SECURE BOOT, SecureBoot, and SECUREBOOT all become SECUREBOOT."""
    return re.sub(r"[^A-Za-z0-9]+", "", text).upper()


class KeywordIndex:
    """Find catalog keywords in a blob without compiling a regex per line."""

    def __init__(self, keywords: Iterable[str]) -> None:
        ordered: list[str] = []
        seen: set[str] = set()
        for keyword in keywords:
            if not keyword or keyword in seen:
                continue
            seen.add(keyword)
            ordered.append(keyword)
        self.keywords = ordered
        self._word_re = None
        if ordered:
            alts = sorted(ordered, key=len, reverse=True)
            self._word_re = re.compile(
                r"(?<![A-Za-z0-9])("
                + "|".join(re.escape(item) for item in alts)
                + r")(?![A-Za-z0-9])",
                re.IGNORECASE,
            )
        self._compact: list[tuple[str, str]] = []
        self._compact_short: list[tuple[str, re.Pattern[str]]] = []
        for keyword in ordered:
            compact = compact_token(keyword)
            if len(compact) >= 6:
                self._compact.append((keyword, compact))
            elif len(compact) >= 3:
                self._compact_short.append(
                    (
                        keyword,
                        re.compile(rf"(?<![A-Z0-9]){re.escape(compact)}(?![A-Z0-9])"),
                    )
                )

    def find(self, text: str) -> set[str]:
        if not text or not self.keywords:
            return set()
        hits: set[str] = set()
        if self._word_re:
            for match in self._word_re.finditer(text):
                hits.add(match.group(1))
        compact = compact_token(text)
        for keyword, needle in self._compact:
            if needle in compact:
                hits.add(keyword)
        if compact:
            for keyword, pattern in self._compact_short:
                if pattern.search(compact):
                    hits.add(keyword)
        return hits


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

"""Parse batched git log --name-only output."""

from __future__ import annotations


def parse_name_only_log(output: str) -> dict[str, list[str]]:
    """Map commit SHA to changed paths from `git log --pretty=format:COMMIT:%H --name-only`."""
    mapping: dict[str, list[str]] = {}
    current: str | None = None
    for line in output.splitlines():
        if line.startswith("COMMIT:"):
            current = line[7:].strip()
            if current:
                mapping[current] = []
        elif current and line.strip():
            mapping[current].append(line.strip())
    return mapping

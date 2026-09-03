"""Persist per-commit analysis so investigate can resume after a stop."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import datetime
from pathlib import Path

from fri.constants import OUTPUT_DIR, VERSION
from fri.logger import logger
from fri.models import Commit, RegressionCandidate, WorkspacePlan

CACHE_SCHEMA = 1


def run_cache_id(plan: WorkspacePlan, failure: str) -> str:
    payload = json.dumps(
        {
            "schema": CACHE_SCHEMA,
            "workspace": str(Path(plan.workspace).resolve()) if plan.workspace else "",
            "good": plan.good_label,
            "bad": plan.bad_label,
            "failure": failure.lower(),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return cleaned or "repo"


class InvestigationCache:
    def __init__(self, root: Path, plan: WorkspacePlan, failure: str) -> None:
        self.root = Path(root)
        self.plan = plan
        self.failure = failure.lower()
        self.run_id = run_cache_id(plan, failure)
        self.directory = self.root / self.run_id
        self._lock = threading.Lock()
        self._loaded: dict[str, dict[str, tuple[Commit, RegressionCandidate]]] = {}

    def reset(self) -> None:
        if self.directory.exists():
            for path in self.directory.glob("*"):
                if path.is_file():
                    path.unlink()
            try:
                self.directory.rmdir()
            except OSError:
                pass
        self._loaded.clear()
        logger.info("Fresh run: cache cleared (%s)", self.run_id)

    def load(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        meta = self.directory / "run.json"
        if not meta.exists():
            meta.write_text(
                json.dumps(
                    {
                        "schema": CACHE_SCHEMA,
                        "version": VERSION,
                        "workspace": self.plan.workspace,
                        "good": self.plan.good_label,
                        "bad": self.plan.bad_label,
                        "failure": self.failure,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        total = 0
        for path in self.directory.glob("*.jsonl"):
            repo = path.stem
            mapping: dict[str, tuple[Commit, RegressionCandidate]] = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    commit, candidate = _from_row(row)
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue
                mapping[commit.sha] = (commit, candidate)
            self._loaded[repo] = mapping
            total += len(mapping)
        if total:
            logger.info(
                "Resume cache %s: %d commit(s) already analyzed.",
                self.run_id,
                total,
            )
        else:
            logger.info("Resume cache %s (empty; results will be saved here).", self.run_id)

    def get(
        self, repo: str, sha: str
    ) -> tuple[Commit, RegressionCandidate] | None:
        return self._loaded.get(_safe_name(repo), {}).get(sha)

    def put(self, repo: str, commit: Commit, candidate: RegressionCandidate) -> None:
        key = _safe_name(repo)
        with self._lock:
            self._loaded.setdefault(key, {})[commit.sha] = (commit, candidate)
            path = self.directory / f"{key}.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(_to_row(commit, candidate), ensure_ascii=False))
                handle.write("\n")


def _to_row(commit: Commit, candidate: RegressionCandidate) -> dict:
    return {
        "sha": commit.sha,
        "commit": {
            "sha": commit.sha,
            "short_sha": commit.short_sha,
            "author": commit.author,
            "email": commit.email,
            "date": commit.date.isoformat(),
            "message": commit.message,
            "files": commit.files,
            "insertions": commit.insertions,
            "deletions": commit.deletions,
            "jira": commit.jira,
            "merge_request": commit.merge_request,
            "intent": commit.intent,
            "primary_domain": commit.primary_domain,
            "domains": commit.domains,
            "keywords": commit.keywords,
            "is_merge_commit": commit.is_merge_commit,
            "repo_name": commit.repo_name,
            "repo_path": commit.repo_path,
        },
        "candidate": {
            "score": candidate.score,
            "confidence": candidate.confidence,
            "rank": candidate.rank,
            "matched_domains": candidate.matched_domains,
            "matched_keywords": candidate.matched_keywords,
            "matched_files": candidate.matched_files,
            "matched_paths": candidate.matched_paths,
            "reasons": candidate.reasons,
            "evidence": candidate.evidence,
            "hazards": candidate.hazards,
            "signal_count": candidate.signal_count,
            "phases": candidate.phases,
            "primary_phase": candidate.primary_phase,
            "vendor": candidate.vendor,
        },
    }


def _from_row(row: dict) -> tuple[Commit, RegressionCandidate]:
    raw = row["commit"]
    date_value = raw.get("date") or datetime.now().isoformat()
    try:
        date = datetime.fromisoformat(date_value)
    except ValueError:
        date = datetime.now()
    commit = Commit(
        sha=raw["sha"],
        short_sha=raw.get("short_sha") or raw["sha"][:8],
        author=raw.get("author") or "",
        email=raw.get("email") or "",
        date=date,
        message=raw.get("message") or "",
        files=list(raw.get("files") or []),
        insertions=int(raw.get("insertions") or 0),
        deletions=int(raw.get("deletions") or 0),
        jira=raw.get("jira"),
        merge_request=raw.get("merge_request"),
        intent=raw.get("intent") or "Unknown",
        primary_domain=raw.get("primary_domain") or "Unknown",
        domains=list(raw.get("domains") or []),
        keywords=list(raw.get("keywords") or []),
        is_merge_commit=bool(raw.get("is_merge_commit")),
        repo_name=raw.get("repo_name") or "",
        repo_path=raw.get("repo_path") or "",
    )
    cand = row.get("candidate") or {}
    candidate = RegressionCandidate(
        commit=commit,
        rank=int(cand.get("rank") or 0),
        confidence=int(cand.get("confidence") or 0),
        score=int(cand.get("score") or 0),
        matched_domains=list(cand.get("matched_domains") or []),
        matched_keywords=list(cand.get("matched_keywords") or []),
        matched_files=list(cand.get("matched_files") or []),
        matched_paths=list(cand.get("matched_paths") or []),
        reasons=list(cand.get("reasons") or []),
        evidence=list(cand.get("evidence") or []),
        hazards=list(cand.get("hazards") or []),
        signal_count=int(cand.get("signal_count") or 0),
        phases=list(cand.get("phases") or []),
        primary_phase=cand.get("primary_phase") or "Unknown",
        vendor=cand.get("vendor") or "common",
    )
    return commit, candidate

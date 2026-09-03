"""
Git Collector — GitPython for repo open / commit walk; subprocess
for diffs so a BIOS binary blob cannot stall the process.
"""

from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from git import Repo
from git.exc import InvalidGitRepositoryError

from fri.collector.build_resolver import BuildResolver
from fri.config import config
from fri.logger import logger
from fri.models import Commit
from fri.utils.git_batch import parse_name_only_log

SOURCE_SUFFIXES = {
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".asl",
    ".aslc",
    ".inf",
    ".dsc",
    ".dec",
    ".fdf",
    ".vfr",
    ".uni",
    ".nasm",
    ".asm",
    ".s",
    ".inc",
    ".mac",
    ".py",
    ".yml",
    ".yaml",
    ".json",
    ".xml",
    ".acpi",
    ".sd",
    ".i",
    ".ld",
    ".lds",
    ".txt",
    ".md",
}

# Diff these only. .uni/.json/.md trees in Edk2 can be multi-megabyte.
DIFF_SUFFIXES = {
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".asl",
    ".aslc",
    ".inf",
    ".dsc",
    ".dec",
    ".fdf",
    ".vfr",
    ".nasm",
    ".asm",
    ".s",
    ".inc",
    ".mac",
    ".i",
    ".acpi",
}


def _git_settings() -> dict:
    return config.settings.get("git") or {}


def _decode_git_bytes(data: bytes | None) -> str:
    if not data:
        return ""
    return data.decode("utf-8", errors="replace")


def _is_source(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in SOURCE_SUFFIXES


def _is_diff_source(path: str) -> bool:
    return Path(path).suffix.lower() in DIFF_SUFFIXES


def has_source_paths(paths: list[str]) -> bool:
    return any(_is_source(path) for path in paths)


class GitCollector:
    """
    Thin wrapper around GitPython.

    This class should never contain firmware-specific logic.
    """

    def __init__(self, repo_path: str):

        self.repo_path = Path(repo_path)

        if not self.repo_path.exists():

            raise FileNotFoundError(
                f"Repository not found: {repo_path}"
            )

        try:

            self.repo = Repo(self.repo_path)

        except InvalidGitRepositoryError as err:

            raise RuntimeError(
                f"{repo_path} is not a valid Git repository."
            ) from err

        git_cfg = _git_settings()
        self.diff_timeout_sec = int(git_cfg.get("diff_timeout_sec", 8))
        self.path_timeout_sec = int(git_cfg.get("path_timeout_sec", 20))
        self.list_timeout_sec = int(git_cfg.get("list_timeout_sec", 180))
        self.max_source_paths = int(git_cfg.get("max_source_paths", 40))
        self.max_diff_bytes = int(git_cfg.get("max_diff_bytes", 65536))
        self.skip_merge_diffs = bool(git_cfg.get("skip_merge_diffs", True))

        #
        # Build resolver
        #
        self.resolver = BuildResolver(self.repo)

    # ======================================================
    # Public API
    # ======================================================

    def get_commits(
        self,
        good_build: str,
        bad_build: str
    ) -> list[Commit]:
        """
        Collect commits between two builds.

        Returns commits in chronological order.
        """

        good = self.resolver.resolve(good_build)

        bad = self.resolver.resolve(bad_build)

        revision = f"{good}..{bad}"

        logger.info(
            "Listing commits between %s and %s (metadata only; diffs come next)",
            good[:8],
            bad[:8],
        )

        path_map, batch_ok = self._batch_changed_paths(good, bad)
        if batch_ok:
            logger.info(
                "Batch path listing: %d commit(s) with file lists in one git log.",
                len(path_map),
            )

        commits: list[Commit] = []

        for index, git_commit in enumerate(
            self.repo.iter_commits(revision, reverse=True),
            start=1,
        ):
            if index % 50 == 0:
                logger.info("  still listing: %d commits...", index)
            files = path_map.get(git_commit.hexsha, []) if batch_ok else []
            commits.append(
                Commit(
                    sha=git_commit.hexsha,
                    short_sha=git_commit.hexsha[:8],
                    author=str(git_commit.author),
                    email=git_commit.author.email,
                    date=datetime.fromtimestamp(git_commit.committed_date),
                    message=git_commit.message.strip(),
                    files=files,
                    insertions=0,
                    deletions=0,
                    is_merge_commit=(len(git_commit.parents) > 1),
                    git_object=git_commit,
                )
            )

        logger.info("Listed %d commits in this repo. Next: analyze each diff.", len(commits))
        return commits

    # ======================================================

    def get_commit(
        self,
        revision: str
    ) -> Commit:
        """
        Return a single commit.
        """

        git_commit = self.repo.commit(revision)

        stats = git_commit.stats.total

        return Commit(

            sha=git_commit.hexsha,

            short_sha=git_commit.hexsha[:8],

            author=str(git_commit.author),

            email=git_commit.author.email,

            date=datetime.fromtimestamp(
                git_commit.committed_date
            ),

            message=git_commit.message.strip(),

            files=list(
                git_commit.stats.files.keys()
            ),

            insertions=stats.get(
                "insertions",
                0
            ),

            deletions=stats.get(
                "deletions",
                0
            ),

            is_merge_commit=(
                len(git_commit.parents) > 1
            ),

            git_object=git_commit

        )

    # ======================================================

    def changed_paths(self, commit: Commit) -> list[str]:
        if commit.files:
            return list(commit.files)
        git_commit = commit.git_object
        if git_commit is None:
            return []
        try:
            output = self._git(
                ["diff-tree", "-r", "--name-only", "--no-commit-id", commit.sha],
                timeout=self.path_timeout_sec,
            )
        except subprocess.TimeoutExpired:
            logger.warning("git diff-tree timed out for %s", commit.short_sha)
            return []
        return [line for line in output.splitlines() if line.strip()]

    def get_diff(
        self,
        commit: Commit,
        heartbeat: Callable[[str], None] | None = None,
    ) -> str:
        git_commit = commit.git_object
        if git_commit is None or not git_commit.parents:
            return ""
        if self.skip_merge_diffs and commit.is_merge_commit:
            logger.info(
                "Skipping full diff for merge %s (%d files)",
                commit.short_sha,
                len(commit.files),
            )
            return ""
        parent = git_commit.parents[0].hexsha
        sources = [path for path in commit.files if _is_diff_source(path)][:self.max_source_paths]
        if not sources:
            return ""
        stop = threading.Event()
        started = time.perf_counter()

        def pulse() -> None:
            while not stop.wait(1.0):
                if heartbeat:
                    heartbeat(f"diff {commit.short_sha} {time.perf_counter() - started:.0f}s")

        thread = threading.Thread(target=pulse, daemon=True)
        thread.start()
        try:
            output = self._git(
                ["diff", "--unified=0", parent, commit.sha, "--", *sources],
                timeout=self.diff_timeout_sec,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "git diff timed out after %ss for %s (%d source files); skipping blob",
                self.diff_timeout_sec,
                commit.short_sha,
                len(sources),
            )
            return ""
        finally:
            stop.set()
        if len(output) > self.max_diff_bytes:
            logger.info("Truncating diff for %s", commit.short_sha)
            return output[:self.max_diff_bytes]
        return output

    def _batch_changed_paths(self, good: str, bad: str) -> tuple[dict[str, list[str]], bool]:
        revision = f"{good}..{bad}"
        try:
            output = self._git(
                [
                    "log",
                    "--reverse",
                    "--pretty=format:COMMIT:%H",
                    "--name-only",
                    revision,
                ],
                timeout=self.list_timeout_sec,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "Batch git log timed out after %ss; using per-commit path listing.",
                self.list_timeout_sec,
            )
            return {}, False
        if not output.strip():
            return {}, False
        return parse_name_only_log(output), True

    def _git(self, args: list[str], timeout: int) -> str:
        proc = subprocess.Popen(
            ["git", "-C", str(self.repo_path), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        try:
            output, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise
        if not output:
            return ""
        return _decode_git_bytes(output)

    # ======================================================

    def current_branch(self) -> str:

        try:

            return self.repo.active_branch.name

        except TypeError:

            return "DETACHED"

    # ======================================================

    def current_commit(self) -> str:

        return self.repo.head.commit.hexsha

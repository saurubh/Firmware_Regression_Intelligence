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
from fri.logger import logger
from fri.models import Commit

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

DIFF_TIMEOUT_SEC = 15
PATH_TIMEOUT_SEC = 20
MAX_SOURCE_PATHS = 120
MAX_DIFF_BYTES = 1_000_000


def _is_source(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in SOURCE_SUFFIXES


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

        commits: list[Commit] = []

        for index, git_commit in enumerate(
            self.repo.iter_commits(revision, reverse=True),
            start=1,
        ):
            if index % 50 == 0:
                logger.info("  still listing: %d commits...", index)
            commits.append(
                Commit(
                    sha=git_commit.hexsha,
                    short_sha=git_commit.hexsha[:8],
                    author=str(git_commit.author),
                    email=git_commit.author.email,
                    date=datetime.fromtimestamp(git_commit.committed_date),
                    message=git_commit.message.strip(),
                    files=[],
                    insertions=0,
                    deletions=0,
                    is_merge_commit=(len(git_commit.parents) > 1),
                    git_object=git_commit,
                )
            )

        logger.info("Listed %d commits. Next: analyze each diff.", len(commits))
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
        git_commit = commit.git_object
        if git_commit is None:
            return []
        try:
            output = self._git(
                ["diff-tree", "-r", "--name-only", "--no-commit-id", commit.sha],
                timeout=PATH_TIMEOUT_SEC,
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
        parent = git_commit.parents[0].hexsha
        sources = [path for path in commit.files if _is_source(path)][:MAX_SOURCE_PATHS]
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
                timeout=DIFF_TIMEOUT_SEC,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "git diff timed out after %ss for %s (%d source files); skipping blob",
                DIFF_TIMEOUT_SEC,
                commit.short_sha,
                len(sources),
            )
            return ""
        finally:
            stop.set()
        if len(output) > MAX_DIFF_BYTES:
            logger.info("Truncating diff for %s", commit.short_sha)
            return output[:MAX_DIFF_BYTES]
        return output

    def _git(self, args: list[str], timeout: int) -> str:
        proc = subprocess.Popen(
            ["git", "-C", str(self.repo_path), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        try:
            output, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise
        return output or ""

    # ======================================================

    def current_branch(self) -> str:

        try:

            return self.repo.active_branch.name

        except TypeError:

            return "DETACHED"

    # ======================================================

    def current_commit(self) -> str:

        return self.repo.head.commit.hexsha
"""
Firmware Regression Intelligence (FRI)

Git Collector

Responsible only for interacting with Git.

Responsibilities
----------------
* Resolve build identifiers
* Collect commits
* Retrieve commit diffs

No parsing.
No classification.
No scoring.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from git import Repo
from git.exc import InvalidGitRepositoryError

from fri.collector.build_resolver import BuildResolver
from fri.logger import logger
from fri.models import Commit


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

    def get_diff(
        self,
        commit: Commit
    ) -> str:
        """
        Return unified diff for a commit.
        """

        git_commit = commit.git_object

        if git_commit is None:

            return ""

        if not git_commit.parents:

            return ""

        parent = git_commit.parents[0]
        try:
            text = self.repo.git.diff(
                parent.hexsha,
                git_commit.hexsha,
                unified=0,
            )
        except Exception:
            return ""
        # Huge binary/firmware blobs can stall keyword scans.
        limit = 2_000_000
        if len(text) > limit:
            logger.info(
                "Truncating diff for %s (%s bytes -> %s)",
                commit.short_sha,
                f"{len(text):,}",
                f"{limit:,}",
            )
            return text[:limit]
        return text

    # ======================================================

    def current_branch(self) -> str:

        try:

            return self.repo.active_branch.name

        except TypeError:

            return "DETACHED"

    # ======================================================

    def current_commit(self) -> str:

        return self.repo.head.commit.hexsha
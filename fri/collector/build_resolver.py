"""
Firmware Regression Intelligence (FRI)

Build Resolver

Converts firmware build identifiers into Git commit SHAs.

Supported inputs
----------------
- Full SHA
- Short SHA
- Branch
- Tag
- HEAD
- HEAD~N

Future
------
- Jenkins Build Number
- Firmware Manifest
- Build Database
"""

from __future__ import annotations

import re

from git.exc import BadName, GitCommandError

from fri.logger import logger


class BuildResolver:

    def __init__(self, repo):

        self.repo = repo

    # ------------------------------------------------------
    # Public API
    # ------------------------------------------------------

    def resolve(self, build: str) -> str:
        """
        Resolve a build identifier into
        a full Git SHA.
        """

        #
        # HEAD
        #
        if build == "HEAD":

            sha = self.repo.head.commit.hexsha

            logger.info("Resolved HEAD -> %s", sha[:8])

            return sha

        #
        # HEAD~N
        #
        if re.match(r"^HEAD~\d+$", build):

            sha = self.repo.commit(build).hexsha

            logger.info(
                "Resolved %s -> %s",
                build,
                sha[:8]
            )

            return sha

        #
        # Branch / Tag / SHA
        #
        try:

            sha = self.repo.commit(build).hexsha

            logger.info(
                "Resolved %s -> %s",
                build,
                sha[:8]
            )

            return sha

        except BadName as err:

            raise RuntimeError(

                f"Unable to resolve build '{build}'."

            ) from err

    @staticmethod
    def resolve_label(repo, build: str) -> tuple[str | None, str]:
        """
        Resolve a tag, branch, or SHA in *this* repository.

        Tags are preferred so the same BIOS tag name can be looked up
        independently in edk2, Intel, and the platform tree.

        Returns (sha, source) where source is tag, branch, sha, ref, or missing.
        """
        if not build:
            return None, "missing"
        try:
            sha = repo.git.rev_parse("--verify", f"refs/tags/{build}^{{commit}}")
            return sha.strip(), "tag"
        except GitCommandError:
            pass
        try:
            sha = repo.git.rev_parse("--verify", f"refs/heads/{build}")
            return sha.strip(), "branch"
        except GitCommandError:
            pass
        try:
            sha = repo.commit(build).hexsha
            if _looks_like_sha(build):
                return sha, "sha"
            return sha, "ref"
        except Exception:
            return None, "missing"

    # ------------------------------------------------------

    def exists(self, build: str) -> bool:

        try:

            self.resolve(build)

            return True

        except Exception:

            return False

    # ------------------------------------------------------

    def describe(self, sha: str) -> str:
        """
        Return nearest tag if available.
        """

        try:

            return self.repo.git.describe(

                sha,

                "--tags",

                "--always"

            )

        except Exception:

            return sha[:8]

    # ------------------------------------------------------

    def current_branch(self):

        try:

            return self.repo.active_branch.name

        except Exception:

            return "DETACHED"

    # ------------------------------------------------------

    def current_commit(self):

        return self.repo.head.commit.hexsha


def _looks_like_sha(value: str) -> bool:
    token = value.strip().lower()
    return 7 <= len(token) <= 40 and all(ch in "0123456789abcdef" for ch in token)

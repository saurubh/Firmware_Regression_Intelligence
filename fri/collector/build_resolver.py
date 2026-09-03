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

from git.exc import BadName

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

        except BadName:

            raise RuntimeError(

                f"Unable to resolve build '{build}'."

            )

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

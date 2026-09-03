"""
Multi-repo / submodule pin discovery for UEFI BIOS workspaces.

A BIOS *build* is a joint pin-set: platform tree + edk2 + edk2-platforms
+ Intel/AMD silicon, often as git submodules. FRI compares those pins
between a known-good superproject revision and a known-bad one.
"""

from __future__ import annotations

import configparser
from pathlib import Path

import yaml
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from fri.logger import logger
from fri.models import RepoDelta, RepoWindow, WorkspacePlan


class WorkspaceCollector:
    """Discover which Git repos moved between two BIOS builds."""

    def plan_from_workspace(self, workspace: str, good: str, bad: str) -> WorkspacePlan:
        root = Path(workspace).resolve()
        repo = Repo(root)
        good_sha = repo.commit(good).hexsha
        bad_sha = repo.commit(bad).hexsha
        windows: list[RepoWindow] = []
        deltas: list[RepoDelta] = []

        # Superproject itself
        windows.append(
            RepoWindow(
                name=root.name or "platform",
                path=str(root),
                good_sha=good_sha,
                bad_sha=bad_sha,
                changed=good_sha != bad_sha,
            )
        )
        deltas.append(
            RepoDelta(
                name=windows[0].name,
                path=".",
                good_sha=good_sha,
                bad_sha=bad_sha,
                status="changed" if good_sha != bad_sha else "unchanged",
            )
        )

        good_pins = self._pins(repo, root, good_sha, prefix="")
        bad_pins = self._pins(repo, root, bad_sha, prefix="")
        paths = sorted(set(good_pins) | set(bad_pins))
        for relpath in paths:
            old = good_pins.get(relpath, "")
            new = bad_pins.get(relpath, "")
            git_path = self._openable_path(root, relpath)
            status = "changed"
            if not old or not new:
                status = "missing"
            elif old == new:
                status = "unchanged"
            if git_path is None:
                status = "missing"
            deltas.append(
                RepoDelta(
                    name=relpath.replace("\\", "/"),
                    path=relpath,
                    good_sha=old,
                    bad_sha=new,
                    status=status,
                )
            )
            if status == "changed" and git_path is not None and old and new:
                windows.append(
                    RepoWindow(
                        name=relpath.replace("\\", "/"),
                        path=str(git_path),
                        good_sha=old,
                        bad_sha=new,
                        changed=True,
                    )
                )
                logger.info(
                    "Submodule %s moved %s -> %s",
                    relpath,
                    old[:8],
                    new[:8],
                )

        return WorkspacePlan(
            workspace=str(root),
            good_label=good,
            bad_label=bad,
            windows=windows,
            deltas=deltas,
        )

    def plan_from_manifest(self, manifest_path: str) -> WorkspacePlan:
        path = Path(manifest_path).resolve()
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        workspace = str(Path(raw.get("workspace") or path.parent).expanduser().resolve())
        good = str(raw.get("good") or "")
        bad = str(raw.get("bad") or "")
        listed = raw.get("repos") or []
        if listed:
            windows = []
            deltas = []
            for item in listed:
                name = str(item.get("name") or item.get("path") or "repo")
                rel = str(item.get("path") or ".")
                repo_dir = Path(workspace) / rel if rel not in {".", ""} else Path(workspace)
                repo_good = str(item.get("good") or good)
                repo_bad = str(item.get("bad") or bad)
                if not repo_good or not repo_bad:
                    raise RuntimeError(
                        f"Manifest repo '{name}' needs good/bad pins "
                        "(or top-level good/bad)."
                    )
                opened = Repo(str(repo_dir))
                good_sha = opened.commit(repo_good).hexsha
                bad_sha = opened.commit(repo_bad).hexsha
                changed = good_sha != bad_sha
                windows.append(
                    RepoWindow(
                        name=name,
                        path=str(repo_dir.resolve()),
                        good_sha=good_sha,
                        bad_sha=bad_sha,
                        changed=changed,
                    )
                )
                deltas.append(
                    RepoDelta(
                        name=name,
                        path=rel,
                        good_sha=good_sha,
                        bad_sha=bad_sha,
                        status="changed" if changed else "unchanged",
                    )
                )
            return WorkspacePlan(
                workspace=workspace,
                good_label=good or "manifest",
                bad_label=bad or "manifest",
                windows=windows,
                deltas=deltas,
            )
        if not good or not bad:
            raise RuntimeError("Manifest needs workspace + good + bad, or explicit repos.")
        return self.plan_from_workspace(workspace, good, bad)

    def _pins(
        self,
        repo: Repo,
        root: Path,
        commit: str,
        prefix: str,
        depth: int = 0,
    ) -> dict[str, str]:
        if depth > 5:
            return {}
        pins: dict[str, str] = {}
        for relpath in self._gitmodules_paths(repo, commit):
            sha = self._gitlink_sha(repo, commit, relpath)
            if not sha:
                continue
            key = f"{prefix}{relpath}" if not prefix else f"{prefix}/{relpath}"
            if prefix == "":
                key = relpath
            pins[key] = sha
            nested = self._open_repo(root, key)
            if nested is None:
                continue
            try:
                nested.commit(sha)
            except Exception:
                continue
            pins.update(
                self._pins(nested, root, sha, prefix=key, depth=depth + 1)
            )
        return pins

    @staticmethod
    def _gitmodules_paths(repo: Repo, commit: str) -> list[str]:
        try:
            text = repo.git.show(f"{commit}:.gitmodules")
        except GitCommandError:
            return []
        parser = configparser.ConfigParser()
        try:
            parser.read_string(text)
        except configparser.Error:
            return []
        paths = []
        for section in parser.sections():
            path = parser[section].get("path")
            if path:
                paths.append(path.strip())
        return paths

    @staticmethod
    def _gitlink_sha(repo: Repo, commit: str, path: str) -> str | None:
        try:
            line = repo.git.ls_tree(commit, "--", path)
        except GitCommandError:
            return None
        if not line:
            return None
        meta = line.split("\t", 1)[0].split()
        if len(meta) < 3 or meta[1] != "commit":
            return None
        return meta[2]

    @staticmethod
    def _open_repo(root: Path, relpath: str) -> Repo | None:
        opened = WorkspaceCollector._openable_path(root, relpath)
        if opened is None:
            return None
        try:
            return Repo(str(opened))
        except (InvalidGitRepositoryError, Exception):
            return None

    @staticmethod
    def _openable_path(root: Path, relpath: str) -> Path | None:
        checkout = root / relpath
        try:
            Repo(str(checkout))
            return checkout
        except (InvalidGitRepositoryError, Exception):
            pass
        module = root / ".git" / "modules" / relpath
        if module.exists():
            try:
                Repo(str(module))
                return module
            except Exception:
                return None
        return None

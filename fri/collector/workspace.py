"""
Multi-repo / submodule pin discovery for UEFI BIOS workspaces.

A BIOS *build* is a joint pin-set: platform tree + edk2 + edk2-platforms
+ Intel/AMD silicon, often as git submodules. FRI compares those pins
between a known-good superproject revision and a known-bad one.

When --good/--bad are tag names, FRI looks up the *same* tag in every
sub-repo first, then falls back to the superproject gitlink pin.
"""

from __future__ import annotations

import configparser
from pathlib import Path

import yaml
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from fri.collector.build_resolver import BuildResolver
from fri.logger import logger
from fri.models import RepoDelta, RepoWindow, WorkspacePlan


class WorkspaceCollector:
    """Discover which Git repos moved between two BIOS builds."""

    def plan_from_workspace(self, workspace: str, good: str, bad: str) -> WorkspacePlan:
        root = Path(workspace).resolve()
        repo = Repo(root)
        windows: list[RepoWindow] = []
        deltas: list[RepoDelta] = []

        super_name = root.name or "platform"
        good_sha, good_src, bad_sha, bad_src, status = self._pair(
            repo,
            good,
            bad,
            gitlink_good="",
            gitlink_bad="",
            name=super_name,
        )
        windows.append(
            RepoWindow(
                name=super_name,
                path=str(root),
                good_sha=good_sha,
                bad_sha=bad_sha,
                changed=status == "changed",
            )
        )
        deltas.append(
            RepoDelta(
                name=super_name,
                path=".",
                good_sha=good_sha,
                bad_sha=bad_sha,
                status=status,
                good_source=good_src,
                bad_source=bad_src,
            )
        )

        for relpath in self._discover_submodule_paths(repo, root, good, bad, good_sha, bad_sha):
            opened = self._open_repo(root, relpath)
            parent, rel_in_parent = self._parent_for(root, repo, relpath)
            parent_good = good_sha
            parent_bad = bad_sha
            if parent is not None and parent is not repo:
                parent_good, _ = BuildResolver.resolve_label(parent, good)
                parent_bad, _ = BuildResolver.resolve_label(parent, bad)
            gitlink_good = (
                self._gitlink_sha(parent, parent_good, rel_in_parent) if parent is not None else ""
            )
            gitlink_bad = (
                self._gitlink_sha(parent, parent_bad, rel_in_parent) if parent is not None else ""
            )
            g_sha, g_src, b_sha, b_src, status = self._pair(
                opened,
                good,
                bad,
                gitlink_good=gitlink_good or "",
                gitlink_bad=gitlink_bad or "",
                name=relpath,
            )
            deltas.append(
                RepoDelta(
                    name=relpath.replace("\\", "/"),
                    path=relpath,
                    good_sha=g_sha,
                    bad_sha=b_sha,
                    status=status if opened is not None else "missing",
                    good_source=g_src if opened is not None else "missing",
                    bad_source=b_src if opened is not None else "missing",
                )
            )
            git_path = self._openable_path(root, relpath)
            if status == "changed" and git_path is not None and g_sha and b_sha:
                windows.append(
                    RepoWindow(
                        name=relpath.replace("\\", "/"),
                        path=str(git_path),
                        good_sha=g_sha,
                        bad_sha=b_sha,
                        changed=True,
                    )
                )
                logger.info(
                    "Repo %s moved %s (%s) -> %s (%s)",
                    relpath,
                    g_sha[:8],
                    g_src,
                    b_sha[:8],
                    b_src,
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
                g_sha, g_src, b_sha, b_src, status = self._pair(
                    opened,
                    repo_good,
                    repo_bad,
                    gitlink_good="",
                    gitlink_bad="",
                    name=name,
                )
                if not g_sha or not b_sha:
                    raise RuntimeError(
                        f"Manifest repo '{name}' has no tag/ref "
                        f"'{repo_good}' and/or '{repo_bad}'."
                    )
                windows.append(
                    RepoWindow(
                        name=name,
                        path=str(repo_dir.resolve()),
                        good_sha=g_sha,
                        bad_sha=b_sha,
                        changed=status == "changed",
                    )
                )
                deltas.append(
                    RepoDelta(
                        name=name,
                        path=rel,
                        good_sha=g_sha,
                        bad_sha=b_sha,
                        status=status,
                        good_source=g_src,
                        bad_source=b_src,
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

    def plan_from_gitman(self, gitman_path: str, good: str, bad: str) -> WorkspacePlan:
        """Inspect every `sources[].name` folder from gitman.yml for the same tags."""
        path = Path(gitman_path).expanduser().resolve()
        if not path.is_file():
            raise RuntimeError(f"gitman.yml not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        location = str(raw.get("location") or ".")
        root = (path.parent / location).resolve()
        names = []
        for key in ("sources", "sources_locked"):
            for item in raw.get(key) or []:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                if name and name not in names:
                    names.append(name)
        if not names:
            raise RuntimeError(f"{path} has no sources[].name entries.")
        logger.info("gitman.yml: %d source folder(s) under %s", len(names), root)

        entries: list[tuple[str, Path, str]] = []
        seen: set[str] = set()
        if _is_git_dir(root):
            entries.append((root.name or "platform", root, "."))
            seen.add(str(root))
        for name in names:
            repo_dir = (root / name).resolve()
            key = str(repo_dir)
            if key in seen:
                continue
            seen.add(key)
            entries.append((name, repo_dir, name))

        windows: list[RepoWindow] = []
        deltas: list[RepoDelta] = []
        for name, repo_dir, rel in entries:
            opened = _open_if_git(repo_dir)
            g_sha, g_src, b_sha, b_src, status = self._pair(
                opened,
                good,
                bad,
                gitlink_good="",
                gitlink_bad="",
                name=name,
            )
            if opened is None:
                status = "missing"
                g_src = b_src = "missing"
            logger.info(
                "  %-22s  %s  via %s/%s",
                name,
                status,
                g_src,
                b_src,
            )
            deltas.append(
                RepoDelta(
                    name=name,
                    path=rel,
                    good_sha=g_sha,
                    bad_sha=b_sha,
                    status=status,
                    good_source=g_src,
                    bad_source=b_src,
                )
            )
            if status == "changed" and opened is not None and g_sha and b_sha:
                windows.append(
                    RepoWindow(
                        name=name,
                        path=str(repo_dir),
                        good_sha=g_sha,
                        bad_sha=b_sha,
                        changed=True,
                    )
                )
        return WorkspacePlan(
            workspace=str(root),
            good_label=good,
            bad_label=bad,
            windows=windows,
            deltas=deltas,
        )

    def _pair(
        self,
        repo: Repo | None,
        good: str,
        bad: str,
        gitlink_good: str,
        gitlink_bad: str,
        name: str,
    ) -> tuple[str, str, str, str, str]:
        good_sha, good_src = self._resolve_with_fallback(repo, good, gitlink_good, name, "good")
        bad_sha, bad_src = self._resolve_with_fallback(repo, bad, gitlink_bad, name, "bad")
        if not good_sha or not bad_sha:
            status = "missing"
        elif good_sha == bad_sha:
            status = "unchanged"
        else:
            status = "changed"
        return good_sha, good_src, bad_sha, bad_src, status

    @staticmethod
    def _resolve_with_fallback(
        repo: Repo | None,
        label: str,
        gitlink: str,
        name: str,
        side: str,
    ) -> tuple[str, str]:
        if repo is not None:
            sha, source = BuildResolver.resolve_label(repo, label)
            if sha:
                if gitlink and gitlink != sha and source == "tag":
                    logger.info(
                        "%s %s: tag '%s' is %s (gitlink was %s)",
                        name,
                        side,
                        label,
                        sha[:8],
                        gitlink[:8],
                    )
                return sha, source
        if gitlink:
            return gitlink, "gitlink"
        return "", "missing"

    def _discover_submodule_paths(
        self,
        repo: Repo,
        root: Path,
        good: str,
        bad: str,
        good_sha: str,
        bad_sha: str,
        prefix: str = "",
        depth: int = 0,
    ) -> list[str]:
        if depth > 5:
            return []
        rels: set[str] = set()
        for commit in (good_sha, bad_sha, "HEAD"):
            if commit:
                rels.update(self._gitmodules_paths(repo, commit))
        rels.update(self._gitmodules_from_file(root if prefix == "" else root / prefix))
        found: list[str] = []
        for relpath in sorted(rels):
            key = f"{prefix}/{relpath}" if prefix else relpath
            if key not in found:
                found.append(key)
            nested = self._open_repo(root, key)
            if nested is None:
                continue
            nested_good, _ = BuildResolver.resolve_label(nested, good)
            nested_bad, _ = BuildResolver.resolve_label(nested, bad)
            if not nested_good:
                nested_good = self._gitlink_sha(repo, good_sha, relpath) if good_sha else ""
            if not nested_bad:
                nested_bad = self._gitlink_sha(repo, bad_sha, relpath) if bad_sha else ""
        return list(dict.fromkeys(found))

    def _parent_for(self, root: Path, super_repo: Repo, relpath: str) -> tuple[Repo | None, str]:
        parts = Path(relpath).parts
        if len(parts) == 1:
            return super_repo, relpath
        parent_key = str(Path(*parts[:-1]))
        parent = self._open_repo(root, parent_key)
        return parent, parts[-1]

    @staticmethod
    def _gitmodules_from_file(repo_dir: Path) -> list[str]:
        path = repo_dir / ".gitmodules"
        if not path.is_file():
            return []
        parser = configparser.ConfigParser()
        try:
            parser.read_string(path.read_text(encoding="utf-8"))
        except (OSError, configparser.Error):
            return []
        paths = []
        for section in parser.sections():
            value = parser[section].get("path")
            if value:
                paths.append(value.strip())
        return paths

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
    def _gitlink_sha(repo: Repo, commit: str, path: str) -> str:
        if not commit or not path:
            return ""
        try:
            line = repo.git.ls_tree(commit, "--", path)
        except GitCommandError:
            return ""
        if not line:
            return ""
        meta = line.split("\t", 1)[0].split()
        if len(meta) < 3 or meta[1] != "commit":
            return ""
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


def _is_git_dir(path: Path) -> bool:
    try:
        Repo(str(path))
        return True
    except (InvalidGitRepositoryError, Exception):
        return False


def _open_if_git(path: Path) -> Repo | None:
    try:
        return Repo(str(path))
    except (InvalidGitRepositoryError, Exception):
        return None

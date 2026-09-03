"""
Firmware Regression Intelligence (FRI)

Configuration Manager

Loads the YAML taxonomy: domains (paths + keywords) and failure profiles.
The CLI reads --failure choices from failure_profiles.yaml, not from
hardcoded Python tuples.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from fri.constants import COMPONENT_MAP, CONFIG_FILE, FAILURE_PROFILE
from fri.models import DomainSpec, FailureProfile
from fri.utils.matching import compact_token


class Config:
    """Singleton configuration manager."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if self._loaded:
            return
        self._config = self._load_yaml(CONFIG_FILE)
        self._domains = self._load_domains(self._load_yaml(COMPONENT_MAP))
        self._failure_profiles = self._load_failure_profiles(FAILURE_PROFILE)
        self.validate()
        self._loaded = True

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(path, encoding="utf-8") as fp:
            data = yaml.safe_load(fp)
        return data or {}

    @staticmethod
    def _load_domains(mapping: dict[str, Any]) -> dict[str, DomainSpec]:
        domains: dict[str, DomainSpec] = {}
        for name, spec in mapping.items():
            if isinstance(spec, list):
                paths = spec
                keywords = [name]
            elif isinstance(spec, dict):
                paths = spec.get("paths") or spec.get("path_patterns") or []
                keywords = spec.get("keywords") or [name]
            else:
                continue
            domains[name] = DomainSpec(
                name=name,
                paths=[
                    str(item).replace("\\", "/").lower().strip()
                    for item in paths
                    if item
                ],
                keywords=[str(item) for item in keywords if isinstance(item, str) and item],
            )
        return domains

    @staticmethod
    def _load_failure_profiles(path: Path) -> dict[str, FailureProfile]:
        raw = Config._load_yaml(path)
        profiles: dict[str, FailureProfile] = {}
        for name, profile in raw.items():
            if not isinstance(profile, dict):
                continue
            profiles[name.lower()] = FailureProfile(
                name=name.lower(),
                description=str(profile.get("description", "")).strip(),
                domains=profile.get("subsystems", []) or [],
                keywords=[
                    item
                    for item in (profile.get("keywords") or [])
                    if isinstance(item, str)
                ],
                path_patterns=[
                    item
                    for item in (profile.get("path_patterns") or [])
                    if isinstance(item, str)
                ],
                risk_signals=[
                    item
                    for item in (profile.get("risk_signals") or [])
                    if isinstance(item, str)
                ],
                related=[
                    str(item).lower()
                    for item in (profile.get("related") or [])
                    if item
                ],
            )
        return profiles

    def validate(self):
        if not self._domains:
            raise RuntimeError("Invalid component_map.yaml")
        if not self._failure_profiles:
            raise RuntimeError("Invalid failure_profiles.yaml")

    @property
    def settings(self):
        return self._config

    @property
    def domains_spec(self) -> dict[str, DomainSpec]:
        return self._domains

    @property
    def component_map(self) -> dict[str, list[str]]:
        return {name: spec.paths for name, spec in self._domains.items()}

    @property
    def failure_profiles(self) -> dict[str, FailureProfile]:
        return self._failure_profiles

    @property
    def failure_names(self) -> list[str]:
        return sorted(self._failure_profiles)

    def keywords(self) -> list[str]:
        """Union of domain and profile keywords — single catalog for parser/diff."""
        seen: dict[str, str] = {}
        for spec in self._domains.values():
            for keyword in spec.keywords:
                seen.setdefault(compact_token(keyword), keyword)
        for profile in self._failure_profiles.values():
            for keyword in profile.keywords:
                seen.setdefault(compact_token(keyword), keyword)
        return sorted(seen.values(), key=str.upper)

    def keyword_domains(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for spec in self._domains.values():
            for keyword in spec.keywords:
                mapping.setdefault(compact_token(keyword), spec.name)
        return mapping

    def get(self, key, default=None):
        return self._config.get(key, default)

    def has(self, key):
        return key in self._config

    def is_debug(self) -> bool:
        return bool(self._config.get("debug", False))

    def get_failure_profile(self, name: str) -> FailureProfile | None:
        return self._failure_profiles.get(name.lower())

    def domains(self):
        return list(self._domains.keys())

    def reload(self):
        self._loaded = False
        self.__init__()


config = Config()

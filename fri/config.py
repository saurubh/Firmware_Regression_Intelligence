"""
Firmware Regression Intelligence (FRI)

Configuration Manager

Loads and validates all application configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from fri.constants import (
    COMPONENT_MAP,
    CONFIG_FILE,
    FAILURE_PROFILE,
)
from fri.models import FailureProfile


class Config:
    """
    Singleton configuration manager.
    """

    _instance = None

    def __new__(cls):

        if cls._instance is None:

            cls._instance = super().__new__(cls)

            cls._instance._loaded = False

        return cls._instance

    def __init__(self):

        if self._loaded:
            return

        #
        # Raw configuration
        #
        self._config = self._load_yaml(CONFIG_FILE)

        self._component_map = self._normalize_component_map(
            self._load_yaml(COMPONENT_MAP)
        )

        self._failure_profiles = self._load_failure_profiles(
            FAILURE_PROFILE
        )

        self.validate()

        self._loaded = True

    # ==========================================================
    # YAML Loader
    # ==========================================================

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:

        if not path.exists():

            raise FileNotFoundError(
                f"Configuration file not found: {path}"
            )

        with open(path, encoding="utf-8") as fp:

            data = yaml.safe_load(fp)

        return data or {}

    # ==========================================================
    # Component Map
    # ==========================================================

    @staticmethod
    def _normalize_component_map(
        mapping: dict[str, Any]
    ) -> dict[str, list]:

        normalized = {}

        for domain, paths in mapping.items():

            normalized[domain] = [

                p.replace("\\", "/").lower()

                for p in paths

            ]

        return normalized

    # ==========================================================
    # Failure Profiles
    # ==========================================================

    @staticmethod
    def _load_failure_profiles(
        path: Path
    ) -> dict[str, FailureProfile]:

        raw = Config._load_yaml(path)

        profiles = {}

        for name, profile in raw.items():

            profiles[name.lower()] = FailureProfile(
                name=name,
                description=str(profile.get("description", "")).strip(),
                domains=profile.get("subsystems", []) or [],
                keywords=[item for item in (profile.get("keywords") or []) if isinstance(item, str)],
                path_patterns=[item for item in (profile.get("path_patterns") or []) if isinstance(item, str)],
                risk_signals=[item for item in (profile.get("risk_signals") or []) if isinstance(item, str)],
            )

        return profiles

    # ==========================================================
    # Validation
    # ==========================================================

    def validate(self):

        if not isinstance(self._component_map, dict):

            raise RuntimeError(

                "Invalid component_map.yaml"

            )

        if not isinstance(

            self._failure_profiles,

            dict

        ):

            raise RuntimeError(

                "Invalid failure_profiles.yaml"

            )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def settings(self):

        return self._config

    @property
    def component_map(self):

        return self._component_map

    @property
    def failure_profiles(self):

        return self._failure_profiles

    # ==========================================================
    # Helpers
    # ==========================================================

    def get(

        self,

        key,

        default=None

    ):

        return self._config.get(

            key,

            default

        )

    def has(self, key):

        return key in self._config

    def is_debug(self) -> bool:

        return bool(

            self._config.get(

                "debug",

                False

            )

        )

    def get_failure_profile(

        self,

        name: str

    ) -> FailureProfile | None:

        return self._failure_profiles.get(

            name.lower()

        )

    def domains(self):

        return list(

            self._component_map.keys()

        )

    # ==========================================================
    # Reload
    # ==========================================================

    def reload(self):

        self._loaded = False

        self.__init__()


#
# Global singleton
#
config = Config()
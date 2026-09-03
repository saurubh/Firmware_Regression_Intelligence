"""
Firmware Regression Intelligence (FRI)

Domain Models

Core business objects shared across the entire application.

These classes intentionally contain NO business logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Commit:
    """Represents a single Git commit."""

    sha: str
    short_sha: str
    author: str
    email: str
    date: datetime
    message: str
    files: list[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
    jira: str | None = None
    merge_request: str | None = None
    intent: str = "Unknown"
    primary_domain: str = "Unknown"
    domains: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    is_merge_commit: bool = False
    git_object: Any = field(default=None, repr=False, compare=False)

    @property
    def total_changes(self) -> int:
        return self.insertions + self.deletions

    @property
    def subject(self) -> str:
        if not self.message:
            return ""
        return self.message.splitlines()[0].strip()


@dataclass
class DomainSpec:
    """One firmware domain from component_map.yaml."""

    name: str
    paths: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass
class FailureProfile:
    """Represents one regression type loaded from failure_profiles.yaml."""

    name: str
    description: str = ""
    domains: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    path_patterns: list[str] = field(default_factory=list)
    risk_signals: list[str] = field(default_factory=list)
    phase: str = ""
    breadth: str = "narrow"
    related: list[str] = field(default_factory=list)


@dataclass
class Hazard:
    """A high-risk firmware or OS-boot change found in a diff."""

    name: str
    category: str
    severity: str
    detail: str


@dataclass
class DiffEvidence:
    """Information extracted from a Git diff."""

    score: int = 0
    tokens: list[str] = field(default_factory=list)
    firmware_keywords: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    modified_functions: list[str] = field(default_factory=list)
    modified_macros: list[str] = field(default_factory=list)
    added_lines: int = 0
    removed_lines: int = 0
    hazards: list[Hazard] = field(default_factory=list)
    pcd_names: list[str] = field(default_factory=list)
    protocol_hits: list[str] = field(default_factory=list)
    boot_api_hits: list[str] = field(default_factory=list)
    docs_only: bool = False
    comment_only: bool = False

    @property
    def total_lines(self) -> int:
        return self.added_lines + self.removed_lines


@dataclass
class RegressionCandidate:
    """One possible regression-causing commit."""

    commit: Commit
    rank: int = 0
    confidence: int = 0
    score: int = 0
    matched_domains: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    matched_files: list[str] = field(default_factory=list)
    matched_paths: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    hazards: list[str] = field(default_factory=list)
    signal_count: int = 0
    phases: list[str] = field(default_factory=list)
    primary_phase: str = "Unknown"
    vendor: str = "common"


@dataclass
class ModuleCandidate:
    """Aggregate view of a firmware module."""

    name: str
    confidence: int
    strength: float = 0.0
    commits: list[Commit] = field(default_factory=list)
    jiras: list[str] = field(default_factory=list)
    merge_requests: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


@dataclass
class ValidationStep:
    """One validation action for proving a regression."""

    priority: int
    commit: Commit
    description: str
    estimated_minutes: int = 45


@dataclass
class BisectPlan:
    """Suggested validation plan."""

    good_sha: str
    bad_sha: str
    commands: list[str] = field(default_factory=list)
    steps: list[ValidationStep] = field(default_factory=list)


@dataclass
class RegressionStatistics:
    """Summary statistics for the investigation."""

    total_commits: int = 0
    filtered_commits: int = 0
    candidate_commits: int = 0
    module_count: int = 0
    execution_time: float = 0.0
    hazard_commits: int = 0
    high_confidence: int = 0


@dataclass
class BootPhaseSpec:
    """One ordered boot phase from CPU reset to OS."""

    name: str
    order: int = 0
    vendors: list[str] = field(default_factory=list)
    edge: str = ""
    description: str = ""
    domains: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)


@dataclass
class PhaseFinding:
    """Aggregated suspicion for one boot phase in the good→bad window."""

    name: str
    order: int
    confidence: int
    strength: float
    edge: str
    description: str
    vendors: list[str] = field(default_factory=list)
    commits: list[Commit] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


@dataclass
class TriagePlan:
    """Where to start debugging between good SHA and failing SHA."""

    start_phase: str = ""
    start_reason: str = ""
    vendor_hint: str = "common"
    phases: list[PhaseFinding] = field(default_factory=list)


@dataclass
class RegressionReport:
    """Complete investigation output."""

    good_sha: str
    bad_sha: str
    failure: str
    profile_description: str = ""
    related_topics: list[str] = field(default_factory=list)
    covered_topics: list[str] = field(default_factory=list)
    commits: list[Commit] = field(default_factory=list)
    candidates: list[RegressionCandidate] = field(default_factory=list)
    modules: list[ModuleCandidate] = field(default_factory=list)
    bisect: BisectPlan | None = None
    triage: TriagePlan | None = None
    statistics: RegressionStatistics = field(default_factory=RegressionStatistics)
    generated_at: datetime = field(default_factory=datetime.now)

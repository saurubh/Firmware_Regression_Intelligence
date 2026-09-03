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
from typing import List
from typing import Optional


# ==========================================================
# Commit
# ==========================================================

@dataclass
class Commit:
    """
    Represents a single Git commit.
    """

    #
    # Git metadata
    #
    sha: str

    short_sha: str

    author: str

    email: str

    date: datetime

    message: str

    #
    # File statistics
    #
    files: List[str] = field(default_factory=list)

    insertions: int = 0

    deletions: int = 0

    #
    # Parsed metadata
    #
    jira: Optional[str] = None

    merge_request: Optional[str] = None

    intent: str = "Unknown"

    primary_domain: str = "Unknown"

    domains: List[str] = field(default_factory=list)

    keywords: List[str] = field(default_factory=list)

    #
    # Git properties
    #
    is_merge_commit: bool = False

    git_object: Any = field(
        default=None,
        repr=False,
        compare=False
    )

    @property
    def total_changes(self) -> int:
        return self.insertions + self.deletions


# ==========================================================
# Failure Profile
# ==========================================================

@dataclass
class FailureProfile:
    """
    Represents one regression type.

    Loaded from failure_profiles.yaml.
    """

    name: str

    domains: List[str] = field(default_factory=list)

    keywords: List[str] = field(default_factory=list)


# ==========================================================
# Diff Evidence
# ==========================================================

@dataclass
class DiffEvidence:
    """
    Information extracted from a Git diff.
    """

    score: int = 0

    tokens: List[str] = field(default_factory=list)

    firmware_keywords: List[str] = field(default_factory=list)

    modified_files: List[str] = field(default_factory=list)

    modified_functions: List[str] = field(default_factory=list)

    modified_macros: List[str] = field(default_factory=list)

    added_lines: int = 0

    removed_lines: int = 0

    @property
    def total_lines(self) -> int:
        return self.added_lines + self.removed_lines


# ==========================================================
# Regression Candidate
# ==========================================================

@dataclass
class RegressionCandidate:
    """
    One possible regression-causing commit.
    """

    commit: Commit

    rank: int = 0

    confidence: int = 0

    score: int = 0

    matched_domains: List[str] = field(default_factory=list)

    matched_keywords: List[str] = field(default_factory=list)

    matched_files: List[str] = field(default_factory=list)

    reasons: List[str] = field(default_factory=list)

    evidence: List[str] = field(default_factory=list)


# ==========================================================
# Module Candidate
# ==========================================================

@dataclass
class ModuleCandidate:
    """
    Aggregate view of a firmware module.
    """

    name: str

    confidence: int

    commits: List[Commit] = field(default_factory=list)

    jiras: List[str] = field(default_factory=list)

    merge_requests: List[str] = field(default_factory=list)

    authors: List[str] = field(default_factory=list)

    files: List[str] = field(default_factory=list)

    reasons: List[str] = field(default_factory=list)


# ==========================================================
# Validation Step
# ==========================================================

@dataclass
class ValidationStep:
    """
    One validation action for proving a regression.
    """

    priority: int

    commit: Commit

    description: str

    estimated_minutes: int = 45


# ==========================================================
# Bisect Plan
# ==========================================================

@dataclass
class BisectPlan:
    """
    Suggested validation plan.
    """

    good_sha: str

    bad_sha: str

    commands: List[str] = field(default_factory=list)

    steps: List[ValidationStep] = field(default_factory=list)


# ==========================================================
# Investigation Statistics
# ==========================================================

@dataclass
class RegressionStatistics:
    """
    Summary statistics for the investigation.
    """

    total_commits: int = 0

    filtered_commits: int = 0

    candidate_commits: int = 0

    module_count: int = 0

    execution_time: float = 0.0


# ==========================================================
# Regression Report
# ==========================================================

@dataclass
class RegressionReport:
    """
    Complete investigation output.
    """

    good_sha: str

    bad_sha: str

    failure: str

    commits: List[Commit] = field(default_factory=list)

    candidates: List[RegressionCandidate] = field(default_factory=list)

    modules: List[ModuleCandidate] = field(default_factory=list)

    bisect: Optional[BisectPlan] = None

    statistics: RegressionStatistics = field(
        default_factory=RegressionStatistics
    )

    generated_at: datetime = field(
        default_factory=datetime.now
    )
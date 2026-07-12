from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from bta.ai.parsers import ParsedSourceFile
from bta.ai.patching import SourceFileContext
from bta.ai.verification import ValidationCommand
from bta.domain import (
    DuplicateCandidate,
    EvidencePack,
    PatchDraft,
    PRDraft,
    RootCauseHypothesis,
    TriageCase,
    ValidationResult,
)


@dataclass(frozen=True, slots=True)
class AnalyzeIssueRequest:
    repo: str
    issue_number: int
    repo_path: Path | None = None
    source_files: Sequence[ParsedSourceFile] = ()
    persist: bool = True


@dataclass(frozen=True, slots=True)
class AnalyzeIssueResult:
    case: TriageCase
    evidence: EvidencePack
    hypotheses: list[RootCauseHypothesis]


@dataclass(frozen=True, slots=True)
class ScanRepositoryRequest:
    repo_path: Path
    persist: bool = False


@dataclass(frozen=True, slots=True)
class ScanRepositoryResult:
    source_files: list[ParsedSourceFile]
    source_contexts: list[SourceFileContext]


@dataclass(frozen=True, slots=True)
class DedupeRequest:
    case: TriageCase
    evidence: EvidencePack | None = None
    persist: bool = False


@dataclass(frozen=True, slots=True)
class DedupeResult:
    duplicates: list[DuplicateCandidate]


@dataclass(frozen=True, slots=True)
class FixRequest:
    case: TriageCase
    evidence: EvidencePack
    worktree_path: Path
    hypotheses: Sequence[RootCauseHypothesis] = ()
    hypothesis_id: UUID | None = None
    source_files: Sequence[SourceFileContext] = ()
    validation_commands: Sequence[ValidationCommand] = ()
    generation_attempt: int = 1
    persist: bool = True


@dataclass(frozen=True, slots=True)
class FixResult:
    patch: PatchDraft
    validation: ValidationResult


@dataclass(frozen=True, slots=True)
class PublishRequest:
    repo: str
    case_id: UUID
    repo_path: Path
    branch_name: str
    pr_draft: PRDraft
    validation: ValidationResult
    persist: bool = True


@dataclass(frozen=True, slots=True)
class PublishResult:
    pr_draft: PRDraft


@dataclass(frozen=True, slots=True)
class StatusResult:
    database_ok: bool
    github_ok: bool
    reasoning_provider_ok: bool
    patch_provider_ok: bool
    details: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvalRequest:
    benchmark_path: Path | None = None
    persist: bool = False


@dataclass(frozen=True, slots=True)
class EvalResult:
    message: str

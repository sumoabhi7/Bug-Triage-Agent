from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import Field, field_validator

from bta.domain.evidence_pack import DuplicateCandidate, EvidencePack, StackTrace
from bta.domain.hypothesis import RootCauseHypothesis
from bta.domain.patch_draft import PatchDraft
from bta.domain.pr_draft import PRDraft
from bta.domain.shared import (
    DomainModel,
    IssueMetadata,
    IssueType,
    Severity,
    StateTransition,
    WorkflowState,
)
from bta.domain.validation_result import ValidationResult


class TriageCase(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    repo: str = Field(min_length=1)
    issue_number: int = Field(ge=1)
    state: WorkflowState = WorkflowState.INGESTED
    state_history: list[StateTransition] = Field(default_factory=list)
    retry_count: int = Field(default=0, ge=0)
    issue_metadata: IssueMetadata
    issue_type: IssueType | None = None
    severity: Severity | None = None
    raw_logs: list[str] = Field(default_factory=list)
    stack_traces: list[StackTrace] = Field(default_factory=list)
    error_messages: list[str] = Field(default_factory=list)
    evidence: EvidencePack | None = None
    candidate_duplicates: list[DuplicateCandidate] = Field(default_factory=list)
    hypotheses: list[RootCauseHypothesis] = Field(default_factory=list)
    patch_drafts: list[PatchDraft] = Field(default_factory=list)
    validation_result: ValidationResult | None = None
    pr_draft: PRDraft | None = None

    @field_validator("repo")
    @classmethod
    def _repo_must_be_owner_name(cls, value: str) -> str:
        owner_repo = value.split("/")
        if len(owner_repo) != 2 or not all(part.strip() for part in owner_repo):
            raise ValueError('repo must use "owner/repo" format')
        return value

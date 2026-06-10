from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from bta.domain.shared import DomainModel, ensure_utc, utc_now


class StackFrame(DomainModel):
    file: str | None = None
    line_number: int | None = Field(default=None, ge=1)
    function_name: str | None = None
    local_vars: dict[str, str] = Field(default_factory=dict)


class StackTrace(DomainModel):
    raw_text: str
    language: str | None = None
    exception_type: str | None = None
    message: str | None = None
    frames: list[StackFrame] = Field(default_factory=list)


class FileReference(DomainModel):
    repo_path: str = Field(min_length=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content: str

    @model_validator(mode="after")
    def _line_range_must_be_ordered(self) -> FileReference:
        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        return self


class CodeSnippet(DomainModel):
    repo_path: str = Field(min_length=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    symbol_name: str | None = None
    symbol_type: str | None = None
    content: str
    score: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def _line_range_must_be_ordered(self) -> CodeSnippet:
        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        return self


class DuplicateCandidate(DomainModel):
    repo: str = Field(min_length=1)
    issue_number: int = Field(ge=1)
    triage_case_id: UUID | None = None
    github_issue_id: int | None = Field(default=None, ge=1)
    similarity_score: float = Field(ge=0, le=1)
    summary: str = ""


class RelatedIssue(DomainModel):
    repo: str = Field(min_length=1)
    issue_number: int = Field(ge=1)
    title: str = Field(min_length=1)
    summary: str = ""
    similarity_score: float = Field(ge=0, le=1)
    state: str = Field(min_length=1)


class EvidencePack(DomainModel):
    relevant_excerpts: list[str] = Field(default_factory=list)
    stack_trace_frames: list[StackFrame] = Field(default_factory=list)
    error_signatures: list[str] = Field(default_factory=list)
    file_references: list[FileReference] = Field(default_factory=list)
    similar_code_snippets: list[CodeSnippet] = Field(default_factory=list)
    duplicate_candidates: list[DuplicateCandidate] = Field(default_factory=list)
    related_issues: list[RelatedIssue] = Field(default_factory=list)
    retrieval_timestamp: datetime = Field(default_factory=utc_now)
    embedding_model: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)

    @field_validator("retrieval_timestamp")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return ensure_utc(value)
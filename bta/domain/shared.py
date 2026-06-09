from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)
from pydantic import (
    JsonValue as PydanticJsonValue,
)

type JsonValue = PydanticJsonValue


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC)


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class WorkflowState(StrEnum):
    INGESTED = "INGESTED"
    NORMALIZED = "NORMALIZED"
    EXTRACTED = "EXTRACTED"
    RETRIEVED = "RETRIEVED"
    REASONED = "REASONED"
    PATCH_DRAFTING = "PATCH_DRAFTING"
    PATCH_VALIDATING = "PATCH_VALIDATING"
    PUBLISHED = "PUBLISHED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


class IssueType(StrEnum):
    BUG = "bug"
    FEATURE = "feature"
    QUESTION = "question"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PRStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    REJECTED = "rejected"


class StateTransition(DomainModel):
    from_state: WorkflowState | None = None
    to_state: WorkflowState
    timestamp: datetime = Field(default_factory=utc_now)
    reason: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class IssueMetadata(DomainModel):
    github_issue_id: int | None = Field(default=None, ge=1)
    title: str = Field(min_length=1)
    body: str = ""
    labels: list[str] = Field(default_factory=list)
    author: str = Field(min_length=1)
    url: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("created_at", "updated_at")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return ensure_utc(value)


class TraceEntry(DomainModel):
    timestamp: datetime = Field(default_factory=utc_now)
    stage: str = Field(min_length=1)
    event: str = Field(min_length=1)
    message: str = ""
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    duration_ms: float | None = Field(default=None, ge=0)
    error: str | None = None

    @field_validator("timestamp")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return ensure_utc(value)

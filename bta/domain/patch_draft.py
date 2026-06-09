from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import Field

from bta.domain.shared import DomainModel


class PatchDraft(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    hypothesis_id: UUID
    diff_content: str = Field(min_length=1)
    files_modified: list[str] = Field(default_factory=list)
    branch_name: str = Field(min_length=1)
    commit_message: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    generation_attempt: int = Field(default=1, ge=1)
    model_used: str = Field(min_length=1)

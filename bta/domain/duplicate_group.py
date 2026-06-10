from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import Field, model_validator

from bta.domain.shared import DomainModel


class DuplicateGroup(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    primary_case_id: UUID
    member_case_ids: list[UUID] = Field(default_factory=list)
    similarity_scores: dict[str, float] = Field(default_factory=dict)
    cluster_summary: str = ""
    threshold_used: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _primary_case_must_be_a_member(self) -> DuplicateGroup:
        if self.primary_case_id not in self.member_case_ids:
            raise ValueError("primary_case_id must be included in member_case_ids")
        return self
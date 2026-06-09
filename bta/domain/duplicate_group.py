from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import Field, model_validator

from bta.domain.shared import DomainModel


class DuplicateGroup(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    primary_issue_number: int = Field(ge=1)
    member_issue_numbers: list[int] = Field(default_factory=list)
    similarity_scores: dict[int, float] = Field(default_factory=dict)
    cluster_summary: str = ""
    threshold_used: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _primary_issue_must_be_a_member(self) -> DuplicateGroup:
        if self.primary_issue_number not in self.member_issue_numbers:
            raise ValueError("primary_issue_number must be included in member_issue_numbers")
        return self

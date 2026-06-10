from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import Field, field_validator

from bta.domain.shared import DomainModel


class RootCauseHypothesis(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    rank: int = Field(ge=1)
    hypothesis: str = Field(min_length=1)
    category: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    evidence_references: list[str] = Field(default_factory=list)
    affected_files: list[str] = Field(default_factory=list)
    affected_lines: list[tuple[str, int, int]] = Field(default_factory=list)
    model_used: str = Field(min_length=1)

    @field_validator("affected_lines")
    @classmethod
    def _affected_lines_must_be_ordered(
        cls, value: list[tuple[str, int, int]]
    ) -> list[tuple[str, int, int]]:
        for repo_path, start_line, end_line in value:
            if not repo_path:
                raise ValueError("affected line repo path cannot be empty")
            if start_line < 1 or end_line < 1:
                raise ValueError("affected line numbers must be positive")
            if end_line < start_line:
                raise ValueError("affected line end must be greater than or equal to start")
        return value
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from bta.domain.shared import DomainModel


class ValidationResult(DomainModel):
    patch_draft_id: UUID
    tests_passed: bool | None = None
    tests_output: str | None = None
    build_passed: bool | None = None
    build_output: str | None = None
    lint_passed: bool | None = None
    lint_output: str | None = None
    overall_passed: bool = False
    confidence_delta: float = 0.0
    worktree_path: str = Field(min_length=1)

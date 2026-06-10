from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import Field

from bta.domain.shared import DomainModel, PRStatus


def default_pr_labels() -> list[str]:
    return ["bta-generated", "needs-review"]


class PRDraft(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    patch_draft_id: UUID
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    base_branch: str = Field(min_length=1)
    head_branch: str = Field(min_length=1)
    labels: list[str] = Field(default_factory=default_pr_labels)
    github_pr_number: int | None = Field(default=None, ge=1)
    pr_url: str | None = None
    status: PRStatus = PRStatus.PENDING
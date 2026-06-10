from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import Field

from bta.domain.shared import DomainModel, StateTransition, TraceEntry, WorkflowState


class AnalysisRun(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    triage_case_id: UUID
    model_used: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    confidence_threshold: float = Field(default=0.75, ge=0, le=1)
    duration_seconds: float = Field(default=0.0, ge=0)
    state_transitions: list[StateTransition] = Field(default_factory=list)
    workflow_trace: list[TraceEntry] = Field(default_factory=list)
    final_state: WorkflowState
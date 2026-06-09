from uuid import uuid4

from bta.domain import AnalysisRun, PRDraft, PRStatus, StateTransition, TraceEntry, WorkflowState


def test_analysis_run_stores_state_transitions_and_trace_entries() -> None:
    case_id = uuid4()
    transition = StateTransition(
        from_state=WorkflowState.REASONED,
        to_state=WorkflowState.PATCH_DRAFTING,
        reason="confidence threshold met",
    )
    trace = TraceEntry(
        stage="reasoning",
        event="hypothesis_selected",
        message="Selected top-ranked hypothesis.",
        metadata={"rank": 1, "confidence": 0.82},
        duration_ms=12.5,
    )

    run = AnalysisRun(
        triage_case_id=case_id,
        model_used="qwen2.5-coder:7b",
        embedding_model="all-MiniLM-L6-v2",
        state_transitions=[transition],
        workflow_trace=[trace],
        final_state=WorkflowState.PATCH_DRAFTING,
    )

    assert run.triage_case_id == case_id
    assert run.confidence_threshold == 0.75
    assert run.state_transitions[0].to_state is WorkflowState.PATCH_DRAFTING
    assert run.workflow_trace[0].metadata["confidence"] == 0.82


def test_pr_draft_defaults_to_pending_review_metadata() -> None:
    patch_id = uuid4()

    draft = PRDraft(
        patch_draft_id=patch_id,
        title="fix(config): handle missing key [closes #42]",
        body="Root cause, fix, and validation summary.",
        base_branch="main",
        head_branch="bta/fix-issue-42-attempt-1",
    )
    other_draft = PRDraft(
        patch_draft_id=patch_id,
        title="fix(config): handle another key",
        body="Root cause, fix, and validation summary.",
        base_branch="main",
        head_branch="bta/fix-issue-43-attempt-1",
    )

    assert draft.status is PRStatus.PENDING
    assert draft.labels == ["bta-generated", "needs-review"]

    draft.labels.append("extra")
    assert other_draft.labels == ["bta-generated", "needs-review"]

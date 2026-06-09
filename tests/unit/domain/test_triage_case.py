from datetime import UTC

import pytest
from pydantic import ValidationError

from bta.domain import IssueMetadata, StateTransition, TriageCase, WorkflowState


def test_triage_case_defaults_are_workflow_safe() -> None:
    issue_metadata = IssueMetadata(title="Crash on startup", author="octocat")

    case = TriageCase(repo="owner/repo", issue_number=42, issue_metadata=issue_metadata)
    other_case = TriageCase(repo="owner/repo", issue_number=43, issue_metadata=issue_metadata)

    assert case.state is WorkflowState.INGESTED
    assert case.retry_count == 0
    assert case.raw_logs == []
    assert case.hypotheses == []
    assert case.patch_drafts == []
    assert case.issue_metadata.created_at.tzinfo is UTC

    case.raw_logs.append("Traceback")
    assert other_case.raw_logs == []


def test_triage_case_keeps_state_history() -> None:
    transition = StateTransition(
        from_state=WorkflowState.INGESTED,
        to_state=WorkflowState.NORMALIZED,
        reason="issue metadata parsed",
        metadata={"label_count": 2},
    )

    case = TriageCase(
        repo="owner/repo",
        issue_number=42,
        issue_metadata=IssueMetadata(title="Crash", author="octocat"),
        state=WorkflowState.NORMALIZED,
        state_history=[transition],
    )

    assert case.state_history[0].from_state is WorkflowState.INGESTED
    assert case.state_history[0].to_state is WorkflowState.NORMALIZED
    assert case.state_history[0].metadata == {"label_count": 2}


def test_triage_case_rejects_invalid_repo_and_retry_count() -> None:
    issue_metadata = IssueMetadata(title="Crash", author="octocat")

    with pytest.raises(ValidationError):
        TriageCase(repo="repo-only", issue_number=42, issue_metadata=issue_metadata)

    with pytest.raises(ValidationError):
        TriageCase(
            repo="owner/repo",
            issue_number=42,
            retry_count=-1,
            issue_metadata=issue_metadata,
        )


def test_triage_case_raw_logs_preserve_exact_whitespace() -> None:
    raw_log = "  ERROR config failed\n    nested detail  \n"

    case = TriageCase(
        repo="owner/repo",
        issue_number=42,
        issue_metadata=IssueMetadata(title="Crash", author="octocat"),
        raw_logs=[raw_log],
    )

    assert case.raw_logs == [raw_log]

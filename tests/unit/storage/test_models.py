from typing import cast
from uuid import uuid4

from sqlalchemy import Table

from bta.domain import (
    AnalysisRun,
    DuplicateGroup,
    EvidencePack,
    IssueMetadata,
    PatchDraft,
    PRDraft,
    RootCauseHypothesis,
    TriageCase,
    ValidationResult,
    WorkflowState,
)
from bta.storage.models import (
    AnalysisRunRecord,
    ArtifactRecord,
    Base,
    DuplicateGroupRecord,
    EvidencePackRecord,
    PatchDraftRecord,
    PullRequestRecord,
    RootCauseHypothesisRecord,
    TriageCaseRecord,
    ValidationResultRecord,
    content_hash,
    validate_case_provenance,
)


def test_domain_records_round_trip_without_changing_domain_models() -> None:
    case = TriageCase(
        repo="owner/repo",
        issue_number=42,
        issue_metadata=IssueMetadata(github_issue_id=100, title="Crash", author="octocat"),
    )
    evidence = EvidencePack(embedding_model="all-MiniLM-L6-v2", confidence=0.8)
    hypothesis = RootCauseHypothesis(
        rank=1,
        hypothesis="Missing guard",
        category="null-ref",
        confidence=0.9,
        model_used="qwen2.5-coder:7b",
    )
    patch = PatchDraft(
        hypothesis_id=hypothesis.id,
        diff_content="--- a/a.py\n+++ b/a.py\n",
        branch_name="bta/fix",
        commit_message="fix: guard value",
        explanation="Adds a guard.",
        model_used="qwen2.5-coder:7b",
    )
    validation = ValidationResult(patch_draft_id=patch.id, worktree_path="/tmp/old-worktree")
    pr = PRDraft(
        patch_draft_id=patch.id,
        title="fix: guard value",
        body="Details",
        base_branch="main",
        head_branch="bta/fix",
    )

    case_record = TriageCaseRecord.from_domain(case)
    evidence_record = EvidencePackRecord.from_domain(case.id, evidence)
    hypothesis_record = RootCauseHypothesisRecord.from_domain(case.id, uuid4(), hypothesis)
    patch_record = PatchDraftRecord.from_domain(case.id, patch)
    validation_record = ValidationResultRecord.from_domain(validation)
    pr_record = PullRequestRecord.from_domain(case.id, pr)

    assert case_record.issue_metadata["github_issue_id"] == 100
    assert evidence_record.to_domain() == evidence
    assert hypothesis_record.to_domain() == hypothesis
    assert patch_record.to_domain() == patch
    assert validation_record.to_domain() == validation
    assert pr_record.to_domain() == pr


def test_analysis_and_duplicate_group_records_round_trip() -> None:
    case_id = uuid4()
    run = AnalysisRun(
        triage_case_id=case_id,
        model_used="qwen2.5-coder:7b",
        embedding_model="all-MiniLM-L6-v2",
        final_state=WorkflowState.NEEDS_REVIEW,
    )
    group = DuplicateGroup(
        primary_case_id=case_id,
        member_case_ids=[case_id],
        similarity_scores={str(case_id): 1.0},
        threshold_used=0.85,
    )

    assert AnalysisRunRecord.from_domain(run).to_domain() == run
    assert DuplicateGroupRecord.from_domain(group).to_domain() == group


def test_storage_metadata_contains_required_tables_and_constraints() -> None:
    assert set(Base.metadata.tables) == {
        "analysis_runs",
        "artifacts",
        "duplicate_groups",
        "evidence_packs",
        "issue_embeddings",
        "patch_drafts",
        "pull_requests",
        "root_cause_hypotheses",
        "triage_cases",
        "validation_results",
    }

    artifact_table = cast(Table, ArtifactRecord.__table__)

    assert artifact_table.c.relative_path.unique is None

    assert "uq_artifacts_relative_path" in {
        constraint.name for constraint in artifact_table.constraints
    }


def test_content_hash_is_stable_for_equivalent_json() -> None:
    assert content_hash({"b": 2, "a": 1}) == content_hash({"a": 1, "b": 2})


def test_case_provenance_rejects_patch_for_unknown_hypothesis() -> None:
    case = TriageCase(
        repo="owner/repo",
        issue_number=42,
        issue_metadata=IssueMetadata(title="Crash", author="octocat"),
        patch_drafts=[
            PatchDraft(
                hypothesis_id=uuid4(),
                diff_content="diff",
                branch_name="bta/fix",
                commit_message="fix: crash",
                explanation="Fixes crash.",
                model_used="model",
            )
        ],
    )

    import pytest

    with pytest.raises(ValueError, match="hypothesis outside"):
        validate_case_provenance(case)


def test_case_record_applies_updated_canonical_projection() -> None:
    case = TriageCase(
        repo="owner/repo",
        issue_number=42,
        issue_metadata=IssueMetadata(title="Crash", author="octocat"),
    )
    record = TriageCaseRecord.from_domain(case)
    case.state = WorkflowState.NORMALIZED
    case.raw_logs = ["exact log\n"]

    assert record.apply_domain(case) is record
    assert record.state == "NORMALIZED"
    assert record.parsed_context["raw_logs"] == ["exact log\n"]

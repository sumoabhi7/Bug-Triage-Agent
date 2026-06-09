from bta.domain import (
    DuplicateCandidate,
    EvidencePack,
    IssueMetadata,
    IssueType,
    PatchDraft,
    PRDraft,
    RootCauseHypothesis,
    Severity,
    StackFrame,
    StackTrace,
    TriageCase,
    ValidationResult,
    WorkflowState,
)


def test_full_triage_case_roundtrip_preserves_nested_workflow_state() -> None:
    issue_metadata = IssueMetadata(
        github_issue_id=1001,
        title="Crash when config key is missing",
        body="Traceback ... KeyError: 'token'",
        labels=["bug"],
        author="octocat",
        url="https://github.com/owner/repo/issues/42",
    )
    frame = StackFrame(file="app.py", line_number=12, function_name="load_config")
    stack_trace = StackTrace(
        raw_text="Traceback ... KeyError: 'token'",
        language="python",
        exception_type="KeyError",
        message="'token'",
        frames=[frame],
    )
    duplicate = DuplicateCandidate(
        repo="owner/repo",
        issue_number=7,
        similarity_score=0.88,
        summary="same missing config key",
    )
    evidence = EvidencePack(
        relevant_excerpts=["KeyError when token is missing."],
        stack_trace_frames=[frame],
        error_signatures=["KeyError"],
        duplicate_candidates=[duplicate],
        embedding_model="all-MiniLM-L6-v2",
        confidence=0.83,
    )
    hypothesis = RootCauseHypothesis(
        rank=1,
        hypothesis="Missing config fallback raises KeyError.",
        category="config-error",
        confidence=0.86,
        evidence_references=["trace:0"],
        affected_files=["app.py"],
        affected_lines=[("app.py", 10, 14)],
        model_used="qwen2.5-coder:7b",
    )
    patch = PatchDraft(
        hypothesis_id=hypothesis.id,
        diff_content="--- a/app.py\n+++ b/app.py\n@@\n-cfg['token']\n+cfg.get('token')\n",
        files_modified=["app.py"],
        branch_name="bta/fix-issue-42-attempt-1",
        commit_message="fix: handle missing token config",
        explanation="Uses a safe lookup for the optional token.",
        model_used="qwen2.5-coder:7b",
    )
    validation = ValidationResult(
        patch_draft_id=patch.id,
        tests_passed=True,
        tests_output="1 passed",
        build_passed=None,
        lint_passed=True,
        overall_passed=True,
        worktree_path="/tmp/bta-worktree",
    )
    pr_draft = PRDraft(
        patch_draft_id=patch.id,
        title="fix(config): handle missing token [closes #42]",
        body="Root cause, fix, and validation summary.",
        base_branch="main",
        head_branch=patch.branch_name,
    )

    case = TriageCase(
        repo="owner/repo",
        issue_number=42,
        state=WorkflowState.PATCH_VALIDATING,
        retry_count=1,
        issue_metadata=issue_metadata,
        issue_type=IssueType.BUG,
        severity=Severity.HIGH,
        raw_logs=["Traceback ..."],
        stack_traces=[stack_trace],
        error_messages=["KeyError: 'token'"],
        evidence=evidence,
        candidate_duplicates=[duplicate],
        hypotheses=[hypothesis],
        patch_drafts=[patch],
        validation_result=validation,
        pr_draft=pr_draft,
    )

    restored = TriageCase.model_validate(case.model_dump(mode="json"))

    assert restored == case
    assert restored.evidence is not None
    assert restored.evidence.embedding_model == "all-MiniLM-L6-v2"
    assert restored.hypotheses[0].id == hypothesis.id
    assert restored.patch_drafts[0].hypothesis_id == hypothesis.id
    assert restored.validation_result is not None
    assert restored.validation_result.patch_draft_id == patch.id
    assert restored.pr_draft is not None
    assert restored.pr_draft.patch_draft_id == patch.id

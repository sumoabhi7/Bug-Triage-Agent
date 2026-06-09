from uuid import uuid4

from bta.domain import PatchDraft, ValidationResult


def test_patch_draft_captures_generated_diff_metadata() -> None:
    hypothesis_id = uuid4()

    patch = PatchDraft(
        hypothesis_id=hypothesis_id,
        diff_content="--- a/app.py\n+++ b/app.py\n@@\n-pass\n+return None\n",
        files_modified=["app.py"],
        branch_name="bta/fix-issue-42-attempt-1",
        commit_message="fix: handle missing config key",
        explanation="Adds a safe fallback for missing config keys.",
        model_used="qwen2.5-coder:7b",
    )

    assert patch.hypothesis_id == hypothesis_id
    assert patch.generation_attempt == 1
    assert patch.files_modified == ["app.py"]


def test_validation_result_captures_present_and_missing_checks() -> None:
    patch_id = uuid4()

    result = ValidationResult(
        patch_draft_id=patch_id,
        tests_passed=True,
        tests_output="1 passed",
        build_passed=None,
        lint_passed=True,
        lint_output="All checks passed",
        overall_passed=True,
        confidence_delta=0.05,
        worktree_path="/tmp/bta-worktree",
    )

    assert result.patch_draft_id == patch_id
    assert result.tests_passed is True
    assert result.build_passed is None
    assert result.overall_passed is True


def test_patch_diff_and_validation_output_preserve_exact_whitespace() -> None:
    diff_content = "  --- a/app.py\n+++ b/app.py\n@@\n- value\n+ value  \n"
    tests_output = "  failed stdout\n    indented line\n"
    lint_output = "\n  W293 blank line contains whitespace\n"
    patch = PatchDraft(
        hypothesis_id=uuid4(),
        diff_content=diff_content,
        files_modified=["app.py"],
        branch_name="bta/fix-issue-42-attempt-1",
        commit_message="fix: preserve whitespace test",
        explanation="Checks that generated diffs are not stripped.",
        model_used="qwen2.5-coder:7b",
    )
    result = ValidationResult(
        patch_draft_id=patch.id,
        tests_passed=False,
        tests_output=tests_output,
        lint_passed=False,
        lint_output=lint_output,
        overall_passed=False,
        worktree_path="/tmp/bta-worktree",
    )

    assert patch.diff_content == diff_content
    assert result.tests_output == tests_output
    assert result.lint_output == lint_output

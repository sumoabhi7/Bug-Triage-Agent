from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

from bta.ai.verification import (
    CommandResult,
    PatchValidationReport,
    ValidationCommand,
    VerificationConfig,
    VerificationEngine,
    VerificationError,
    VerificationInput,
    apply_patch,
    run_validation_command,
    validation_result_from_report,
)
from bta.domain import PatchDraft

VALID_DIFF = "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-print('bad')\n+print('good')\n"


def make_patch(diff: str = VALID_DIFF) -> PatchDraft:
    return PatchDraft(
        hypothesis_id=uuid4(),
        diff_content=diff,
        files_modified=["app.py"],
        branch_name="bta/fix/issue-42-config-error-attempt-1",
        commit_message="fix: handle config token",
        explanation="Updates the failing code path.",
        model_used="fake-patcher",
    )


def make_worktree(tmp_path: Path) -> Path:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / "app.py").write_text("print('bad')\n", encoding="utf-8")
    return worktree


@pytest.mark.asyncio
async def test_verification_applies_patch_and_runs_configurable_commands(tmp_path: Path) -> None:
    worktree = make_worktree(tmp_path)
    patch = make_patch()
    original_patch = patch.model_dump(mode="json")
    command = ValidationCommand(
        name="tests",
        argv=(
            sys.executable,
            "-c",
            "import pathlib; print(pathlib.Path('app.py').read_text(), end='')",
        ),
    )
    engine = VerificationEngine(VerificationConfig(commands=(command,)))

    result = await engine.validate(VerificationInput(patch=patch, worktree_path=worktree))

    assert (worktree / "app.py").read_text(encoding="utf-8") == "print('good')\n"
    assert result.patch_draft_id == patch.id
    assert result.tests_passed is True
    assert result.overall_passed is True
    assert result.confidence_delta == 0.05
    assert "exit_code: 0" in (result.tests_output or "")
    assert "print('good')" in (result.tests_output or "")
    assert patch.model_dump(mode="json") == original_patch


@pytest.mark.asyncio
async def test_verification_returns_failed_result_when_patch_apply_fails(tmp_path: Path) -> None:
    worktree = make_worktree(tmp_path)
    patch = make_patch("--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-missing\n+value\n")
    command = ValidationCommand(name="tests", argv=(sys.executable, "-c", "print('skip')"))
    engine = VerificationEngine(VerificationConfig(commands=(command,)))

    result = await engine.validate(VerificationInput(patch=patch, worktree_path=worktree))

    assert (worktree / "app.py").read_text(encoding="utf-8") == "print('bad')\n"
    assert result.overall_passed is False
    assert result.tests_passed is None
    assert result.confidence_delta == -0.10
    assert "patch-apply-check" in (result.tests_output or "")
    assert "exit_code:" in (result.tests_output or "")


@pytest.mark.asyncio
async def test_run_validation_command_preserves_stdout_stderr_and_exit_code(tmp_path: Path) -> None:
    worktree = make_worktree(tmp_path)
    command = ValidationCommand(
        name="lint",
        argv=(
            sys.executable,
            "-c",
            "import sys; print('  out  '); print('  err  ', file=sys.stderr); raise SystemExit(3)",
        ),
    )

    result = await run_validation_command(worktree, command)

    assert result.name == "lint"
    assert result.exit_code == 3
    assert result.stdout == "  out  \n"
    assert result.stderr == "  err  \n"
    assert result.timed_out is False
    assert result.passed is False


@pytest.mark.asyncio
async def test_validation_timeout_is_captured_as_command_result(tmp_path: Path) -> None:
    worktree = make_worktree(tmp_path)
    patch = make_patch()
    command = ValidationCommand(
        name="tests",
        argv=(sys.executable, "-c", "import time; time.sleep(1)"),
        timeout_seconds=0.05,
    )
    engine = VerificationEngine(VerificationConfig(commands=(command,)))

    result = await engine.validate(VerificationInput(patch=patch, worktree_path=worktree))

    assert result.tests_passed is False
    assert result.overall_passed is False
    assert "exit_code: timeout" in (result.tests_output or "")


@pytest.mark.asyncio
async def test_apply_patch_helper_applies_diff_inside_worktree(tmp_path: Path) -> None:
    worktree = make_worktree(tmp_path)
    patch = make_patch()

    result = await apply_patch(worktree, patch, timeout_seconds=5)

    assert result.passed is True
    assert (worktree / "app.py").read_text(encoding="utf-8") == "print('good')\n"


def test_validation_report_preserves_command_metadata(tmp_path: Path) -> None:
    patch = make_patch()
    apply_check = CommandResult(
        name="patch-apply-check",
        argv=("git", "apply", "--check", "-"),
        exit_code=0,
        stdout="",
        stderr="",
        timed_out=False,
        duration_seconds=0.01,
    )
    apply_result = CommandResult(
        name="patch-apply",
        argv=("git", "apply", "-"),
        exit_code=0,
        stdout="",
        stderr="",
        timed_out=False,
        duration_seconds=0.01,
    )
    unknown_result = CommandResult(
        name="custom",
        argv=("tool", "--flag"),
        exit_code=7,
        stdout="custom stdout\n",
        stderr="custom stderr\n",
        timed_out=False,
        duration_seconds=0.01,
    )
    report = PatchValidationReport(
        patch=patch,
        worktree_path=tmp_path,
        apply_check_result=apply_check,
        apply_result=apply_result,
        command_results=(unknown_result,),
    )

    result = validation_result_from_report(report)

    assert report.command_results[0].argv == ("tool", "--flag")
    assert result.overall_passed is False
    assert result.build_output is None
    assert result.tests_output is not None
    assert "name: custom" in result.tests_output
    assert "$ tool --flag" in result.tests_output
    assert "stdout:\ncustom stdout\n\nstderr:\ncustom stderr\n" in result.tests_output


def test_command_result_format_separates_stdout_and_stderr(tmp_path: Path) -> None:
    patch = make_patch()
    apply_check = CommandResult(
        name="patch-apply-check",
        argv=("git", "apply", "--check", "-"),
        exit_code=0,
        stdout="",
        stderr="",
        timed_out=False,
        duration_seconds=0.01,
    )
    apply_result = CommandResult(
        name="patch-apply",
        argv=("git", "apply", "-"),
        exit_code=0,
        stdout="",
        stderr="",
        timed_out=False,
        duration_seconds=0.01,
    )
    tests_result = CommandResult(
        name="tests",
        argv=("pytest",),
        exit_code=1,
        stdout="  stdout with spaces  \n",
        stderr="  stderr with spaces  \n",
        timed_out=False,
        duration_seconds=0.01,
    )
    report = PatchValidationReport(
        patch=patch,
        worktree_path=tmp_path,
        apply_check_result=apply_check,
        apply_result=apply_result,
        command_results=(tests_result,),
    )

    result = validation_result_from_report(report)

    assert result.tests_output is not None
    assert "stdout:\n  stdout with spaces  \n\nstderr:\n  stderr with spaces  \n" in (
        result.tests_output
    )


@pytest.mark.asyncio
async def test_verification_rejects_missing_worktree(tmp_path: Path) -> None:
    engine = VerificationEngine()

    with pytest.raises(VerificationError):
        await engine.validate(
            VerificationInput(patch=make_patch(), worktree_path=tmp_path / "missing")
        )

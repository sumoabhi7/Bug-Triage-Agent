from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from bta.domain import PatchDraft, ValidationResult

CANONICAL_COMMAND_NAMES = frozenset(("tests", "build", "lint", "typecheck"))


class VerificationError(Exception):
    """Raised when patch verification cannot be executed."""


@dataclass(frozen=True, slots=True)
class ValidationCommand:
    name: str
    argv: tuple[str, ...]
    timeout_seconds: float = 300.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must not be blank")
        if not self.argv:
            raise ValueError("argv must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True, slots=True)
class CommandResult:
    name: str
    argv: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


@dataclass(frozen=True, slots=True)
class PatchValidationReport:
    patch: PatchDraft
    worktree_path: Path
    apply_check_result: CommandResult
    apply_result: CommandResult | None
    command_results: tuple[CommandResult, ...]

    @property
    def patch_applied(self) -> bool:
        return (
            self.apply_check_result.passed
            and self.apply_result is not None
            and self.apply_result.passed
        )

    @property
    def overall_passed(self) -> bool:
        return self.patch_applied and all(result.passed for result in self.command_results)


@dataclass(frozen=True, slots=True)
class VerificationConfig:
    apply_timeout_seconds: float = 60.0
    commands: tuple[ValidationCommand, ...] = ()

    def __post_init__(self) -> None:
        if self.apply_timeout_seconds <= 0:
            raise ValueError("apply_timeout_seconds must be positive")


@dataclass(frozen=True, slots=True)
class VerificationInput:
    patch: PatchDraft
    worktree_path: Path
    commands: Sequence[ValidationCommand] | None = None


class VerificationEngine:
    """Apply patches and run validation commands inside an isolated worktree."""

    def __init__(self, config: VerificationConfig | None = None) -> None:
        self._config = config or VerificationConfig()

    async def validate(self, input: VerificationInput) -> ValidationResult:
        worktree_path = input.worktree_path
        if not worktree_path.exists() or not worktree_path.is_dir():
            raise VerificationError(f"worktree path does not exist: {worktree_path}")

        commands = tuple(input.commands) if input.commands is not None else self._config.commands
        apply_check_result = await check_patch_application(
            worktree_path,
            input.patch,
            timeout_seconds=self._config.apply_timeout_seconds,
        )
        apply_result: CommandResult | None = None
        command_results: tuple[CommandResult, ...] = ()
        if apply_check_result.passed:
            apply_result = await apply_patch(
                worktree_path,
                input.patch,
                timeout_seconds=self._config.apply_timeout_seconds,
            )
            if apply_result.passed:
                command_results = tuple(
                    [await run_validation_command(worktree_path, command) for command in commands]
                )

        report = PatchValidationReport(
            patch=input.patch,
            worktree_path=worktree_path,
            apply_check_result=apply_check_result,
            apply_result=apply_result,
            command_results=command_results,
        )
        return validation_result_from_report(report)


async def check_patch_application(
    worktree_path: Path,
    patch: PatchDraft,
    *,
    timeout_seconds: float,
) -> CommandResult:
    return await _run_command(
        worktree_path,
        name="patch-apply-check",
        argv=("git", "apply", "--check", "-"),
        timeout_seconds=timeout_seconds,
        stdin=patch.diff_content,
    )


async def apply_patch(
    worktree_path: Path,
    patch: PatchDraft,
    *,
    timeout_seconds: float,
) -> CommandResult:
    return await _run_command(
        worktree_path,
        name="patch-apply",
        argv=("git", "apply", "-"),
        timeout_seconds=timeout_seconds,
        stdin=patch.diff_content,
    )


async def run_validation_command(
    worktree_path: Path,
    command: ValidationCommand,
) -> CommandResult:
    return await _run_command(
        worktree_path,
        name=command.name,
        argv=command.argv,
        timeout_seconds=command.timeout_seconds,
        stdin=None,
    )


def validation_result_from_report(report: PatchValidationReport) -> ValidationResult:
    tests_result = _first_result(report.command_results, "tests")
    build_results = tuple(
        result for result in report.command_results if result.name in {"build", "typecheck"}
    )
    lint_result = _first_result(report.command_results, "lint")
    infrastructure_output = _format_infrastructure_output(report)
    unknown_output = _format_unknown_command_output(report.command_results)
    tests_output = _combined_output(tests_result)
    build_output = _combined_outputs(build_results)
    lint_output = _combined_output(lint_result)

    if infrastructure_output and tests_output is None:
        tests_output = infrastructure_output
    elif infrastructure_output and tests_output is not None:
        tests_output = f"{infrastructure_output}\n{tests_output}"
    if unknown_output and tests_output is None:
        tests_output = unknown_output
    elif unknown_output and tests_output is not None:
        tests_output = f"{tests_output}\n{unknown_output}"

    return ValidationResult(
        patch_draft_id=report.patch.id,
        tests_passed=_passed_or_none(tests_result),
        tests_output=tests_output,
        build_passed=_passed_or_none(build_results[-1] if build_results else None),
        build_output=build_output,
        lint_passed=_passed_or_none(lint_result),
        lint_output=lint_output,
        overall_passed=report.overall_passed,
        confidence_delta=0.05 if report.overall_passed else -0.10,
        worktree_path=str(report.worktree_path),
    )


async def _run_command(
    worktree_path: Path,
    *,
    name: str,
    argv: tuple[str, ...],
    timeout_seconds: float,
    stdin: str | None,
) -> CommandResult:
    start = time.monotonic()
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=worktree_path,
            stdin=asyncio.subprocess.PIPE if stdin is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        raise VerificationError(f"failed to start validation command: {name}") from exc

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(stdin.encode() if stdin is not None else None),
            timeout=timeout_seconds,
        )
        timed_out = False
        exit_code = process.returncode
    except TimeoutError:
        process.kill()
        stdout_bytes, stderr_bytes = await process.communicate()
        timed_out = True
        exit_code = None

    return CommandResult(
        name=name,
        argv=argv,
        exit_code=exit_code,
        stdout=stdout_bytes.decode(errors="replace"),
        stderr=stderr_bytes.decode(errors="replace"),
        timed_out=timed_out,
        duration_seconds=time.monotonic() - start,
    )


def _first_result(results: Sequence[CommandResult], name: str) -> CommandResult | None:
    for result in results:
        if result.name == name:
            return result
    return None


def _passed_or_none(result: CommandResult | None) -> bool | None:
    if result is None:
        return None
    return result.passed


def _combined_output(result: CommandResult | None) -> str | None:
    if result is None:
        return None
    return _format_command_result(result)


def _combined_outputs(results: Sequence[CommandResult]) -> str | None:
    if not results:
        return None
    return "\n".join(_format_command_result(result) for result in results)


def _format_infrastructure_output(report: PatchValidationReport) -> str | None:
    results = [report.apply_check_result]
    if report.apply_result is not None:
        results.append(report.apply_result)
    if report.patch_applied:
        return None
    return "\n".join(_format_command_result(result) for result in results)


def _format_unknown_command_output(results: Sequence[CommandResult]) -> str | None:
    unknown_results = [result for result in results if result.name not in CANONICAL_COMMAND_NAMES]
    if not unknown_results:
        return None
    return "\n".join(_format_command_result(result) for result in unknown_results)


def _format_command_result(result: CommandResult) -> str:
    status = "timeout" if result.timed_out else str(result.exit_code)
    return (
        f"$ {' '.join(result.argv)}\n"
        f"name: {result.name}\n"
        f"exit_code: {status}\n"
        f"stdout:\n{result.stdout}"
        "\n"
        f"stderr:\n{result.stderr}"
    )

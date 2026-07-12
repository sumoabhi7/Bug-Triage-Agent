from __future__ import annotations

import inspect
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

import bta.services.analyze as analyze_module
import bta.services.dedupe as dedupe_module
import bta.services.fix as fix_module
import bta.services.pr as pr_module
import bta.services.scan as scan_module
from bta.ai.parsers import ParsedSourceFile
from bta.ai.patching import SourceFileContext
from bta.ai.verification import ValidationCommand
from bta.domain import (
    DuplicateCandidate,
    EvidencePack,
    IssueMetadata,
    PatchDraft,
    PRDraft,
    RootCauseHypothesis,
    StackFrame,
    TriageCase,
    ValidationResult,
)
from bta.github.service import GitHubIssue, GitHubUser
from bta.services.analyze import AnalyzeService
from bta.services.dedupe import DedupeService
from bta.services.exceptions import AnalyzeServiceError, PublishServiceError
from bta.services.fix import FixService
from bta.services.models import (
    AnalyzeIssueRequest,
    DedupeRequest,
    FixRequest,
    PublishRequest,
    ScanRepositoryRequest,
)
from bta.services.pr import PublishService
from bta.services.scan import ScanService
from bta.services.status import StatusService


class FakeUnitOfWork:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    async def __aenter__(self) -> FakeUnitOfWork:
        self._calls.append("enter")
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        self._calls.append("exit")

    async def save_case(self, case: TriageCase) -> None:
        self._calls.append("save_case")

    async def save_evidence(self, case_id, evidence: EvidencePack) -> object:
        self._calls.append("save_evidence")
        return SimpleNamespace(id=uuid4())

    async def save_hypotheses(self, case_id, evidence_pack_id, hypotheses) -> None:
        self._calls.append("save_hypotheses")

    async def save_patch(self, case_id, patch: PatchDraft) -> None:
        self._calls.append("save_patch")

    async def save_validation(self, validation: ValidationResult) -> None:
        self._calls.append("save_validation")

    async def save_pr(self, case_id, draft: PRDraft) -> None:
        self._calls.append("save_pr")


def uow_factory(calls: list[str]):
    return lambda: FakeUnitOfWork(calls)


class FakeGitHub:
    def __init__(self) -> None:
        self.pushed: list[tuple[Path, str]] = []
        self.published: list[tuple[str, PRDraft]] = []

    def get_issue(self, repo: str, issue_number: int) -> GitHubIssue:
        return GitHubIssue(
            id=100,
            number=issue_number,
            title="Crash on missing token",
            body="ERROR bad\nKeyError: token",
            labels=["bug"],
            author="octocat",
            url="https://example.test/issue",
            state="open",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def authenticate(self) -> GitHubUser:
        return GitHubUser(login="octocat")

    def push_branch(self, repo_path: Path, branch_name: str) -> None:
        self.pushed.append((repo_path, branch_name))

    def publish_draft_pull_request(self, repo: str, draft: PRDraft) -> PRDraft:
        self.published.append((repo, draft))
        return draft.model_copy(update={"github_pr_number": 12, "pr_url": "https://pr.test"})


class FakeRetrieval:
    async def retrieve(self, input) -> EvidencePack:
        return EvidencePack(
            relevant_excerpts=["Crash on missing token"],
            stack_trace_frames=[StackFrame(file="app.py", line_number=1)],
            error_signatures=["KeyError: token"],
            duplicate_candidates=[
                DuplicateCandidate(repo="acme/widget", issue_number=1, similarity_score=0.9)
            ],
            embedding_model="fake",
            confidence=0.8,
        )


class FakeReasoning:
    async def generate_hypotheses(self, input) -> list[RootCauseHypothesis]:
        return [make_hypothesis()]


class FakeScanner:
    def __init__(self) -> None:
        self.roots: list[Path] = []

    def iter_source_files(self, root: Path):
        self.roots.append(root)
        yield SourceFileContext(repo_path="app.py", content="def f():\n    pass\n")


class ExplodingGitHub(FakeGitHub):
    def get_issue(self, repo: str, issue_number: int) -> GitHubIssue:
        raise RuntimeError("network failed")


class FakePatching:
    async def generate_patch(self, input) -> PatchDraft:
        return make_patch(input.hypothesis.id)


class FakeVerification:
    async def validate(self, input) -> ValidationResult:
        return make_validation(input.patch.id, overall=True)


def make_case() -> TriageCase:
    return TriageCase(
        repo="acme/widget",
        issue_number=42,
        issue_metadata=IssueMetadata(title="Bug", author="octocat"),
    )


def make_hypothesis() -> RootCauseHypothesis:
    return RootCauseHypothesis(
        rank=1,
        hypothesis="Missing fallback",
        category="config-error",
        confidence=0.8,
        evidence_references=["snippet:0"],
        affected_files=["app.py"],
        model_used="fake-reasoner",
    )


def make_patch(hypothesis_id) -> PatchDraft:
    return PatchDraft(
        hypothesis_id=hypothesis_id,
        diff_content="--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-a\n+b\n",
        files_modified=["app.py"],
        branch_name="bta/fix/test",
        commit_message="fix: test",
        explanation="test",
        model_used="fake-patcher",
    )


def make_validation(patch_id, *, overall: bool) -> ValidationResult:
    return ValidationResult(
        patch_draft_id=patch_id,
        overall_passed=overall,
        worktree_path="/tmp/worktree",
    )


@pytest.mark.asyncio
async def test_analyze_service_coordinates_workflow_and_persists() -> None:
    calls: list[str] = []
    service = AnalyzeService(
        github=FakeGitHub(),  # type: ignore[arg-type]
        retrieval=FakeRetrieval(),  # type: ignore[arg-type]
        reasoning=FakeReasoning(),  # type: ignore[arg-type]
        scan=ScanService(FakeScanner()),
        unit_of_work_factory=uow_factory(calls),
    )

    result = await service.analyze_issue(
        AnalyzeIssueRequest(repo="acme/widget", issue_number=42, persist=True)
    )

    assert result.case.repo == "acme/widget"
    assert result.evidence.embedding_model == "fake"
    assert result.hypotheses[0].rank == 1
    assert calls == ["enter", "save_case", "save_evidence", "save_hypotheses", "exit"]


@pytest.mark.asyncio
async def test_analyze_service_persist_false_does_not_open_unit_of_work() -> None:
    calls: list[str] = []
    service = AnalyzeService(
        github=FakeGitHub(),  # type: ignore[arg-type]
        retrieval=FakeRetrieval(),  # type: ignore[arg-type]
        reasoning=FakeReasoning(),  # type: ignore[arg-type]
        scan=ScanService(FakeScanner()),
        unit_of_work_factory=uow_factory(calls),
    )

    await service.analyze_issue(
        AnalyzeIssueRequest(repo="acme/widget", issue_number=42, persist=False)
    )

    assert calls == []


@pytest.mark.asyncio
async def test_analyze_service_wraps_lower_level_errors() -> None:
    service = AnalyzeService(
        github=ExplodingGitHub(),  # type: ignore[arg-type]
        retrieval=FakeRetrieval(),  # type: ignore[arg-type]
        reasoning=FakeReasoning(),  # type: ignore[arg-type]
        scan=ScanService(FakeScanner()),
        unit_of_work_factory=uow_factory([]),
    )

    with pytest.raises(AnalyzeServiceError) as exc_info:
        await service.analyze_issue(AnalyzeIssueRequest(repo="acme/widget", issue_number=42))

    assert isinstance(exc_info.value.__cause__, RuntimeError)


@pytest.mark.asyncio
async def test_scan_service_uses_repository_scanner_abstraction(tmp_path: Path) -> None:
    scanner = FakeScanner()
    service = ScanService(scanner)

    result = await service.scan_repository(ScanRepositoryRequest(repo_path=tmp_path))

    assert scanner.roots == [tmp_path]
    assert result.source_contexts[0].repo_path == "app.py"
    assert isinstance(result.source_files[0], ParsedSourceFile)


@pytest.mark.asyncio
async def test_dedupe_service_returns_evidence_duplicates() -> None:
    duplicate = DuplicateCandidate(repo="acme/widget", issue_number=2, similarity_score=0.8)
    evidence = EvidencePack(
        duplicate_candidates=[duplicate],
        embedding_model="fake",
        confidence=0.5,
    )

    result = await DedupeService().find_duplicates(
        DedupeRequest(case=make_case(), evidence=evidence)
    )

    assert result.duplicates == [duplicate]


@pytest.mark.asyncio
async def test_fix_service_coordinates_patch_and_validation(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    hypothesis = make_hypothesis()
    case = make_case().model_copy(update={"hypotheses": [hypothesis]})
    evidence = EvidencePack(embedding_model="fake", confidence=0.5)
    service = FixService(
        patching=FakePatching(),  # type: ignore[arg-type]
        verification=FakeVerification(),  # type: ignore[arg-type]
        unit_of_work_factory=uow_factory(calls),
    )

    result = await service.generate_and_validate_fix(
        FixRequest(
            case=case,
            evidence=evidence,
            worktree_path=tmp_path,
            validation_commands=[ValidationCommand(name="tests", argv=("pytest",))],
            persist=True,
        )
    )

    assert result.patch.hypothesis_id == hypothesis.id
    assert result.validation.overall_passed is True
    assert calls == ["enter", "save_patch", "save_validation", "exit"]


def test_fix_request_requires_worktree_path() -> None:
    with pytest.raises(TypeError):
        FixRequest(  # type: ignore[call-arg]
            case=make_case(),
            evidence=EvidencePack(embedding_model="fake", confidence=0.5),
        )


@pytest.mark.asyncio
async def test_publish_service_gates_on_successful_validation(tmp_path: Path) -> None:
    github = FakeGitHub()
    calls: list[str] = []
    service = PublishService(github=github, unit_of_work_factory=uow_factory(calls))  # type: ignore[arg-type]
    patch = make_patch(make_hypothesis().id)
    failed = make_validation(patch.id, overall=False)
    draft = PRDraft(
        patch_draft_id=patch.id,
        title="Fix bug",
        body="Body",
        base_branch="main",
        head_branch="bta/fix/test",
    )

    with pytest.raises(PublishServiceError):
        await service.publish_draft_pr(
            PublishRequest(
                repo="acme/widget",
                case_id=make_case().id,
                repo_path=tmp_path,
                branch_name="bta/fix/test",
                pr_draft=draft,
                validation=failed,
            )
        )

    assert github.pushed == []
    assert github.published == []
    assert calls == []


@pytest.mark.asyncio
async def test_publish_service_pushes_and_persists_after_successful_validation(
    tmp_path: Path,
) -> None:
    github = FakeGitHub()
    calls: list[str] = []
    service = PublishService(github=github, unit_of_work_factory=uow_factory(calls))  # type: ignore[arg-type]
    patch = make_patch(make_hypothesis().id)
    draft = PRDraft(
        patch_draft_id=patch.id,
        title="Fix bug",
        body="Body",
        base_branch="main",
        head_branch="bta/fix/test",
    )

    result = await service.publish_draft_pr(
        PublishRequest(
            repo="acme/widget",
            case_id=make_case().id,
            repo_path=tmp_path,
            branch_name="bta/fix/test",
            pr_draft=draft,
            validation=make_validation(patch.id, overall=True),
            persist=True,
        )
    )

    assert result.pr_draft.github_pr_number == 12
    assert github.pushed == [(tmp_path, "bta/fix/test")]
    assert github.published[0][0] == "acme/widget"
    assert calls == ["enter", "save_pr", "exit"]


@pytest.mark.asyncio
async def test_status_service_reports_readiness_without_raising() -> None:
    service = StatusService(
        session_factory=None,
        github=FakeGitHub(),  # type: ignore[arg-type]
        reasoning_ready=lambda: True,
        patch_ready=lambda: False,
    )

    result = await service.check()

    assert result.database_ok is False
    assert result.github_ok is True
    assert result.reasoning_provider_ok is True
    assert result.patch_provider_ok is False
    assert result.details["reasoning_provider"] == "ok"
    assert result.details["patch_provider"] == "not configured"


def test_services_do_not_import_cli_or_orchestrator() -> None:
    for module in [
        analyze_module,
        dedupe_module,
        fix_module,
        pr_module,
        scan_module,
    ]:
        source = inspect.getsource(module)
        assert "bta.cli" not in source
        assert "bta.orchestrator" not in source

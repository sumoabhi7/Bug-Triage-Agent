from __future__ import annotations

from bta.ai.parsers import parse_issue
from bta.ai.reasoning import ReasoningEngine, ReasoningInput
from bta.ai.retrieval import RetrievalEngine, RetrievalInput
from bta.domain import TriageCase
from bta.github.service import GitHubAdapter
from bta.services.exceptions import AnalyzeServiceError
from bta.services.models import AnalyzeIssueRequest, AnalyzeIssueResult, ScanRepositoryRequest
from bta.services.scan import ScanService
from bta.services.unit_of_work import UnitOfWorkFactory


class AnalyzeService:
    def __init__(
        self,
        *,
        github: GitHubAdapter,
        retrieval: RetrievalEngine,
        reasoning: ReasoningEngine,
        scan: ScanService,
        unit_of_work_factory: UnitOfWorkFactory,
    ) -> None:
        self._github = github
        self._retrieval = retrieval
        self._reasoning = reasoning
        self._scan = scan
        self._unit_of_work_factory = unit_of_work_factory

    async def analyze_issue(self, request: AnalyzeIssueRequest) -> AnalyzeIssueResult:
        try:
            issue = self._github.get_issue(request.repo, request.issue_number)
            parsed_issue = parse_issue(issue)
            case = TriageCase(
                repo=request.repo,
                issue_number=request.issue_number,
                issue_metadata=parsed_issue.metadata,
                raw_logs=parsed_issue.raw_logs,
                stack_traces=parsed_issue.stack_traces,
                error_messages=parsed_issue.error_messages,
            )
            source_files = list(request.source_files)
            if request.repo_path is not None:
                scan_result = await self._scan.scan_repository(
                    ScanRepositoryRequest(repo_path=request.repo_path, persist=False)
                )
                source_files.extend(scan_result.source_files)
            evidence = await self._retrieval.retrieve(
                RetrievalInput(case=case, source_files=source_files)
            )
            hypotheses = await self._reasoning.generate_hypotheses(
                ReasoningInput(evidence=evidence)
            )
            case = case.model_copy(
                update={
                    "evidence": evidence,
                    "candidate_duplicates": evidence.duplicate_candidates,
                    "hypotheses": hypotheses,
                }
            )
            if request.persist:
                async with self._unit_of_work_factory() as unit_of_work:
                    await unit_of_work.save_case(case)
                    evidence_record = await unit_of_work.save_evidence(case.id, evidence)
                    await unit_of_work.save_hypotheses(
                        case.id,
                        evidence_record.id,
                        hypotheses,
                    )
            return AnalyzeIssueResult(case=case, evidence=evidence, hypotheses=hypotheses)
        except AnalyzeServiceError:
            raise
        except Exception as exc:
            raise AnalyzeServiceError("issue analysis failed") from exc

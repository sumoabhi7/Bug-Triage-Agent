from __future__ import annotations

from bta.ai.patching import PatchGenerationEngine, PatchGenerationInput
from bta.ai.verification import VerificationEngine, VerificationInput
from bta.domain import RootCauseHypothesis
from bta.services.exceptions import FixServiceError
from bta.services.models import FixRequest, FixResult
from bta.services.unit_of_work import UnitOfWorkFactory


class FixService:
    def __init__(
        self,
        *,
        patching: PatchGenerationEngine,
        verification: VerificationEngine,
        unit_of_work_factory: UnitOfWorkFactory,
    ) -> None:
        self._patching = patching
        self._verification = verification
        self._unit_of_work_factory = unit_of_work_factory

    async def generate_and_validate_fix(self, request: FixRequest) -> FixResult:
        try:
            hypothesis = _select_hypothesis(request)
            patch = await self._patching.generate_patch(
                PatchGenerationInput(
                    hypothesis=hypothesis,
                    evidence=request.evidence,
                    source_files=request.source_files,
                    issue_number=request.case.issue_number,
                    generation_attempt=request.generation_attempt,
                )
            )
            validation = await self._verification.validate(
                VerificationInput(
                    patch=patch,
                    worktree_path=request.worktree_path,
                    commands=request.validation_commands,
                )
            )
            if request.persist:
                async with self._unit_of_work_factory() as unit_of_work:
                    await unit_of_work.save_patch(request.case.id, patch)
                    await unit_of_work.save_validation(validation)
            return FixResult(patch=patch, validation=validation)
        except FixServiceError:
            raise
        except Exception as exc:
            raise FixServiceError("fix generation failed") from exc


def _select_hypothesis(request: FixRequest) -> RootCauseHypothesis:
    candidates = list(request.hypotheses) or list(request.case.hypotheses)
    if not candidates:
        raise FixServiceError("no hypotheses available")
    if request.hypothesis_id is not None:
        for hypothesis in candidates:
            if hypothesis.id == request.hypothesis_id:
                return hypothesis
        raise FixServiceError(f"hypothesis not found: {request.hypothesis_id}")
    return sorted(candidates, key=lambda item: item.rank)[0]

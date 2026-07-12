from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bta.domain import (
    EvidencePack,
    PatchDraft,
    PRDraft,
    RootCauseHypothesis,
    TriageCase,
    ValidationResult,
)
from bta.storage.models import (
    EvidencePackRecord,
    PatchDraftRecord,
    PullRequestRecord,
    RootCauseHypothesisRecord,
    TriageCaseRecord,
    ValidationResultRecord,
)


class UnitOfWork:
    """Service-layer transaction boundary over an AsyncSession."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork is not active")
        return self._session

    async def __aenter__(self) -> UnitOfWork:
        self._session = self._session_factory()
        await self.session.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()
            self._session = None

    async def save_case(self, case: TriageCase) -> TriageCaseRecord:
        record = await self.session.merge(TriageCaseRecord.from_domain(case))
        await self.session.flush()
        return record

    async def save_evidence(self, case_id: UUID, evidence: EvidencePack) -> EvidencePackRecord:
        record = EvidencePackRecord.from_domain(case_id, evidence)
        self.session.add(record)
        await self.session.flush()
        return record

    async def save_hypotheses(
        self,
        case_id: UUID,
        evidence_pack_id: UUID,
        hypotheses: list[RootCauseHypothesis],
    ) -> list[RootCauseHypothesisRecord]:
        records = [
            RootCauseHypothesisRecord.from_domain(case_id, evidence_pack_id, hypothesis)
            for hypothesis in hypotheses
        ]
        self.session.add_all(records)
        await self.session.flush()
        return records

    async def save_patch(self, case_id: UUID, patch: PatchDraft) -> PatchDraftRecord:
        record = PatchDraftRecord.from_domain(case_id, patch)
        self.session.add(record)
        await self.session.flush()
        return record

    async def save_validation(self, validation: ValidationResult) -> ValidationResultRecord:
        record = ValidationResultRecord.from_domain(validation)
        self.session.add(record)
        await self.session.flush()
        return record

    async def save_pr(self, case_id: UUID, draft: PRDraft) -> PullRequestRecord:
        record = PullRequestRecord.from_domain(case_id, draft)
        self.session.add(record)
        await self.session.flush()
        return record


type UnitOfWorkFactory = Callable[[], UnitOfWork]

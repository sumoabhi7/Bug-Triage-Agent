from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bta.storage.models import IssueEmbeddingRecord, TriageCaseRecord

EMBEDDING_DIMENSIONS = 384


@dataclass(frozen=True, slots=True)
class SimilarIssue:
    triage_case_id: UUID
    repo: str
    issue_number: int
    similarity: float


class VectorStore:
    """PostgreSQL pgvector operations used by retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def put_issue_embedding(
        self,
        *,
        triage_case_id: UUID,
        embedding: list[float],
        content_hash: str,
        model_name: str,
    ) -> IssueEmbeddingRecord:
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(f"embedding must contain {EMBEDDING_DIMENSIONS} dimensions")
        statement = (
            insert(IssueEmbeddingRecord)
            .values(
                triage_case_id=triage_case_id,
                embedding=embedding,
                content_hash=content_hash,
                model_name=model_name,
            )
            .on_conflict_do_nothing(
                constraint="uq_issue_embeddings_identity",
            )
            .returning(IssueEmbeddingRecord)
        )
        created = (await self._session.scalars(statement)).one_or_none()
        if created is not None:
            return created
        existing = await self._session.scalar(
            select(IssueEmbeddingRecord).where(
                IssueEmbeddingRecord.triage_case_id == triage_case_id,
                IssueEmbeddingRecord.model_name == model_name,
                IssueEmbeddingRecord.content_hash == content_hash,
            )
        )
        if existing is None:
            raise RuntimeError("embedding conflict did not resolve to an existing row")
        return existing

    async def find_similar_issues(
        self,
        *,
        source_case_id: UUID,
        repo: str,
        model_name: str,
        embedding: list[float],
        threshold: float,
        limit: int = 10,
    ) -> list[SimilarIssue]:
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(f"embedding must contain {EMBEDDING_DIMENSIONS} dimensions")
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        distance = IssueEmbeddingRecord.embedding.cosine_distance(embedding)
        statement = (
            select(
                TriageCaseRecord.id,
                TriageCaseRecord.repo,
                TriageCaseRecord.issue_number,
                (1 - distance).label("similarity"),
            )
            .join(
                IssueEmbeddingRecord,
                IssueEmbeddingRecord.triage_case_id == TriageCaseRecord.id,
            )
            .where(
                TriageCaseRecord.id != source_case_id,
                TriageCaseRecord.repo == repo,
                IssueEmbeddingRecord.model_name == model_name,
                distance <= 1 - threshold,
            )
            .order_by(distance, TriageCaseRecord.id)
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            SimilarIssue(
                triage_case_id=row.id,
                repo=row.repo,
                issue_number=row.issue_number,
                similarity=float(row.similarity),
            )
            for row in rows
        ]

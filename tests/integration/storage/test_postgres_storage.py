import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bta.domain import IssueMetadata, TriageCase
from bta.storage.database import create_engine
from bta.storage.models import TriageCaseRecord
from bta.storage.vector_store import VectorStore

DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL is required")


@pytest.mark.asyncio
async def test_async_storage_and_vector_similarity_round_trip() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            source = TriageCase(
                repo="integration/storage",
                issue_number=1,
                issue_metadata=IssueMetadata(title="Source", author="test"),
            )
            candidate = TriageCase(
                repo="integration/storage",
                issue_number=2,
                issue_metadata=IssueMetadata(title="Candidate", author="test"),
            )
            session.add_all(
                [
                    TriageCaseRecord.from_domain(source),
                    TriageCaseRecord.from_domain(candidate),
                ]
            )
            await session.flush()

            vector_store = VectorStore(session)
            vector = [1.0] + [0.0] * 383
            first = await vector_store.put_issue_embedding(
                triage_case_id=candidate.id,
                embedding=vector,
                content_hash="candidate-hash",
                model_name="all-MiniLM-L6-v2",
            )
            repeated = await vector_store.put_issue_embedding(
                triage_case_id=candidate.id,
                embedding=vector,
                content_hash="candidate-hash",
                model_name="all-MiniLM-L6-v2",
            )
            results = await vector_store.find_similar_issues(
                source_case_id=source.id,
                repo=source.repo,
                model_name="all-MiniLM-L6-v2",
                embedding=vector,
                threshold=0.99,
            )

            assert first.id == repeated.id
            assert results[0].triage_case_id == candidate.id
            assert results[0].similarity == pytest.approx(1.0)
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()

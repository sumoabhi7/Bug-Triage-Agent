from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from bta.storage.vector_store import VectorStore


@pytest.mark.asyncio
async def test_vector_store_rejects_wrong_embedding_dimensions() -> None:
    store = VectorStore(AsyncMock())

    with pytest.raises(ValueError, match="384"):
        await store.put_issue_embedding(
            triage_case_id=uuid4(),
            embedding=[0.0],
            content_hash="hash",
            model_name="all-MiniLM-L6-v2",
        )


@pytest.mark.asyncio
async def test_vector_store_rejects_invalid_similarity_threshold() -> None:
    store = VectorStore(AsyncMock())

    with pytest.raises(ValueError, match="threshold"):
        await store.find_similar_issues(
            source_case_id=uuid4(),
            repo="owner/repo",
            model_name="all-MiniLM-L6-v2",
            embedding=[0.0] * 384,
            threshold=1.1,
        )

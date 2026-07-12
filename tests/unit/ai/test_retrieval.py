from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

import pytest

from bta.ai.parsers import ParsedSourceFile
from bta.ai.retrieval import (
    RetrievalConfig,
    RetrievalEngine,
    RetrievalInput,
    SimilarityStore,
    build_issue_text,
    score_retrieval_confidence,
    score_snippet,
    select_context_snippets,
)
from bta.domain import (
    CodeSnippet,
    DuplicateCandidate,
    IssueMetadata,
    StackFrame,
    StackTrace,
    TriageCase,
)
from bta.storage.vector_store import SimilarIssue, VectorStore


@dataclass(frozen=True, slots=True)
class FakeEmbeddingProvider:
    model_name: str = "fake-embedding-model"
    dimensions: int = 384

    def embed_text(self, text: str) -> list[float]:
        seed = min(1.0, len(text) / 1000)
        return [seed] * self.dimensions


@dataclass(slots=True)
class FakeSimilarityStore:
    similar_issues: list[SimilarIssue] = field(default_factory=list)
    put_calls: list[dict[str, object]] = field(default_factory=list)
    search_calls: list[dict[str, object]] = field(default_factory=list)

    async def put_issue_embedding(
        self,
        *,
        triage_case_id,
        embedding: list[float],
        content_hash: str,
        model_name: str,
    ) -> object:
        self.put_calls.append(
            {
                "triage_case_id": triage_case_id,
                "embedding": embedding,
                "content_hash": content_hash,
                "model_name": model_name,
            }
        )
        return object()

    async def find_similar_issues(
        self,
        *,
        source_case_id,
        repo: str,
        model_name: str,
        embedding: list[float],
        threshold: float,
        limit: int = 10,
    ) -> list[SimilarIssue]:
        self.search_calls.append(
            {
                "source_case_id": source_case_id,
                "repo": repo,
                "model_name": model_name,
                "embedding": embedding,
                "threshold": threshold,
                "limit": limit,
            }
        )
        return self.similar_issues[:limit]


def make_case() -> TriageCase:
    return TriageCase(
        repo="acme/widget",
        issue_number=42,
        issue_metadata=IssueMetadata(
            github_issue_id=1001,
            title="Crash when config token is missing",
            body="The failure happens in app/config.py when load_config reads the token.",
            labels=["bug", "config"],
            author="octocat",
        ),
        raw_logs=["ERROR failed to load token"],
        stack_traces=[
            StackTrace(
                raw_text="Traceback ...",
                language="python",
                exception_type="KeyError",
                message="'token'",
                frames=[
                    StackFrame(
                        file="app/config.py",
                        line_number=12,
                        function_name="load_config",
                    )
                ],
            )
        ],
        error_messages=["KeyError: 'token'"],
    )


def make_source_files() -> list[ParsedSourceFile]:
    return [
        ParsedSourceFile(
            repo_path="app/config.py",
            language="python",
            snippets=[
                CodeSnippet(
                    repo_path="app/config.py",
                    start_line=10,
                    end_line=14,
                    symbol_name="load_config",
                    symbol_type="function",
                    content="def load_config():\n    return config['token']",
                    score=0.5,
                )
            ],
        ),
        ParsedSourceFile(
            repo_path="app/other.py",
            language="python",
            snippets=[
                CodeSnippet(
                    repo_path="app/other.py",
                    start_line=1,
                    end_line=2,
                    symbol_name="other",
                    symbol_type="function",
                    content="def other():\n    return None",
                )
            ],
        ),
    ]


def test_vector_store_structurally_satisfies_similarity_store() -> None:
    instance = VectorStore.__new__(VectorStore)

    assert isinstance(instance, SimilarityStore)


def test_retrieval_engine_rejects_embedding_dimension_mismatch() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        RetrievalEngine(
            embedding_provider=FakeEmbeddingProvider(dimensions=3),
            similarity_store=FakeSimilarityStore(),
        )


def test_build_issue_text_is_deterministic() -> None:
    case = make_case()

    first = build_issue_text(case)
    second = build_issue_text(case)

    assert first == second
    assert "Crash when config token is missing" in first
    assert "app/config.py" in first
    assert "load_config" in first


def test_score_snippet_uses_path_symbol_error_and_existing_score() -> None:
    case = make_case()
    snippet = make_source_files()[0].snippets[0]

    assert score_snippet(case, snippet) == pytest.approx(0.9)


def test_select_context_snippets_uses_stable_tie_ordering() -> None:
    case = make_case()
    source_files = [
        ParsedSourceFile(
            repo_path="x",
            language="python",
            snippets=[
                CodeSnippet(
                    repo_path="app/b.py",
                    start_line=2,
                    end_line=2,
                    symbol_name="b",
                    content="token",
                    score=1,
                ),
                CodeSnippet(
                    repo_path="app/a.py",
                    start_line=1,
                    end_line=1,
                    symbol_name="a",
                    content="token",
                    score=1,
                ),
            ],
        )
    ]

    selected = select_context_snippets(case, source_files, limit=2)

    assert [snippet.repo_path for snippet in selected] == ["app/a.py", "app/b.py"]


def test_confidence_uses_documented_weights_and_clamps() -> None:
    confidence = score_retrieval_confidence(
        issue_text="x" * 240,
        stack_trace_frames=[StackFrame(file="app.py")],
        error_signatures=["ValueError: bad"],
        snippets=[CodeSnippet(repo_path="app.py", start_line=1, end_line=1, content="", score=1)],
        duplicates=[
            DuplicateCandidate(
                triage_case_id=uuid4(),
                repo="acme/widget",
                issue_number=1,
                similarity_score=1,
            )
        ],
    )

    assert confidence == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_retrieve_assembles_evidence_pack_and_uses_similarity_store() -> None:
    case = make_case()
    original_dump = case.model_dump(mode="json")
    duplicate_id = uuid4()
    store = FakeSimilarityStore(
        similar_issues=[
            SimilarIssue(
                triage_case_id=duplicate_id,
                repo="acme/widget",
                issue_number=7,
                similarity=0.91,
            )
        ]
    )
    engine = RetrievalEngine(
        embedding_provider=FakeEmbeddingProvider(),
        similarity_store=store,
        config=RetrievalConfig(duplicate_threshold=0.8, duplicate_limit=5, context_limit=3),
    )

    evidence = await engine.retrieve(RetrievalInput(case=case, source_files=make_source_files()))

    assert len(store.put_calls) == 1
    assert store.put_calls[0]["triage_case_id"] == case.id
    assert store.put_calls[0]["model_name"] == "fake-embedding-model"
    assert len(store.search_calls) == 1
    assert store.search_calls[0]["threshold"] == 0.8
    assert evidence.embedding_model == "fake-embedding-model"
    assert evidence.related_issues == []
    assert evidence.duplicate_candidates[0].triage_case_id == duplicate_id
    assert evidence.duplicate_candidates[0].similarity_score == 0.91
    assert evidence.similar_code_snippets[0].repo_path == "app/config.py"
    assert evidence.file_references[0].repo_path == "app/config.py"
    assert evidence.stack_trace_frames[0].function_name == "load_config"
    assert "KeyError: 'token'" in evidence.error_signatures
    assert 0 <= evidence.confidence <= 1
    assert case.model_dump(mode="json") == original_dump


@pytest.mark.asyncio
async def test_retrieval_engine_is_stateless_across_repeated_calls() -> None:
    case = make_case()
    store = FakeSimilarityStore()
    engine = RetrievalEngine(
        embedding_provider=FakeEmbeddingProvider(),
        similarity_store=store,
    )

    first = await engine.retrieve(RetrievalInput(case=case, source_files=make_source_files()))
    second = await engine.retrieve(RetrievalInput(case=case, source_files=make_source_files()))

    assert first.model_dump(mode="json", exclude={"retrieval_timestamp"}) == second.model_dump(
        mode="json", exclude={"retrieval_timestamp"}
    )
    assert len(store.put_calls) == 2
    assert len(store.search_calls) == 2

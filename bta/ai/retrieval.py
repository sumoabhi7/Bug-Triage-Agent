from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from bta.ai.parsers import ParsedSourceFile
from bta.domain import (
    CodeSnippet,
    DuplicateCandidate,
    EvidencePack,
    FileReference,
    StackFrame,
    TriageCase,
)
from bta.storage.models import content_hash
from bta.storage.vector_store import EMBEDDING_DIMENSIONS, SimilarIssue

ISSUE_TEXT_COMPLETENESS_LENGTH = 240


class EmbeddingProvider(Protocol):
    @property
    def model_name(self) -> str:
        """Embedding model name."""

    @property
    def dimensions(self) -> int:
        """Embedding vector dimensions."""

    def embed_text(self, text: str) -> list[float]:
        """Return an embedding for text."""


@runtime_checkable
class SimilarityStore(Protocol):
    async def put_issue_embedding(
        self,
        *,
        triage_case_id: UUID,
        embedding: list[float],
        content_hash: str,
        model_name: str,
    ) -> object:
        """Persist an issue embedding."""

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
        """Find issues similar to the supplied embedding."""


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    duplicate_threshold: float = 0.82
    duplicate_limit: int = 10
    context_limit: int = 8
    embedding_dimensions: int = EMBEDDING_DIMENSIONS

    def __post_init__(self) -> None:
        if not 0 <= self.duplicate_threshold <= 1:
            raise ValueError("duplicate_threshold must be between 0 and 1")
        if self.duplicate_limit < 1:
            raise ValueError("duplicate_limit must be positive")
        if self.context_limit < 1:
            raise ValueError("context_limit must be positive")
        if self.embedding_dimensions < 1:
            raise ValueError("embedding_dimensions must be positive")


@dataclass(frozen=True, slots=True)
class RetrievalInput:
    case: TriageCase
    source_files: Sequence[ParsedSourceFile]


class SentenceTransformerEmbeddingProvider:
    """Sentence-transformers based embedding provider."""

    def __init__(self, model_name: str, *, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.dimensions = dimensions
        self._model: Any = SentenceTransformer(model_name)
        sample = self.embed_text("dimension check")
        if len(sample) != dimensions:
            raise ValueError(
                f"embedding model produced {len(sample)} dimensions; expected {dimensions}"
            )

    def embed_text(self, text: str) -> list[float]:
        encoded = self._model.encode(text)
        return [float(value) for value in encoded]


class RetrievalEngine:
    """Deterministic retrieval engine that assembles EvidencePack inputs."""

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        similarity_store: SimilarityStore,
        config: RetrievalConfig | None = None,
    ) -> None:
        config = config or RetrievalConfig()
        if embedding_provider.dimensions != config.embedding_dimensions:
            raise ValueError(
                "embedding provider dimensions must match retrieval configuration dimensions"
            )
        self._embedding_provider = embedding_provider
        self._similarity_store = similarity_store
        self._config = config

    async def retrieve(self, input: RetrievalInput) -> EvidencePack:
        case = input.case
        issue_text = build_issue_text(case)
        embedding = self._embedding_provider.embed_text(issue_text)
        await self._similarity_store.put_issue_embedding(
            triage_case_id=case.id,
            embedding=embedding,
            content_hash=content_hash(issue_text),
            model_name=self._embedding_provider.model_name,
        )
        similar_issues = await self._similarity_store.find_similar_issues(
            source_case_id=case.id,
            repo=case.repo,
            model_name=self._embedding_provider.model_name,
            embedding=embedding,
            threshold=self._config.duplicate_threshold,
            limit=self._config.duplicate_limit,
        )
        duplicates = [_duplicate_candidate(item) for item in similar_issues]
        snippets = select_context_snippets(
            case,
            input.source_files,
            limit=self._config.context_limit,
        )
        error_signatures = _error_signatures(case)
        return EvidencePack(
            relevant_excerpts=_relevant_excerpts(case),
            stack_trace_frames=_stack_trace_frames(case),
            error_signatures=error_signatures,
            file_references=_file_references(snippets),
            similar_code_snippets=snippets,
            duplicate_candidates=duplicates,
            related_issues=[],
            embedding_model=self._embedding_provider.model_name,
            confidence=score_retrieval_confidence(
                issue_text=issue_text,
                stack_trace_frames=_stack_trace_frames(case),
                error_signatures=error_signatures,
                snippets=snippets,
                duplicates=duplicates,
            ),
        )


def build_issue_text(case: TriageCase) -> str:
    parts: list[str] = [
        case.issue_metadata.title,
        case.issue_metadata.body,
        " ".join(case.issue_metadata.labels),
    ]
    parts.extend(case.error_messages)
    parts.extend(case.raw_logs)
    for trace in case.stack_traces:
        if trace.exception_type:
            parts.append(trace.exception_type)
        if trace.message:
            parts.append(trace.message)
        for frame in trace.frames:
            if frame.file:
                parts.append(frame.file)
            if frame.function_name:
                parts.append(frame.function_name)
    return "\n".join(part.strip() for part in parts if part and part.strip())


def score_snippet(case: TriageCase, snippet: CodeSnippet) -> float:
    score = 0.0
    stack_paths = {frame.file for frame in _stack_trace_frames(case) if frame.file}
    stack_functions = {
        frame.function_name.lower() for frame in _stack_trace_frames(case) if frame.function_name
    }
    if snippet.repo_path in stack_paths:
        score += 0.4
    if snippet.symbol_name and snippet.symbol_name.lower() in stack_functions:
        score += 0.25
    if snippet.repo_path in case.issue_metadata.body:
        score += 0.15
    score += 0.15 * _error_term_overlap(case.error_messages, snippet.content)
    if snippet.score is not None:
        score += 0.05 * snippet.score
    return _clamp(score)


def select_context_snippets(
    case: TriageCase,
    source_files: Sequence[ParsedSourceFile],
    *,
    limit: int,
) -> list[CodeSnippet]:
    scored = [
        (score_snippet(case, snippet), snippet)
        for source_file in source_files
        for snippet in source_file.snippets
    ]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].repo_path,
            item[1].start_line,
            item[1].end_line,
            item[1].symbol_name or "",
        )
    )
    return [snippet.model_copy(update={"score": score}) for score, snippet in scored[:limit]]


def score_retrieval_confidence(
    *,
    issue_text: str,
    stack_trace_frames: Sequence[StackFrame],
    error_signatures: Sequence[str],
    snippets: Sequence[CodeSnippet],
    duplicates: Sequence[DuplicateCandidate],
) -> float:
    score = 0.0
    if stack_trace_frames:
        score += 0.25
    if error_signatures:
        score += 0.20
    score += 0.25 * max((snippet.score or 0 for snippet in snippets), default=0)
    score += 0.20 * max((item.similarity_score for item in duplicates), default=0)
    score += 0.10 * min(1.0, len(issue_text) / ISSUE_TEXT_COMPLETENESS_LENGTH)
    return _clamp(score)


def _duplicate_candidate(item: SimilarIssue) -> DuplicateCandidate:
    return DuplicateCandidate(
        repo=item.repo,
        issue_number=item.issue_number,
        triage_case_id=item.triage_case_id,
        similarity_score=item.similarity,
    )


def _relevant_excerpts(case: TriageCase) -> list[str]:
    excerpts = [
        case.issue_metadata.title,
        _first_nonempty_line(case.issue_metadata.body),
        *case.error_messages[:3],
        *case.raw_logs[:2],
    ]
    return _dedupe([item for item in excerpts if item])


def _first_nonempty_line(value: str) -> str:
    for line in value.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _stack_trace_frames(case: TriageCase) -> list[StackFrame]:
    return [frame for trace in case.stack_traces for frame in trace.frames]


def _error_signatures(case: TriageCase) -> list[str]:
    values = list(case.error_messages)
    for trace in case.stack_traces:
        if trace.exception_type:
            if trace.message:
                values.append(f"{trace.exception_type}: {trace.message}")
            else:
                values.append(trace.exception_type)
    return _dedupe(values)


def _file_references(snippets: Sequence[CodeSnippet]) -> list[FileReference]:
    return [
        FileReference(
            repo_path=snippet.repo_path,
            start_line=snippet.start_line,
            end_line=snippet.end_line,
            content=snippet.content,
        )
        for snippet in snippets
    ]


def _error_term_overlap(error_messages: Sequence[str], content: str) -> float:
    error_terms = _terms(" ".join(error_messages))
    if not error_terms:
        return 0.0
    content_terms = _terms(content)
    if not content_terms:
        return 0.0
    return len(error_terms & content_terms) / len(error_terms)


def _terms(value: str) -> set[str]:
    return {term.lower() for term in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", value)}


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))

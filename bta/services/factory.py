from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from bta.ai.patching import PatchGenerationEngine, PatchGenerationError
from bta.ai.reasoning import OllamaLLMProvider, OllamaProviderConfig, ReasoningEngine
from bta.ai.retrieval import (
    RetrievalConfig,
    RetrievalEngine,
    SentenceTransformerEmbeddingProvider,
)
from bta.ai.verification import VerificationEngine
from bta.config import Settings
from bta.github.service import GitHubAdapter
from bta.services.analyze import AnalyzeService
from bta.services.container import ServiceContainer
from bta.services.dedupe import DedupeService
from bta.services.eval import EvalService
from bta.services.fix import FixService
from bta.services.pr import PublishService
from bta.services.scan import FilesystemRepositoryScanner, ScanService
from bta.services.status import StatusService
from bta.services.unit_of_work import UnitOfWork
from bta.storage.database import create_engine, create_session_factory
from bta.storage.vector_store import SimilarIssue, VectorStore


@dataclass(frozen=True, slots=True)
class StorageDependencies:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]


@dataclass(frozen=True, slots=True)
class AIDependencies:
    retrieval: RetrievalEngine
    reasoning: ReasoningEngine
    patching: PatchGenerationEngine
    verification: VerificationEngine
    reasoning_provider_ready: bool
    patch_provider_ready: bool
    managed_resources: tuple[object, ...]


class SessionSimilarityStore:
    """SimilarityStore adapter that creates a VectorStore per storage operation."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def put_issue_embedding(
        self,
        *,
        triage_case_id: UUID,
        embedding: list[float],
        content_hash: str,
        model_name: str,
    ) -> object:
        async with self._session_factory() as session, session.begin():
            return await VectorStore(session).put_issue_embedding(
                triage_case_id=triage_case_id,
                embedding=embedding,
                content_hash=content_hash,
                model_name=model_name,
            )

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
        async with self._session_factory() as session:
            return await VectorStore(session).find_similar_issues(
                source_case_id=source_case_id,
                repo=repo,
                model_name=model_name,
                embedding=embedding,
                threshold=threshold,
                limit=limit,
            )


class UnavailablePatchLLMProvider:
    @property
    def model_name(self) -> str:
        return "unconfigured-patch-provider"

    async def generate_structured(
        self,
        prompt: str,
        *,
        response_format: Literal["json"],
    ) -> str:
        raise PatchGenerationError("patch LLM provider is not configured")


def build_service_container(settings: Settings) -> ServiceContainer:
    storage = build_storage(settings)
    github = build_github(settings)

    def unit_of_work_factory() -> UnitOfWork:
        return UnitOfWork(storage.session_factory)

    scanner = FilesystemRepositoryScanner()
    scan = ScanService(scanner)
    ai = build_ai_dependencies(settings, storage.session_factory)
    analyze = AnalyzeService(
        github=github,
        retrieval=ai.retrieval,
        reasoning=ai.reasoning,
        scan=scan,
        unit_of_work_factory=unit_of_work_factory,
    )
    dedupe = DedupeService()
    fix = FixService(
        patching=ai.patching,
        verification=ai.verification,
        unit_of_work_factory=unit_of_work_factory,
    )
    publish = PublishService(github=github, unit_of_work_factory=unit_of_work_factory)
    status = StatusService(
        session_factory=storage.session_factory,
        github=github,
        reasoning_ready=lambda: ai.reasoning_provider_ready,
        patch_ready=lambda: ai.patch_provider_ready,
    )
    evaluation = EvalService()
    return ServiceContainer(
        analyze=analyze,
        scan=scan,
        dedupe=dedupe,
        fix=fix,
        publish=publish,
        status=status,
        eval=evaluation,
        managed_resources=(storage.engine, *ai.managed_resources),
    )


def build_storage(settings: Settings) -> StorageDependencies:
    engine = create_engine(settings.database_url, echo=settings.database_echo)
    session_factory = create_session_factory(engine)
    return StorageDependencies(engine=engine, session_factory=session_factory)


def build_github(settings: Settings) -> GitHubAdapter:
    token = settings.github_token.get_secret_value() if settings.github_token else None
    return GitHubAdapter(token=token)


def build_ai_dependencies(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> AIDependencies:
    embedding_provider = SentenceTransformerEmbeddingProvider(
        settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    retrieval = RetrievalEngine(
        embedding_provider=embedding_provider,
        similarity_store=SessionSimilarityStore(session_factory),
        config=RetrievalConfig(embedding_dimensions=settings.embedding_dimensions),
    )
    reasoning_provider = OllamaLLMProvider(
        OllamaProviderConfig(
            host=settings.ollama_host,
            model=settings.ollama_model,
            max_retries=settings.max_retries,
            retry_backoff_seconds=settings.retry_initial_seconds,
        )
    )
    reasoning = ReasoningEngine(llm_provider=reasoning_provider)
    patching = PatchGenerationEngine(llm_provider=UnavailablePatchLLMProvider())
    verification = VerificationEngine()
    return AIDependencies(
        retrieval=retrieval,
        reasoning=reasoning,
        patching=patching,
        verification=verification,
        reasoning_provider_ready=bool(settings.ollama_host and settings.ollama_model),
        patch_provider_ready=False,
        managed_resources=(reasoning_provider,),
    )

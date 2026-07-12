from __future__ import annotations

from dataclasses import dataclass

import pytest

from bta.config import Settings
from bta.services import factory
from bta.services.container import ServiceContainer


class Closable:
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


@dataclass(slots=True)
class FakeProvider:
    model_name: str = "fake"
    dimensions: int = 384

    def embed_text(self, text: str) -> list[float]:
        return [0.0] * self.dimensions


class FakeOllamaProvider(Closable):
    @property
    def model_name(self) -> str:
        return "fake-ollama"

    async def generate_structured(self, prompt: str, *, response_format: str) -> str:
        return '{"hypotheses": []}'


def make_settings() -> Settings:
    return Settings(database_url="postgresql+asyncpg://user:pass@localhost/db")


@pytest.mark.asyncio
async def test_service_container_lifecycle_closes_resources() -> None:
    resource = Closable()
    container = ServiceContainer(
        analyze=object(),  # type: ignore[arg-type]
        scan=object(),  # type: ignore[arg-type]
        dedupe=object(),  # type: ignore[arg-type]
        fix=object(),  # type: ignore[arg-type]
        publish=object(),  # type: ignore[arg-type]
        status=object(),  # type: ignore[arg-type]
        eval=object(),  # type: ignore[arg-type]
        managed_resources=(resource,),
    )

    async with container as active:
        assert active is container

    assert resource.closed is True


@pytest.mark.asyncio
async def test_factory_constructs_dependencies_once_and_wires_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, int] = {
        "engine": 0,
        "session_factory": 0,
        "github": 0,
        "embedding": 0,
        "ollama": 0,
    }
    engine = Closable()

    def fake_create_engine(database_url: str, *, echo: bool = False) -> Closable:
        calls["engine"] += 1
        return engine

    def fake_session_factory(engine_arg: object) -> object:
        calls["session_factory"] += 1
        return object()

    class FakeGitHub:
        def __init__(self, *, token: str | None = None) -> None:
            calls["github"] += 1

    class FakeEmbedding(FakeProvider):
        def __init__(self, model_name: str, *, dimensions: int) -> None:
            calls["embedding"] += 1
            super().__init__(model_name=model_name, dimensions=dimensions)

    class FakeOllama(FakeOllamaProvider):
        def __init__(self, config: object) -> None:
            super().__init__()
            calls["ollama"] += 1

    monkeypatch.setattr(factory, "create_engine", fake_create_engine)
    monkeypatch.setattr(factory, "create_session_factory", fake_session_factory)
    monkeypatch.setattr(factory, "GitHubAdapter", FakeGitHub)
    monkeypatch.setattr(factory, "SentenceTransformerEmbeddingProvider", FakeEmbedding)
    monkeypatch.setattr(factory, "OllamaLLMProvider", FakeOllama)

    container = factory.build_service_container(make_settings())
    status = await container.status.check()

    assert isinstance(container, ServiceContainer)
    assert calls == {
        "engine": 1,
        "session_factory": 1,
        "github": 1,
        "embedding": 1,
        "ollama": 1,
    }
    assert status.reasoning_provider_ok is True
    assert status.patch_provider_ok is False
    assert status.details["reasoning_provider"] == "ok"
    assert status.details["patch_provider"] == "not configured"

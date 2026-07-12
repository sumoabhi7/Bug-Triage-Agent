from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

import httpx
import pytest

from bta.ai import reasoning
from bta.ai.reasoning import (
    HYPOTHESIS_RESPONSE_SCHEMA,
    LLMProvider,
    OllamaLLMProvider,
    OllamaProviderConfig,
    ReasoningCandidate,
    ReasoningConfig,
    ReasoningEngine,
    ReasoningInput,
    ReasoningParseError,
    ReasoningProviderError,
    calibrate_confidence,
    parse_hypothesis_response,
    rank_hypotheses,
    render_reasoning_prompt,
    valid_evidence_ids,
)
from bta.domain import (
    CodeSnippet,
    DuplicateCandidate,
    EvidencePack,
    FileReference,
    RelatedIssue,
    StackFrame,
)


def make_evidence() -> EvidencePack:
    return EvidencePack(
        relevant_excerpts=["Crash when config token is missing"],
        stack_trace_frames=[
            StackFrame(
                file="app/config.py",
                line_number=12,
                function_name="load_config",
            )
        ],
        error_signatures=["KeyError: 'token'"],
        file_references=[
            FileReference(
                repo_path="app/config.py",
                start_line=10,
                end_line=14,
                content="def load_config():\n    return config['token']",
            )
        ],
        similar_code_snippets=[
            CodeSnippet(
                repo_path="app/config.py",
                start_line=10,
                end_line=14,
                symbol_name="load_config",
                symbol_type="function",
                content="def load_config():\n    return config['token']",
                score=0.9,
            )
        ],
        duplicate_candidates=[
            DuplicateCandidate(
                repo="acme/widget",
                issue_number=7,
                similarity_score=0.91,
            )
        ],
        related_issues=[
            RelatedIssue(
                repo="acme/widget",
                issue_number=8,
                title="Token config crashes",
                similarity_score=0.75,
                state="open",
            )
        ],
        embedding_model="fake-embedding",
        confidence=0.8,
    )


def model_response(*, confidence: float = 0.9) -> str:
    return json.dumps(
        {
            "hypotheses": [
                {
                    "hypothesis": "Missing token handling raises KeyError.",
                    "explanation": "The stack frame and snippet both point to config token lookup.",
                    "category": "config-error",
                    "confidence": confidence,
                    "evidence_references": ["trace:0", "snippet:0", "missing:0"],
                    "affected_files": ["app/config.py"],
                    "affected_lines": [["app/config.py", 10, 14], ["bad.py", 20, 10]],
                }
            ]
        }
    )


@dataclass(slots=True)
class FakeProvider:
    raw_response: str = model_response()
    model_name: str = "fake-reasoner"
    prompts: list[str] | None = None
    formats: list[str] | None = None
    error: Exception | None = None

    async def generate_structured(
        self,
        prompt: str,
        *,
        response_format: Literal["json"],
    ) -> str:
        if self.prompts is None:
            self.prompts = []
        if self.formats is None:
            self.formats = []
        self.prompts.append(prompt)
        self.formats.append(response_format)
        if self.error is not None:
            raise self.error
        return self.raw_response


def test_fake_provider_satisfies_llm_provider_protocol() -> None:
    provider: LLMProvider = FakeProvider()

    assert provider.model_name == "fake-reasoner"


def test_render_reasoning_prompt_uses_external_template_and_stable_ids() -> None:
    evidence = make_evidence()

    first = render_reasoning_prompt(evidence)
    second = render_reasoning_prompt(evidence)

    assert first == second
    assert "Prompt version: v1" in first
    assert "Return only JSON with this shape:" in first
    assert "trace:0" in first
    assert "snippet:0" in first
    assert "duplicate:0" in first
    assert "related:0" in first


def test_parse_hypothesis_response_preserves_candidate_fields_and_filters_grounding() -> None:
    evidence = make_evidence()

    candidates = parse_hypothesis_response(
        model_response(confidence=1.5),
        valid_evidence_ids=valid_evidence_ids(evidence),
    )

    assert candidates == [
        ReasoningCandidate(
            hypothesis="Missing token handling raises KeyError.",
            explanation="The stack frame and snippet both point to config token lookup.",
            category="config-error",
            raw_confidence=1.0,
            evidence_references=["trace:0", "snippet:0"],
            affected_files=["app/config.py"],
            affected_lines=[("app/config.py", 10, 14)],
        )
    ]


def test_parse_hypothesis_response_raises_for_malformed_json_and_schema() -> None:
    with pytest.raises(ReasoningParseError) as malformed:
        parse_hypothesis_response("{bad", valid_evidence_ids=frozenset())

    assert isinstance(malformed.value.__cause__, json.JSONDecodeError)

    with pytest.raises(ReasoningParseError):
        parse_hypothesis_response("[]", valid_evidence_ids=frozenset())

    with pytest.raises(ReasoningParseError):
        parse_hypothesis_response("{}", valid_evidence_ids=frozenset())


def test_parse_hypothesis_response_skips_invalid_candidate_objects() -> None:
    raw = json.dumps(
        {
            "hypotheses": [
                {"hypothesis": "", "category": "bad", "confidence": 0.8},
                {
                    "hypothesis": "Valid candidate.",
                    "explanation": "Grounded explanation.",
                    "category": "config-error",
                    "confidence": 0.7,
                    "evidence_references": ["trace:0"],
                    "affected_files": [],
                    "affected_lines": [],
                },
            ]
        }
    )

    candidates = parse_hypothesis_response(raw, valid_evidence_ids=frozenset({"trace:0"}))

    assert [candidate.hypothesis for candidate in candidates] == ["Valid candidate."]


def test_rank_hypotheses_calibrates_confidence_and_reassigns_ranks() -> None:
    evidence = make_evidence()
    candidates = [
        ReasoningCandidate(
            hypothesis="Beta lower confidence.",
            explanation="Internal rationale.",
            category="config-error",
            raw_confidence=0.6,
            evidence_references=["trace:0"],
            affected_files=["app/config.py"],
            affected_lines=[],
        ),
        ReasoningCandidate(
            hypothesis="Alpha higher confidence.",
            explanation="Internal rationale.",
            category="config-error",
            raw_confidence=0.9,
            evidence_references=["trace:0", "snippet:0"],
            affected_files=["app/config.py"],
            affected_lines=[("app/config.py", 10, 14)],
        ),
    ]

    hypotheses = rank_hypotheses(
        candidates,
        evidence,
        model_used="fake-reasoner",
        max_hypotheses=2,
        min_confidence=0,
    )

    assert [item.rank for item in hypotheses] == [1, 2]
    assert hypotheses[0].hypothesis == "Alpha higher confidence."
    assert hypotheses[0].model_used == "fake-reasoner"
    assert hypotheses[0].confidence == pytest.approx(0.7978571428571428)
    assert all(0 <= item.confidence <= 1 for item in hypotheses)


def test_rank_hypotheses_uses_deterministic_tie_breakers_and_min_confidence() -> None:
    evidence = make_evidence()
    candidates = [
        ReasoningCandidate(
            hypothesis="zeta tie",
            explanation="Internal rationale.",
            category="config-error",
            raw_confidence=0.5,
            evidence_references=["trace:0"],
            affected_files=[],
            affected_lines=[],
        ),
        ReasoningCandidate(
            hypothesis="alpha tie",
            explanation="Internal rationale.",
            category="config-error",
            raw_confidence=0.5,
            evidence_references=["trace:0"],
            affected_files=[],
            affected_lines=[],
        ),
    ]

    hypotheses = rank_hypotheses(
        candidates,
        evidence,
        model_used="fake-reasoner",
        max_hypotheses=2,
        min_confidence=0.45,
    )

    assert [item.hypothesis for item in hypotheses] == ["alpha tie", "zeta tie"]
    assert calibrate_confidence(candidates[0], evidence, min_confidence=0.99) is None


@pytest.mark.asyncio
async def test_reasoning_engine_uses_provider_and_does_not_mutate_evidence() -> None:
    evidence = make_evidence()
    original_dump = evidence.model_dump(mode="json")
    provider = FakeProvider()
    engine = ReasoningEngine(
        llm_provider=provider,
        config=ReasoningConfig(max_hypotheses=1),
    )

    hypotheses = await engine.generate_hypotheses(ReasoningInput(evidence=evidence))

    assert provider.formats == ["json"]
    assert provider.prompts is not None
    assert "snippet:0" in provider.prompts[0]
    assert len(hypotheses) == 1
    assert hypotheses[0].rank == 1
    assert "trace:0" in hypotheses[0].evidence_references
    assert evidence.model_dump(mode="json") == original_dump


@pytest.mark.asyncio
async def test_reasoning_engine_uses_prompt_helper_and_provider_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = make_evidence()
    provider = FakeProvider()

    def fail_async_client(*args: object, **kwargs: object) -> object:
        pytest.fail("ReasoningEngine must not instantiate HTTP clients")

    def fail_environment(*args: object, **kwargs: object) -> object:
        pytest.fail("ReasoningEngine must not construct Jinja environments")

    def fake_render_prompt(input_evidence: EvidencePack) -> str:
        assert input_evidence is evidence
        return "rendered prompt"

    monkeypatch.setattr(reasoning.httpx, "AsyncClient", fail_async_client)
    monkeypatch.setattr(reasoning, "Environment", fail_environment)
    monkeypatch.setattr(reasoning, "render_reasoning_prompt", fake_render_prompt)

    engine = ReasoningEngine(llm_provider=provider)
    await engine.generate_hypotheses(ReasoningInput(evidence=evidence))

    assert provider.prompts == ["rendered prompt"]
    assert provider.formats == ["json"]


@pytest.mark.asyncio
async def test_reasoning_engine_returns_empty_list_for_parse_failures() -> None:
    engine = ReasoningEngine(llm_provider=FakeProvider(raw_response="{bad"))

    assert await engine.generate_hypotheses(ReasoningInput(evidence=make_evidence())) == []


@pytest.mark.asyncio
async def test_reasoning_engine_propagates_provider_failures() -> None:
    engine = ReasoningEngine(
        llm_provider=FakeProvider(error=ReasoningProviderError("provider unavailable"))
    )

    with pytest.raises(ReasoningProviderError):
        await engine.generate_hypotheses(ReasoningInput(evidence=make_evidence()))


class FakeResponse:
    def __init__(self, data: Mapping[str, object]) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Mapping[str, object]:
        return self._data


class FakeAsyncClient:
    instances: list[FakeAsyncClient] = []
    responses: list[FakeResponse | Exception] = []

    def __init__(self, *, base_url: str, timeout: float) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.posts: list[dict[str, Any]] = []
        self.closed = False
        FakeAsyncClient.instances.append(self)

    async def post(self, url: str, *, json: Mapping[str, object]) -> FakeResponse:
        self.posts.append({"url": url, "json": json})
        response = FakeAsyncClient.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_ollama_provider_reuses_single_async_client_and_closes_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.instances = []
    FakeAsyncClient.responses = [
        FakeResponse({"message": {"content": model_response()}}),
        FakeResponse({"message": {"content": model_response()}}),
    ]
    monkeypatch.setattr(reasoning.httpx, "AsyncClient", FakeAsyncClient)
    provider = OllamaLLMProvider(
        OllamaProviderConfig(
            host="http://localhost:11434",
            model="qwen2.5-coder:7b",
        )
    )

    first = await provider.generate_structured("prompt", response_format="json")
    second = await provider.generate_structured("prompt", response_format="json")
    await provider.aclose()

    assert first == model_response()
    assert second == model_response()
    assert len(FakeAsyncClient.instances) == 1
    assert FakeAsyncClient.instances[0].closed is True
    assert len(FakeAsyncClient.instances[0].posts) == 2
    payload = FakeAsyncClient.instances[0].posts[0]["json"]
    assert payload["format"] is HYPOTHESIS_RESPONSE_SCHEMA


@pytest.mark.asyncio
async def test_ollama_provider_async_context_manager_closes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.instances = []
    FakeAsyncClient.responses = [FakeResponse({"message": {"content": model_response()}})]
    monkeypatch.setattr(reasoning.httpx, "AsyncClient", FakeAsyncClient)

    async with OllamaLLMProvider(
        OllamaProviderConfig(host="http://localhost:11434", model="qwen2.5-coder:7b")
    ) as provider:
        assert (
            await provider.generate_structured("prompt", response_format="json") == model_response()
        )
        assert FakeAsyncClient.instances[0].closed is False

    assert FakeAsyncClient.instances[0].closed is True


@pytest.mark.asyncio
async def test_ollama_provider_retries_and_wraps_transport_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.instances = []
    FakeAsyncClient.responses = [
        httpx.ConnectError("connection failed"),
        httpx.ConnectError("connection failed again"),
        FakeResponse({"response": model_response()}),
    ]
    delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(reasoning.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(reasoning.asyncio, "sleep", fake_sleep)
    provider = OllamaLLMProvider(
        OllamaProviderConfig(
            host="http://localhost:11434",
            model="qwen2.5-coder:7b",
            max_retries=2,
            retry_backoff_seconds=0.25,
        )
    )

    assert await provider.generate_structured("prompt", response_format="json") == model_response()
    assert len(FakeAsyncClient.instances[0].posts) == 3
    assert delays == [0.25, 0.5]

    FakeAsyncClient.responses = [httpx.TimeoutException("timeout")]
    failing_provider = OllamaLLMProvider(
        OllamaProviderConfig(
            host="http://localhost:11434",
            model="qwen2.5-coder:7b",
            max_retries=0,
        )
    )
    with pytest.raises(ReasoningProviderError) as exc_info:
        await failing_provider.generate_structured("prompt", response_format="json")

    assert isinstance(exc_info.value.__cause__, httpx.TimeoutException)


@pytest.mark.asyncio
async def test_ollama_provider_rejects_invalid_response_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.instances = []
    FakeAsyncClient.responses = [FakeResponse({"message": {"content": ""}})]
    monkeypatch.setattr(reasoning.httpx, "AsyncClient", FakeAsyncClient)
    provider = OllamaLLMProvider(
        OllamaProviderConfig(host="http://localhost:11434", model="qwen2.5-coder:7b")
    )

    with pytest.raises(ReasoningProviderError, match="model content"):
        await provider.generate_structured("prompt", response_format="json")

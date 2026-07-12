from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.resources import files
from typing import Final, Literal, Protocol

import httpx
from jinja2 import Environment, Template

from bta.domain import EvidencePack, RootCauseHypothesis

PROMPT_VERSION: Final = "v1"
PROMPT_TEMPLATE_NAME: Final = f"reasoning_hypotheses_{PROMPT_VERSION}.j2"

HYPOTHESIS_RESPONSE_SCHEMA: Final[dict[str, object]] = {
    "type": "object",
    "properties": {
        "hypotheses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hypothesis": {"type": "string"},
                    "explanation": {"type": "string"},
                    "category": {"type": "string"},
                    "confidence": {"type": "number"},
                    "evidence_references": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "affected_files": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "affected_lines": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "prefixItems": [
                                {"type": "string"},
                                {"type": "integer"},
                                {"type": "integer"},
                            ],
                            "minItems": 3,
                            "maxItems": 3,
                        },
                    },
                },
                "required": [
                    "hypothesis",
                    "explanation",
                    "category",
                    "confidence",
                    "evidence_references",
                    "affected_files",
                    "affected_lines",
                ],
            },
        }
    },
    "required": ["hypotheses"],
}


class ReasoningProviderError(Exception):
    """Raised when an LLM provider request fails."""


class ReasoningParseError(Exception):
    """Raised when model output cannot be parsed as structured hypotheses."""


class LLMProvider(Protocol):
    @property
    def model_name(self) -> str:
        """Provider model name."""

    async def generate_structured(
        self,
        prompt: str,
        *,
        response_format: Literal["json"],
    ) -> str:
        """Return raw structured model output."""


@dataclass(frozen=True, slots=True)
class ReasoningConfig:
    max_hypotheses: int = 3
    min_confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.max_hypotheses < 1:
            raise ValueError("max_hypotheses must be positive")
        if not 0 <= self.min_confidence <= 1:
            raise ValueError("min_confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ReasoningInput:
    evidence: EvidencePack


@dataclass(frozen=True, slots=True)
class OllamaProviderConfig:
    host: str
    model: str
    timeout_seconds: float = 60.0
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("host must not be blank")
        if not self.model.strip():
            raise ValueError("model must not be blank")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must not be negative")


@dataclass(frozen=True, slots=True)
class ReasoningCandidate:
    hypothesis: str
    explanation: str
    category: str
    raw_confidence: float
    evidence_references: list[str]
    affected_files: list[str]
    affected_lines: list[tuple[str, int, int]]


class OllamaLLMProvider:
    """Ollama-backed LLM provider with provider-owned HTTP and retry behavior."""

    def __init__(self, config: OllamaProviderConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.host.rstrip("/"),
            timeout=config.timeout_seconds,
        )

    @property
    def model_name(self) -> str:
        return self._config.model

    async def __aenter__(self) -> OllamaLLMProvider:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def generate_structured(
        self,
        prompt: str,
        *,
        response_format: Literal["json"],
    ) -> str:
        if response_format != "json":
            raise ReasoningProviderError(f"unsupported response format: {response_format}")
        payload: dict[str, object] = {
            "model": self._config.model,
            "stream": False,
            "format": HYPOTHESIS_RESPONSE_SCHEMA,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only JSON that matches the requested response schema.",
                },
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": 0},
        }
        data = await self._post_with_retries("/api/chat", payload)
        return self._extract_content(data)

    async def _post_with_retries(
        self,
        url: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        attempts = self._config.max_retries + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                response = await self._client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, Mapping):
                    raise ReasoningProviderError("provider response must be a JSON object")
                return data
            except ReasoningProviderError:
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt == attempts - 1:
                    break
                if self._config.retry_backoff_seconds:
                    await asyncio.sleep(self._retry_delay(attempt))
        raise ReasoningProviderError("Ollama provider request failed") from last_error

    def _retry_delay(self, attempt: int) -> float:
        return self._config.retry_backoff_seconds * (2**attempt)

    def _extract_content(self, data: Mapping[str, object]) -> str:
        message = data.get("message")
        if isinstance(message, Mapping):
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content
        response = data.get("response")
        if isinstance(response, str) and response.strip():
            return response
        raise ReasoningProviderError("Ollama response did not include model content")


class ReasoningEngine:
    """Stateless reasoning engine that turns EvidencePack into hypotheses."""

    def __init__(
        self,
        *,
        llm_provider: LLMProvider,
        config: ReasoningConfig | None = None,
    ) -> None:
        self._llm_provider = llm_provider
        self._config = config or ReasoningConfig()

    async def generate_hypotheses(self, input: ReasoningInput) -> list[RootCauseHypothesis]:
        prompt = render_reasoning_prompt(input.evidence)
        try:
            raw = await self._llm_provider.generate_structured(prompt, response_format="json")
        except ReasoningProviderError:
            raise
        except Exception as exc:
            raise ReasoningProviderError("LLM provider failed") from exc

        try:
            candidates = parse_hypothesis_response(
                raw,
                valid_evidence_ids=valid_evidence_ids(input.evidence),
            )
        except ReasoningParseError:
            return []

        return rank_hypotheses(
            candidates,
            input.evidence,
            model_used=self._llm_provider.model_name,
            max_hypotheses=self._config.max_hypotheses,
            min_confidence=self._config.min_confidence,
        )


def render_reasoning_prompt(evidence: EvidencePack) -> str:
    template = _load_prompt_template()
    return template.render(
        prompt_version=PROMPT_VERSION,
        evidence_items=_prompt_evidence_items(evidence),
        valid_evidence_ids=sorted(valid_evidence_ids(evidence)),
    )


def _load_prompt_template() -> Template:
    template_text = files("bta.prompts").joinpath(PROMPT_TEMPLATE_NAME).read_text(encoding="utf-8")
    environment = Environment(
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    return environment.from_string(template_text)


def parse_hypothesis_response(
    raw: str,
    *,
    valid_evidence_ids: set[str] | frozenset[str],
) -> list[ReasoningCandidate]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReasoningParseError("model output was not valid JSON") from exc

    if not isinstance(data, dict):
        raise ReasoningParseError("model output must be a JSON object")
    items = data.get("hypotheses")
    if not isinstance(items, list):
        raise ReasoningParseError("model output must contain a hypotheses list")

    candidates: list[ReasoningCandidate] = []
    for item in items:
        candidate = _parse_candidate(item, valid_evidence_ids=valid_evidence_ids)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def calibrate_confidence(
    candidate: ReasoningCandidate,
    evidence: EvidencePack,
    *,
    min_confidence: float,
) -> float | None:
    confidence = _clamp(
        0.55 * candidate.raw_confidence
        + 0.20 * evidence.confidence
        + 0.15 * _grounding_ratio(candidate, evidence)
        + 0.10 * _affected_file_signal(candidate)
    )
    if confidence < min_confidence:
        return None
    return confidence


def rank_hypotheses(
    candidates: Sequence[ReasoningCandidate],
    evidence: EvidencePack,
    *,
    model_used: str,
    max_hypotheses: int,
    min_confidence: float,
) -> list[RootCauseHypothesis]:
    scored: list[tuple[float, ReasoningCandidate]] = []
    for candidate in candidates:
        confidence = calibrate_confidence(
            candidate,
            evidence,
            min_confidence=min_confidence,
        )
        if confidence is not None:
            scored.append((confidence, candidate))

    scored.sort(
        key=lambda item: (
            -item[0],
            -len(item[1].evidence_references),
            -len(_affected_files(item[1])),
            _normalize_text(item[1].hypothesis),
        )
    )

    hypotheses: list[RootCauseHypothesis] = []
    for rank, (confidence, candidate) in enumerate(scored[:max_hypotheses], start=1):
        hypotheses.append(
            RootCauseHypothesis(
                rank=rank,
                hypothesis=candidate.hypothesis,
                category=candidate.category,
                confidence=confidence,
                evidence_references=candidate.evidence_references,
                affected_files=_affected_files(candidate),
                affected_lines=candidate.affected_lines,
                model_used=model_used,
            )
        )
    return hypotheses


def valid_evidence_ids(evidence: EvidencePack) -> frozenset[str]:
    values: set[str] = set()
    values.update(f"excerpt:{index}" for index, _ in enumerate(evidence.relevant_excerpts))
    values.update(f"trace:{index}" for index, _ in enumerate(evidence.stack_trace_frames))
    values.update(f"error:{index}" for index, _ in enumerate(evidence.error_signatures))
    values.update(f"file:{index}" for index, _ in enumerate(evidence.file_references))
    values.update(f"snippet:{index}" for index, _ in enumerate(evidence.similar_code_snippets))
    values.update(f"duplicate:{index}" for index, _ in enumerate(evidence.duplicate_candidates))
    values.update(f"related:{index}" for index, _ in enumerate(evidence.related_issues))
    return frozenset(values)


def _parse_candidate(
    value: object,
    *,
    valid_evidence_ids: set[str] | frozenset[str],
) -> ReasoningCandidate | None:
    if not isinstance(value, dict):
        return None
    hypothesis = _required_string(value.get("hypothesis"))
    explanation = _required_string(value.get("explanation"))
    category = _required_string(value.get("category"))
    confidence = _number(value.get("confidence"))
    if hypothesis is None or explanation is None or category is None or confidence is None:
        return None

    return ReasoningCandidate(
        hypothesis=hypothesis,
        explanation=explanation,
        category=category,
        raw_confidence=_clamp(confidence),
        evidence_references=_valid_references(
            value.get("evidence_references"),
            valid_evidence_ids=valid_evidence_ids,
        ),
        affected_files=_valid_affected_files(value.get("affected_files")),
        affected_lines=_valid_affected_lines(value.get("affected_lines")),
    )


def _prompt_evidence_items(evidence: EvidencePack) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for index, excerpt in enumerate(evidence.relevant_excerpts):
        items.append({"id": f"excerpt:{index}", "kind": "Issue excerpt", "content": excerpt})
    for index, frame in enumerate(evidence.stack_trace_frames):
        items.append(
            {
                "id": f"trace:{index}",
                "kind": "Stack frame",
                "content": _format_stack_frame(frame.file, frame.line_number, frame.function_name),
            }
        )
    for index, error in enumerate(evidence.error_signatures):
        items.append({"id": f"error:{index}", "kind": "Error signature", "content": error})
    for index, file_ref in enumerate(evidence.file_references):
        items.append(
            {
                "id": f"file:{index}",
                "kind": "File reference",
                "content": (
                    f"{file_ref.repo_path}:{file_ref.start_line}-{file_ref.end_line}\n"
                    f"{file_ref.content}"
                ),
            }
        )
    for index, snippet in enumerate(evidence.similar_code_snippets):
        symbol = (
            f" {snippet.symbol_type or 'symbol'} {snippet.symbol_name}"
            if snippet.symbol_name
            else ""
        )
        items.append(
            {
                "id": f"snippet:{index}",
                "kind": "Code snippet",
                "content": (
                    f"{snippet.repo_path}:{snippet.start_line}-{snippet.end_line}{symbol}\n"
                    f"{snippet.content}"
                ),
            }
        )
    for index, duplicate in enumerate(evidence.duplicate_candidates):
        items.append(
            {
                "id": f"duplicate:{index}",
                "kind": "Duplicate candidate",
                "content": (
                    f"{duplicate.repo}#{duplicate.issue_number} "
                    f"similarity={duplicate.similarity_score:.3f} {duplicate.summary}"
                ),
            }
        )
    for index, issue in enumerate(evidence.related_issues):
        items.append(
            {
                "id": f"related:{index}",
                "kind": "Related issue",
                "content": (
                    f"{issue.repo}#{issue.issue_number} [{issue.state}] "
                    f"{issue.title} similarity={issue.similarity_score:.3f} {issue.summary}"
                ),
            }
        )
    return items


def _format_stack_frame(
    file: str | None,
    line_number: int | None,
    function_name: str | None,
) -> str:
    location = file or "<unknown>"
    if line_number is not None:
        location = f"{location}:{line_number}"
    if function_name:
        location = f"{location} in {function_name}"
    return location


def _valid_references(
    value: object,
    *,
    valid_evidence_ids: set[str] | frozenset[str],
) -> list[str]:
    if not isinstance(value, list):
        return []
    return _dedupe(
        [
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip() in valid_evidence_ids
        ]
    )


def _valid_affected_files(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return _dedupe([item.strip() for item in value if isinstance(item, str) and item.strip()])


def _valid_affected_lines(value: object) -> list[tuple[str, int, int]]:
    if not isinstance(value, list):
        return []
    lines: list[tuple[str, int, int]] = []
    for item in value:
        if not isinstance(item, list | tuple) or len(item) != 3:
            continue
        repo_path, start_line, end_line = item
        if (
            not isinstance(repo_path, str)
            or not repo_path.strip()
            or not isinstance(start_line, int)
            or not isinstance(end_line, int)
            or start_line < 1
            or end_line < start_line
        ):
            continue
        lines.append((repo_path.strip(), start_line, end_line))
    return list(dict.fromkeys(lines))


def _available_evidence_categories(evidence: EvidencePack) -> set[str]:
    categories: set[str] = set()
    if evidence.relevant_excerpts:
        categories.add("excerpt")
    if evidence.stack_trace_frames:
        categories.add("trace")
    if evidence.error_signatures:
        categories.add("error")
    if evidence.file_references:
        categories.add("file")
    if evidence.similar_code_snippets:
        categories.add("snippet")
    if evidence.duplicate_candidates:
        categories.add("duplicate")
    if evidence.related_issues:
        categories.add("related")
    return categories


def _grounding_ratio(candidate: ReasoningCandidate, evidence: EvidencePack) -> float:
    categories = _available_evidence_categories(evidence)
    if not categories:
        return 0.0
    cited_categories = {
        reference.split(":", maxsplit=1)[0]
        for reference in candidate.evidence_references
        if ":" in reference
    }
    return min(1.0, len(cited_categories & categories) / len(categories))


def _affected_file_signal(candidate: ReasoningCandidate) -> float:
    return 1.0 if candidate.affected_files or candidate.affected_lines else 0.0


def _affected_files(candidate: ReasoningCandidate) -> list[str]:
    values = list(candidate.affected_files)
    values.extend(repo_path for repo_path, _, _ in candidate.affected_lines)
    return _dedupe(values)


def _required_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

import pytest

from bta.ai.patching import (
    PatchCandidate,
    PatchDiffError,
    PatchGenerationConfig,
    PatchGenerationEngine,
    PatchGenerationInput,
    PatchLLMProvider,
    PatchParseError,
    SourceFileContext,
    enforce_max_files,
    parse_patch_response,
    render_patch_prompt,
    validate_unified_diff,
)
from bta.domain import EvidencePack, RootCauseHypothesis

VALID_DIFF = "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-value\n+value or 'fallback'\n"


def make_hypothesis() -> RootCauseHypothesis:
    return RootCauseHypothesis(
        rank=1,
        hypothesis="Missing fallback for a config token raises KeyError.",
        category="config-error",
        confidence=0.82,
        evidence_references=["snippet:0"],
        affected_files=["app.py"],
        affected_lines=[("app.py", 1, 1)],
        model_used="fake-reasoner",
    )


def make_evidence() -> EvidencePack:
    return EvidencePack(
        relevant_excerpts=["Crash when token is missing"],
        error_signatures=["KeyError: token"],
        embedding_model="fake-embedding",
        confidence=0.75,
    )


def patch_response(diff: str = VALID_DIFF) -> str:
    return json.dumps(
        {
            "diff_content": diff,
            "files_modified": ["app.py", "app.py"],
            "commit_message": "fix: handle missing config token",
            "explanation": "Adds a fallback when token is absent.",
        }
    )


def oversized_patch_response() -> str:
    return json.dumps(
        {
            "diff_content": (
                "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-a\n+b\n"
                "--- a/other.py\n+++ b/other.py\n@@ -1 +1 @@\n-c\n+d\n"
            ),
            "files_modified": ["app.py", "other.py"],
            "commit_message": "fix: update two files",
            "explanation": "Updates two files.",
        }
    )


@dataclass(slots=True)
class FakePatchProvider:
    raw_response: str = patch_response()
    model_name: str = "fake-patcher"
    prompts: list[str] | None = None
    formats: list[str] | None = None

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
        return self.raw_response


def test_fake_patch_provider_satisfies_protocol() -> None:
    provider: PatchLLMProvider = FakePatchProvider()

    assert provider.model_name == "fake-patcher"


def test_render_patch_prompt_is_stable_and_uses_source_context() -> None:
    input = PatchGenerationInput(
        hypothesis=make_hypothesis(),
        evidence=make_evidence(),
        source_files=[SourceFileContext(repo_path="app.py", content="value = config['token']")],
    )

    first = render_patch_prompt(input, PatchGenerationConfig())
    second = render_patch_prompt(input, PatchGenerationConfig())

    assert first == second
    assert "Prompt version: v1" in first
    assert "--- app.py" in first
    assert "value = config['token']" in first


def test_parse_patch_response_builds_candidate_and_dedupes_files() -> None:
    candidate = parse_patch_response(patch_response())

    assert candidate == PatchCandidate(
        diff_content=VALID_DIFF,
        files_modified=["app.py"],
        commit_message="fix: handle missing config token",
        explanation="Adds a fallback when token is absent.",
    )


def test_parse_patch_response_rejects_malformed_json_and_missing_fields() -> None:
    with pytest.raises(PatchParseError) as exc_info:
        parse_patch_response("{bad")

    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)

    with pytest.raises(PatchParseError):
        parse_patch_response(json.dumps({"diff_content": VALID_DIFF}))


def test_validate_unified_diff_accepts_shape_and_rejects_invalid_diff() -> None:
    validate_unified_diff(VALID_DIFF)

    with pytest.raises(PatchDiffError):
        validate_unified_diff("")

    with pytest.raises(PatchDiffError):
        validate_unified_diff("--- a/app.py\n+++ b/app.py\n-value\n+value\n")


def test_enforce_max_files_rejects_oversized_candidate() -> None:
    candidate = PatchCandidate(
        diff_content=VALID_DIFF,
        files_modified=["app.py", "other.py"],
        commit_message="fix: update files",
        explanation="Updates files.",
    )

    with pytest.raises(PatchDiffError, match="max_files"):
        enforce_max_files(candidate, max_files=1)


@pytest.mark.asyncio
async def test_patch_generation_engine_returns_patch_draft_and_does_not_mutate_inputs() -> None:
    hypothesis = make_hypothesis()
    evidence = make_evidence()
    original_hypothesis = hypothesis.model_dump(mode="json")
    original_evidence = evidence.model_dump(mode="json")
    provider = FakePatchProvider()
    engine = PatchGenerationEngine(llm_provider=provider)
    input = PatchGenerationInput(
        hypothesis=hypothesis,
        evidence=evidence,
        source_files=[SourceFileContext(repo_path="app.py", content="value = config['token']")],
        issue_number=42,
        generation_attempt=2,
    )

    patch = await engine.generate_patch(input)

    assert provider.formats == ["json"]
    assert provider.prompts is not None
    assert "config-error" in provider.prompts[0]
    assert patch.hypothesis_id == hypothesis.id
    assert patch.diff_content == VALID_DIFF
    assert patch.files_modified == ["app.py"]
    assert patch.branch_name == "bta/fix/issue-42-config-error-attempt-2"
    assert patch.generation_attempt == 2
    assert patch.model_used == "fake-patcher"
    assert hypothesis.model_dump(mode="json") == original_hypothesis
    assert evidence.model_dump(mode="json") == original_evidence


@pytest.mark.asyncio
async def test_patch_generation_engine_rejects_invalid_diff_output() -> None:
    engine = PatchGenerationEngine(
        llm_provider=FakePatchProvider(raw_response=patch_response("nope"))
    )
    input = PatchGenerationInput(
        hypothesis=make_hypothesis(),
        evidence=make_evidence(),
        source_files=[SourceFileContext(repo_path="app.py", content="value = config['token']")],
    )

    with pytest.raises(PatchDiffError):
        await engine.generate_patch(input)


@pytest.mark.asyncio
async def test_patch_generation_engine_rejects_too_many_modified_files() -> None:
    engine = PatchGenerationEngine(
        llm_provider=FakePatchProvider(raw_response=oversized_patch_response()),
        config=PatchGenerationConfig(max_files=1),
    )
    input = PatchGenerationInput(
        hypothesis=make_hypothesis(),
        evidence=make_evidence(),
        source_files=[
            SourceFileContext(repo_path="app.py", content="a"),
            SourceFileContext(repo_path="other.py", content="c"),
        ],
    )

    with pytest.raises(PatchDiffError, match="max_files"):
        await engine.generate_patch(input)

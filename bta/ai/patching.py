from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.resources import files
from typing import Final, Literal, Protocol

from jinja2 import Environment, Template

from bta.domain import EvidencePack, PatchDraft, RootCauseHypothesis

PATCH_PROMPT_VERSION: Final = "v1"
PATCH_PROMPT_TEMPLATE_NAME: Final = f"patch_generation_{PATCH_PROMPT_VERSION}.j2"


class PatchGenerationError(Exception):
    """Raised when patch generation fails."""


class PatchParseError(Exception):
    """Raised when structured patch output cannot be parsed."""


class PatchDiffError(Exception):
    """Raised when generated diff content is not a usable unified diff."""


class PatchLLMProvider(Protocol):
    """Backend-agnostic patch-generation model provider.

    Network-backed implementations should own one reusable client per provider
    instance and expose a clean lifecycle method such as aclose().
    """

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
class PatchGenerationConfig:
    branch_prefix: str = "bta/fix"
    max_files: int = 8
    prompt_version: str = PATCH_PROMPT_VERSION

    def __post_init__(self) -> None:
        if not self.branch_prefix.strip():
            raise ValueError("branch_prefix must not be blank")
        if self.max_files < 1:
            raise ValueError("max_files must be positive")
        if self.prompt_version != PATCH_PROMPT_VERSION:
            raise ValueError(f"unsupported patch prompt version: {self.prompt_version}")


@dataclass(frozen=True, slots=True)
class SourceFileContext:
    repo_path: str
    content: str

    def __post_init__(self) -> None:
        if not self.repo_path.strip():
            raise ValueError("repo_path must not be blank")


@dataclass(frozen=True, slots=True)
class PatchGenerationInput:
    hypothesis: RootCauseHypothesis
    evidence: EvidencePack
    source_files: Sequence[SourceFileContext]
    issue_number: int | None = None
    generation_attempt: int = 1

    def __post_init__(self) -> None:
        if self.issue_number is not None and self.issue_number < 1:
            raise ValueError("issue_number must be positive")
        if self.generation_attempt < 1:
            raise ValueError("generation_attempt must be positive")


@dataclass(frozen=True, slots=True)
class PatchCandidate:
    diff_content: str
    files_modified: list[str]
    commit_message: str
    explanation: str


class PatchGenerationEngine:
    """Stateless LLM-assisted patch generation engine."""

    def __init__(
        self,
        *,
        llm_provider: PatchLLMProvider,
        config: PatchGenerationConfig | None = None,
    ) -> None:
        self._llm_provider = llm_provider
        self._config = config or PatchGenerationConfig()

    async def generate_patch(self, input: PatchGenerationInput) -> PatchDraft:
        prompt = render_patch_prompt(input, self._config)
        try:
            raw = await self._llm_provider.generate_structured(prompt, response_format="json")
            candidate = parse_patch_response(raw)
            validate_unified_diff(candidate.diff_content)
            enforce_max_files(candidate, max_files=self._config.max_files)
        except (PatchParseError, PatchDiffError):
            raise
        except Exception as exc:
            raise PatchGenerationError("patch generation failed") from exc

        return assemble_patch_draft(
            candidate,
            input,
            model_used=self._llm_provider.model_name,
            branch_name=_branch_name(input, self._config),
        )


def render_patch_prompt(input: PatchGenerationInput, config: PatchGenerationConfig) -> str:
    template = _load_patch_template()
    return template.render(
        prompt_version=config.prompt_version,
        max_files=config.max_files,
        hypothesis=input.hypothesis,
        evidence=input.evidence,
        source_files=list(input.source_files)[: config.max_files],
    )


def parse_patch_response(raw: str) -> PatchCandidate:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PatchParseError("patch output was not valid JSON") from exc

    if not isinstance(data, dict):
        raise PatchParseError("patch output must be a JSON object")
    diff_content = _required_diff(data.get("diff_content"))
    commit_message = _required_string(data.get("commit_message"))
    explanation = _required_string(data.get("explanation"))
    files_modified = _string_list(data.get("files_modified"))
    if diff_content is None or commit_message is None or explanation is None or not files_modified:
        raise PatchParseError("patch output is missing required fields")
    return PatchCandidate(
        diff_content=diff_content,
        files_modified=files_modified,
        commit_message=commit_message,
        explanation=explanation,
    )


def validate_unified_diff(diff: str) -> None:
    if not diff.strip():
        raise PatchDiffError("diff_content must not be blank")
    if "--- " not in diff or "+++ " not in diff or "@@" not in diff:
        raise PatchDiffError("diff_content must be a unified diff")
    old_paths = _diff_paths(diff, prefix="--- ")
    new_paths = _diff_paths(diff, prefix="+++ ")
    if not old_paths or not new_paths:
        raise PatchDiffError("diff_content must include file headers")
    if len(old_paths) != len(new_paths):
        raise PatchDiffError("diff_content must include matching old and new file headers")


def enforce_max_files(candidate: PatchCandidate, *, max_files: int) -> None:
    if len(candidate.files_modified) > max_files:
        raise PatchDiffError(
            f"generated patch modifies {len(candidate.files_modified)} files; "
            f"max_files is {max_files}"
        )


def assemble_patch_draft(
    candidate: PatchCandidate,
    input: PatchGenerationInput,
    *,
    model_used: str,
    branch_name: str,
) -> PatchDraft:
    return PatchDraft(
        hypothesis_id=input.hypothesis.id,
        diff_content=candidate.diff_content,
        files_modified=candidate.files_modified,
        branch_name=branch_name,
        commit_message=candidate.commit_message,
        explanation=candidate.explanation,
        generation_attempt=input.generation_attempt,
        model_used=model_used,
    )


def _load_patch_template() -> Template:
    template_text = (
        files("bta.prompts").joinpath(PATCH_PROMPT_TEMPLATE_NAME).read_text(encoding="utf-8")
    )
    environment = Environment(
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    return environment.from_string(template_text)


def _branch_name(input: PatchGenerationInput, config: PatchGenerationConfig) -> str:
    issue_part = f"issue-{input.issue_number}" if input.issue_number else "hypothesis"
    slug = _slug(input.hypothesis.category or input.hypothesis.hypothesis)
    return f"{config.branch_prefix}/{issue_part}-{slug}-attempt-{input.generation_attempt}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "patch"


def _required_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _required_diff(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    if not value.strip():
        return None
    return value


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        stripped = item.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            result.append(stripped)
    return result


def _diff_paths(diff: str, *, prefix: str) -> list[str]:
    paths: list[str] = []
    for line in diff.splitlines():
        if line.startswith(prefix):
            value = line[len(prefix) :].split("\t", maxsplit=1)[0].strip()
            if value:
                paths.append(value)
    return paths

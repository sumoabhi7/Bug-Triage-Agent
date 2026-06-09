from datetime import UTC

import pytest
from pydantic import ValidationError

from bta.domain import (
    CodeSnippet,
    DuplicateCandidate,
    EvidencePack,
    FileReference,
    RelatedIssue,
    StackFrame,
    StackTrace,
)


def test_evidence_pack_supports_nested_retrieval_outputs() -> None:
    frame = StackFrame(file="app.py", line_number=12, function_name="load_config")
    reference = FileReference(
        repo_path="app.py",
        start_line=10,
        end_line=14,
        content="value = cfg[key]",
    )
    snippet = CodeSnippet(
        repo_path="app.py",
        start_line=8,
        end_line=16,
        symbol_name="load_config",
        symbol_type="function",
        content="def load_config(): ...",
        score=0.92,
    )
    duplicate = DuplicateCandidate(
        repo="owner/repo",
        issue_number=7,
        similarity_score=0.88,
        summary="same missing config key",
    )
    related = RelatedIssue(
        repo="owner/repo",
        issue_number=8,
        title="Config crash",
        summary="similar traceback",
        similarity_score=0.81,
        state="open",
    )

    pack = EvidencePack(
        relevant_excerpts=["Crashes when config key is missing"],
        stack_trace_frames=[frame],
        error_signatures=["KeyError"],
        file_references=[reference],
        similar_code_snippets=[snippet],
        duplicate_candidates=[duplicate],
        related_issues=[related],
        embedding_model="all-MiniLM-L6-v2",
        confidence=0.86,
    )

    assert pack.retrieval_timestamp.tzinfo is UTC
    assert pack.stack_trace_frames[0].file == "app.py"
    assert pack.file_references[0].start_line == 10
    assert pack.duplicate_candidates[0].issue_number == 7


def test_evidence_pack_serializes_and_restores() -> None:
    pack = EvidencePack(
        embedding_model="all-MiniLM-L6-v2",
        confidence=0.5,
        stack_trace_frames=[StackFrame(file="app.py", line_number=1)],
    )

    restored = EvidencePack.model_validate(pack.model_dump(mode="json"))

    assert restored == pack


def test_evidence_artifacts_preserve_exact_whitespace() -> None:
    raw_trace = '  Traceback (most recent call last):\n    File "app.py", line 1\n  '
    file_content = "  def load():\n      return config['token']\n  "
    snippet_content = "\n  if value:\n      return value\n"
    log_excerpt = "  ERROR  failed to load config  "

    stack_trace = StackTrace(raw_text=raw_trace, frames=[])
    reference = FileReference(
        repo_path="app.py",
        start_line=1,
        end_line=2,
        content=file_content,
    )
    snippet = CodeSnippet(
        repo_path="app.py",
        start_line=1,
        end_line=2,
        content=snippet_content,
    )
    pack = EvidencePack(
        relevant_excerpts=[log_excerpt],
        file_references=[reference],
        similar_code_snippets=[snippet],
        embedding_model="all-MiniLM-L6-v2",
        confidence=0.5,
    )

    assert stack_trace.raw_text == raw_trace
    assert pack.relevant_excerpts == [log_excerpt]
    assert pack.file_references[0].content == file_content
    assert pack.similar_code_snippets[0].content == snippet_content


def test_evidence_pack_rejects_bad_confidence_and_line_ranges() -> None:
    with pytest.raises(ValidationError):
        EvidencePack(embedding_model="all-MiniLM-L6-v2", confidence=1.1)

    with pytest.raises(ValidationError):
        FileReference(repo_path="app.py", start_line=10, end_line=9, content="bad range")

    with pytest.raises(ValidationError):
        CodeSnippet(repo_path="app.py", start_line=4, end_line=3, content="bad range")

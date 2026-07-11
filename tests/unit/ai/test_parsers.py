from __future__ import annotations

from datetime import UTC, datetime

from bta.ai.parsers import (
    extract_error_messages,
    extract_logs,
    parse_issue,
    parse_issue_metadata,
    parse_source_file,
    parse_stack_traces,
)
from bta.github.service import GitHubIssue


def make_issue(body: str, author: str | None = "octocat") -> GitHubIssue:
    return GitHubIssue(
        id=123,
        number=42,
        title="Crash when config key is missing",
        body=body,
        labels=["bug", "triage"],
        author=author,
        url="https://github.com/acme/widget/issues/42",
        state="open",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
    )


def test_parse_issue_metadata_maps_adapter_issue_to_domain_metadata() -> None:
    metadata = parse_issue_metadata(make_issue("body"))

    assert metadata.github_issue_id == 123
    assert metadata.title == "Crash when config key is missing"
    assert metadata.body == "body"
    assert metadata.labels == ["bug", "triage"]
    assert metadata.author == "octocat"
    assert metadata.url == "https://github.com/acme/widget/issues/42"


def test_parse_issue_metadata_normalizes_missing_author() -> None:
    metadata = parse_issue_metadata(make_issue("body", author=None))

    assert metadata.author == "unknown"
    assert metadata.author != "None"


def test_extract_logs_from_fenced_blocks_and_inline_log_lines() -> None:
    text = """
    ```log
    ERROR failed to load config
    INFO retrying
    ```

    Runtime details:
    WARN falling back to defaults
    """

    logs = extract_logs(text)

    assert "ERROR failed to load config\n    INFO retrying" in logs
    assert "WARN falling back to defaults" in logs


def test_extract_logs_preserves_order_and_removes_duplicates() -> None:
    text = """
    ```log
    ERROR repeated
    ```
    ERROR repeated
    WARN next
    WARN next
    """

    assert extract_logs(text) == ["ERROR repeated", "WARN next"]


def test_parse_python_traceback_into_stack_trace() -> None:
    text = """Traceback (most recent call last):
  File "app.py", line 10, in load
    return config["token"]
  File "runner.py", line 4, in main
    load()
KeyError: 'token'
"""

    traces = parse_stack_traces(text)

    assert len(traces) == 1
    trace = traces[0]
    assert trace.language == "python"
    assert trace.exception_type == "KeyError"
    assert trace.message == "'token'"
    assert [(frame.file, frame.line_number, frame.function_name) for frame in trace.frames] == [
        ("app.py", 10, "load"),
        ("runner.py", 4, "main"),
    ]


def test_parse_multiple_tracebacks_preserves_order() -> None:
    text = """Traceback (most recent call last):
  File "first.py", line 1, in one
    raise ValueError("first")
ValueError: first

Traceback (most recent call last):
  File "second.py", line 2, in two
    raise RuntimeError("second")
RuntimeError: second
"""

    traces = parse_stack_traces(text)

    assert [trace.exception_type for trace in traces] == ["ValueError", "RuntimeError"]
    assert [trace.frames[0].file for trace in traces] == ["first.py", "second.py"]


def test_parse_chained_tracebacks_preserves_exception_order() -> None:
    text = """Traceback (most recent call last):
  File "loader.py", line 3, in load
    int("bad")
ValueError: invalid literal

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "app.py", line 7, in main
    load()
RuntimeError: config failed

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "runner.py", line 9, in run
    main()
KeyError: 'token'
"""

    traces = parse_stack_traces(text)

    assert [trace.exception_type for trace in traces] == ["ValueError", "RuntimeError", "KeyError"]
    assert [trace.frames[0].file for trace in traces] == ["loader.py", "app.py", "runner.py"]


def test_extract_error_messages_finds_common_errors_and_error_logs() -> None:
    text = """
    ERROR failed to start worker
    ValueError: invalid configuration
    AssertionError: expected token
    """

    messages = extract_error_messages(text)

    assert "ERROR failed to start worker" in messages
    assert "ValueError: invalid configuration" in messages
    assert "AssertionError: expected token" in messages


def test_extract_error_messages_preserves_order_dedupes_and_keeps_traceback_errors() -> None:
    text = """ERROR repeated
ERROR repeated
Traceback (most recent call last):
  File "app.py", line 1, in main
    raise ValueError("bad")
ValueError: bad
ValueError: bad
"""

    assert extract_error_messages(text) == ["ERROR repeated", "ValueError: bad"]


def test_parse_issue_combines_metadata_logs_traces_and_errors() -> None:
    issue = make_issue(
        """```output
ERROR bad config
```
Traceback (most recent call last):
  File "app.py", line 1, in <module>
    raise RuntimeError("bad")
RuntimeError: bad
"""
    )

    parsed = parse_issue(issue)

    assert parsed.metadata.github_issue_id == 123
    assert parsed.raw_logs == ["ERROR bad config"]
    assert parsed.stack_traces[0].exception_type == "RuntimeError"
    assert "RuntimeError: bad" in parsed.error_messages


def test_parse_python_source_file_extracts_class_and_function_snippets() -> None:
    content = """class Loader:
    def load(self):
        return "token"

async def run():
    return Loader().load()
"""

    parsed = parse_source_file("app.py", content)

    assert parsed.language == "python"
    names = [snippet.symbol_name for snippet in parsed.snippets]
    assert names == ["Loader", "load", "run"]
    loader = parsed.snippets[0]
    assert loader.symbol_type == "class"
    assert loader.start_line == 1
    assert loader.end_line == 3


def test_parse_unknown_source_file_uses_file_level_snippet() -> None:
    parsed = parse_source_file("config.ini", "[app]\ntoken = missing\n")

    assert parsed.language is None
    assert len(parsed.snippets) == 1
    assert parsed.snippets[0].repo_path == "config.ini"
    assert parsed.snippets[0].start_line == 1
    assert parsed.snippets[0].end_line == 2


def test_parse_blank_unknown_source_file_returns_no_snippets() -> None:
    parsed = parse_source_file("config.ini", "   \n")

    assert parsed.language is None
    assert parsed.snippets == []

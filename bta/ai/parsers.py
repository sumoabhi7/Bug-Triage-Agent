from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from bta.domain import CodeSnippet, IssueMetadata, StackFrame, StackTrace
from bta.github.service import GitHubIssue

FENCED_BLOCK_RE = re.compile(r"```(?P<language>[A-Za-z0-9_-]*)\n(?P<content>.*?)```", re.DOTALL)
LOG_LEVEL_RE = re.compile(r"\b(?:TRACE|DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL)\b")
ERROR_LINE_RE = re.compile(
    r"^(?:[A-Za-z_][\w.]*?(?:Error|Exception|Warning)|AssertionError|RuntimeError|"
    r"TypeError|ValueError|KeyError|ImportError|ModuleNotFoundError):?\s*.*$"
)
FRAME_RE = re.compile(r'^\s*File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<function>.+)$')
PYTHON_EXTENSIONS = {".py", ".pyw"}


@dataclass(frozen=True, slots=True)
class ParsedIssue:
    metadata: IssueMetadata
    raw_logs: list[str]
    stack_traces: list[StackTrace]
    error_messages: list[str]


@dataclass(frozen=True, slots=True)
class ParsedSourceFile:
    repo_path: str
    language: str | None
    snippets: list[CodeSnippet]


def parse_issue(issue: GitHubIssue) -> ParsedIssue:
    body = issue.body
    return ParsedIssue(
        metadata=parse_issue_metadata(issue),
        raw_logs=extract_logs(body),
        stack_traces=parse_stack_traces(body),
        error_messages=extract_error_messages(body),
    )


def parse_issue_metadata(issue: GitHubIssue) -> IssueMetadata:
    return IssueMetadata(
        github_issue_id=issue.id,
        title=issue.title,
        body=issue.body,
        labels=issue.labels,
        author=issue.author or "unknown",
        url=issue.url,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )


def extract_logs(text: str) -> list[str]:
    logs: list[str] = []
    for match in FENCED_BLOCK_RE.finditer(text):
        language = match.group("language").lower()
        content = match.group("content").strip()
        if language in {"log", "logs", "text", "txt", "output"} and content:
            logs.append(content)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and LOG_LEVEL_RE.search(stripped):
            logs.append(stripped)
    return _dedupe(logs)


def extract_error_messages(text: str) -> list[str]:
    messages: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if ERROR_LINE_RE.match(stripped) or re.search(r"\bERROR\b", stripped):
            messages.append(stripped)
    for trace in parse_stack_traces(text):
        if trace.exception_type:
            if trace.message:
                messages.append(f"{trace.exception_type}: {trace.message}")
            else:
                messages.append(trace.exception_type)
    return _dedupe(messages)


def parse_stack_traces(text: str) -> list[StackTrace]:
    traces: list[StackTrace] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if not lines[index].startswith("Traceback (most recent call last):"):
            index += 1
            continue
        block: list[str] = [lines[index]]
        index += 1
        while index < len(lines):
            line = lines[index]
            if line.startswith("Traceback (most recent call last):"):
                break
            if _is_chain_separator(line):
                break
            block.append(line)
            if ERROR_LINE_RE.match(line.strip()):
                index += 1
                break
            if not line.strip() and len(block) > 1:
                index += 1
                break
            index += 1
        traces.append(_parse_python_traceback("\n".join(block)))
    return traces


def detect_language(repo_path: str) -> str | None:
    suffix = _path_suffix(repo_path)
    if suffix in PYTHON_EXTENSIONS:
        return "python"
    if suffix in {".js", ".jsx", ".mjs", ".cjs"}:
        return "javascript"
    if suffix in {".ts", ".tsx"}:
        return "typescript"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix in {".json"}:
        return "json"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    return None


def parse_source_file(repo_path: str, content: str) -> ParsedSourceFile:
    language = detect_language(repo_path)
    if not content.strip():
        return ParsedSourceFile(repo_path=repo_path, language=language, snippets=[])
    if language == "python":
        snippets = _parse_python_source(repo_path, content)
        if snippets:
            return ParsedSourceFile(repo_path=repo_path, language=language, snippets=snippets)
    return ParsedSourceFile(
        repo_path=repo_path,
        language=language,
        snippets=[_file_level_snippet(repo_path, content)],
    )


def _parse_python_traceback(raw_text: str) -> StackTrace:
    frames: list[StackFrame] = []
    exception_type: str | None = None
    message: str | None = None
    for line in raw_text.splitlines():
        frame_match = FRAME_RE.match(line)
        if frame_match:
            frames.append(
                StackFrame(
                    file=frame_match.group("file"),
                    line_number=int(frame_match.group("line")),
                    function_name=frame_match.group("function").strip(),
                )
            )
            continue
        stripped = line.strip()
        if ERROR_LINE_RE.match(stripped):
            exception_type, _, message_text = stripped.partition(":")
            message = message_text.strip() or None
    return StackTrace(
        raw_text=raw_text,
        language="python",
        exception_type=exception_type,
        message=message,
        frames=frames,
    )


def _parse_python_source(repo_path: str, content: str) -> list[CodeSnippet]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    lines = content.splitlines()
    nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
        and getattr(node, "end_lineno", None) is not None
    ]
    nodes.sort(key=lambda item: (item.lineno, item.name))
    snippets: list[CodeSnippet] = []
    for node in nodes:
        end_line = int(node.end_lineno or node.lineno)
        symbol_type = "class" if isinstance(node, ast.ClassDef) else "function"
        snippets.append(
            CodeSnippet(
                repo_path=repo_path,
                start_line=node.lineno,
                end_line=end_line,
                symbol_name=node.name,
                symbol_type=symbol_type,
                content="\n".join(lines[node.lineno - 1 : end_line]),
            )
        )
    return snippets


def _file_level_snippet(repo_path: str, content: str) -> CodeSnippet:
    lines = content.splitlines() or [content]
    return CodeSnippet(
        repo_path=repo_path,
        start_line=1,
        end_line=max(1, len(lines)),
        content=content,
    )


def _path_suffix(repo_path: str) -> str:
    _, dot, suffix = repo_path.rpartition(".")
    if not dot:
        return ""
    return f".{suffix.lower()}"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _is_chain_separator(line: str) -> bool:
    stripped = line.strip()
    return stripped in {
        "During handling of the above exception, another exception occurred:",
        "The above exception was the direct cause of the following exception:",
    }

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from bta.ai.parsers import parse_source_file
from bta.ai.patching import SourceFileContext
from bta.services.exceptions import ScanServiceError
from bta.services.models import ScanRepositoryRequest, ScanRepositoryResult


class RepositoryScanner(Protocol):
    def iter_source_files(self, root: Path) -> Iterable[SourceFileContext]:
        """Yield repository-relative source files and content."""


class FilesystemRepositoryScanner:
    def __init__(self, *, ignored_dirs: frozenset[str] | None = None) -> None:
        self._ignored_dirs = ignored_dirs or frozenset(
            {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
        )

    def iter_source_files(self, root: Path) -> Iterable[SourceFileContext]:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or any(part in self._ignored_dirs for part in path.parts):
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            yield SourceFileContext(repo_path=path.relative_to(root).as_posix(), content=content)


class ScanService:
    def __init__(self, scanner: RepositoryScanner) -> None:
        self._scanner = scanner

    async def scan_repository(self, request: ScanRepositoryRequest) -> ScanRepositoryResult:
        try:
            contexts = list(self._scanner.iter_source_files(request.repo_path))
            parsed = [parse_source_file(context.repo_path, context.content) for context in contexts]
            return ScanRepositoryResult(source_files=parsed, source_contexts=contexts)
        except Exception as exc:
            raise ScanServiceError("repository scan failed") from exc

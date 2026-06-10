from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path, PurePosixPath
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bta.storage.models import ArtifactRecord


class ArtifactStore:
    """Write immutable local artifacts and optionally stage their metadata."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    async def write(
        self,
        *,
        triage_case_id: UUID,
        kind: str,
        content: bytes | str,
        media_type: str = "text/plain",
        analysis_run_id: UUID | None = None,
        patch_draft_id: UUID | None = None,
        suffix: str = ".txt",
        session: AsyncSession | None = None,
    ) -> ArtifactRecord:
        if not kind or "/" in kind or "\\" in kind:
            raise ValueError("kind must be a non-empty path-safe name")
        if not suffix.startswith(".") or "/" in suffix or "\\" in suffix:
            raise ValueError("suffix must be a path-safe extension")
        payload = content.encode() if isinstance(content, str) else content
        digest = hashlib.sha256(payload).hexdigest()
        relative = PurePosixPath(str(triage_case_id), kind, f"{digest}{suffix}")
        destination = self._resolve(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
                raise RuntimeError("existing artifact does not match expected hash")
        else:
            self._atomic_write(destination, payload)
        record = ArtifactRecord(
            triage_case_id=triage_case_id,
            analysis_run_id=analysis_run_id,
            patch_draft_id=patch_draft_id,
            kind=kind,
            relative_path=relative.as_posix(),
            sha256=digest,
            byte_size=len(payload),
            media_type=media_type,
        )
        if session is not None:
            session.add(record)
        return record

    def read(self, relative_path: str) -> bytes:
        return self._resolve(PurePosixPath(relative_path)).read_bytes()

    def _resolve(self, relative: PurePosixPath) -> Path:
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("artifact path must remain within the artifact root")
        resolved = (self._root / Path(*relative.parts)).resolve()
        if not resolved.is_relative_to(self._root):
            raise ValueError("artifact path must remain within the artifact root")
        return resolved

    @staticmethod
    def _atomic_write(destination: Path, payload: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(dir=destination.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

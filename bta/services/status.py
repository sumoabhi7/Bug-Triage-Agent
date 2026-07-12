from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bta.github.service import GitHubAdapter
from bta.services.exceptions import StatusServiceError
from bta.services.models import StatusResult


class StatusService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        github: GitHubAdapter | None = None,
        reasoning_ready: Callable[[], bool] | None = None,
        patch_ready: Callable[[], bool] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._github = github
        self._reasoning_ready = reasoning_ready or (lambda: False)
        self._patch_ready = patch_ready or (lambda: False)

    async def check(self) -> StatusResult:
        try:
            details: dict[str, str] = {}
            database_ok = await self._check_database(details)
            github_ok = self._check_github(details)
            reasoning_provider_ok = self._check_provider(
                details,
                key="reasoning_provider",
                ready=self._reasoning_ready,
            )
            patch_provider_ok = self._check_provider(
                details,
                key="patch_provider",
                ready=self._patch_ready,
            )
            return StatusResult(
                database_ok=database_ok,
                github_ok=github_ok,
                reasoning_provider_ok=reasoning_provider_ok,
                patch_provider_ok=patch_provider_ok,
                details=details,
            )
        except Exception as exc:
            raise StatusServiceError("status check failed") from exc

    async def _check_database(self, details: dict[str, str]) -> bool:
        if self._session_factory is None:
            details["database"] = "not configured"
            return False
        try:
            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))
            details["database"] = "ok"
            return True
        except Exception as exc:
            details["database"] = str(exc)
            return False

    def _check_github(self, details: dict[str, str]) -> bool:
        if self._github is None:
            details["github"] = "not configured"
            return False
        try:
            user = self._github.authenticate()
            details["github"] = user.login
            return True
        except Exception as exc:
            details["github"] = str(exc)
            return False

    def _check_provider(
        self,
        details: dict[str, str],
        *,
        key: str,
        ready: Callable[[], bool],
    ) -> bool:
        try:
            ok = ready()
            details[key] = "ok" if ok else "not configured"
            return ok
        except Exception as exc:
            details[key] = str(exc)
            return False

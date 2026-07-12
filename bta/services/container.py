from __future__ import annotations

import inspect
from collections.abc import Sequence
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any

from bta.services.analyze import AnalyzeService
from bta.services.dedupe import DedupeService
from bta.services.eval import EvalService
from bta.services.fix import FixService
from bta.services.pr import PublishService
from bta.services.scan import ScanService
from bta.services.status import StatusService


@dataclass(slots=True)
class ServiceContainer:
    """Owns fully constructed service dependencies and their lifecycle."""

    analyze: AnalyzeService
    scan: ScanService
    dedupe: DedupeService
    fix: FixService
    publish: PublishService
    status: StatusService
    eval: EvalService
    managed_resources: Sequence[object] = field(default_factory=tuple)

    async def __aenter__(self) -> ServiceContainer:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        for resource in reversed(tuple(self.managed_resources)):
            await _close_resource(resource)


async def _close_resource(resource: object) -> None:
    close = getattr(resource, "aclose", None)
    if close is None:
        close = getattr(resource, "dispose", None)
    if close is None:
        close = getattr(resource, "close", None)
    if close is None:
        return
    result: Any = close()
    if inspect.isawaitable(result):
        await result

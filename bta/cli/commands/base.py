from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

import typer

from bta.config import Settings


class ServiceProvider(Protocol):
    """Placeholder extension point for the future application service layer."""


@dataclass(frozen=True, slots=True)
class CliContext:
    settings: Settings
    services: ServiceProvider | None = None


def get_cli_context(ctx: typer.Context) -> CliContext:
    if not isinstance(ctx.obj, CliContext):
        raise RuntimeError("CLI context has not been initialized")
    return cast(CliContext, ctx.obj)

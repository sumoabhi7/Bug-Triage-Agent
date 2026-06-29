from __future__ import annotations

import typer

from bta.cli.commands.base import get_cli_context


def status(ctx: typer.Context) -> None:
    get_cli_context(ctx)
    typer.echo("Status service is not implemented yet.")

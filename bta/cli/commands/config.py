from __future__ import annotations

import typer

from bta.cli.commands.base import get_cli_context

config_app = typer.Typer(help="Inspect non-sensitive configuration.")


@config_app.command("show")
def show(ctx: typer.Context) -> None:
    settings = get_cli_context(ctx).settings
    rows = {
        "database_url": "configured",
        "database_echo": settings.database_echo,
        "artifact_root": settings.artifact_root,
        "ollama_host": settings.ollama_host,
        "ollama_model": settings.ollama_model,
        "embedding_model": settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimensions,
        "confidence_threshold": settings.confidence_threshold,
        "max_retries": settings.max_retries,
        "retry_initial_seconds": settings.retry_initial_seconds,
        "retry_max_seconds": settings.retry_max_seconds,
        "auto_publish_pr": settings.auto_publish_pr,
        "log_level": settings.log_level,
        "log_format": settings.log_format,
        "github_token_configured": settings.github_token is not None,
    }
    for key, value in rows.items():
        typer.echo(f"{key}: {value}")

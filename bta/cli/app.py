from __future__ import annotations

from collections.abc import Callable

import typer

from bta.cli.commands.base import CliContext, ServiceProvider
from bta.cli.commands.config import config_app
from bta.cli.commands.status import status
from bta.cli.commands.version import version
from bta.config import Settings, configure_logging, get_settings


def create_app(
    *,
    settings_loader: Callable[[], Settings] = get_settings,
    logging_configurer: Callable[[Settings], None] = configure_logging,
    service_provider: ServiceProvider | None = None,
) -> typer.Typer:
    app = typer.Typer(help="GitHub Bug Triage Agent")

    @app.callback()
    def bootstrap(ctx: typer.Context) -> None:
        settings = settings_loader()
        logging_configurer(settings)
        ctx.obj = CliContext(settings=settings, services=service_provider)

    app.command("version")(version)
    app.add_typer(config_app, name="config")
    app.command("status")(status)
    return app

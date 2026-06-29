from __future__ import annotations

from importlib.metadata import (
    PackageNotFoundError,
)
from importlib.metadata import (
    version as package_version,
)

import typer

PACKAGE_NAME = "bug-triage-agent"
FALLBACK_VERSION = "0.1.0"


def get_version() -> str:
    try:
        return package_version(PACKAGE_NAME)
    except PackageNotFoundError:
        return FALLBACK_VERSION


def version() -> None:
    typer.echo(f"{PACKAGE_NAME} {get_version()}")

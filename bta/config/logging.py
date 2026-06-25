from __future__ import annotations

import logging

from bta.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    """Configure process logging from validated settings."""
    if settings.log_format == "json":
        log_format = (
            '{"level":"%(levelname)s","logger":"%(name)s","message":"%(message)s",'
            '"timestamp":"%(asctime)s"}'
        )
    else:
        log_format = "%(levelname)s %(name)s: %(message)s"

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=log_format,
        force=True,
    )

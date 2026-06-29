from collections.abc import Callable
from pathlib import Path

from pydantic import SecretStr
from typer.testing import CliRunner

from bta.cli.app import create_app
from bta.config import Settings

DATABASE_URL = "postgresql+asyncpg://bugtriage:bugtriage@localhost:5432/bugtriage"


def make_settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        database_url=DATABASE_URL,
        github_token=SecretStr("super-secret-token"),
        artifact_root=Path(".bta/test-artifacts"),
    )


def make_app(
    *,
    settings_loader: Callable[[], Settings] = make_settings,
    logging_configurer: Callable[[Settings], None] | None = None,
):
    if logging_configurer is None:

        def logging_configurer(settings: Settings) -> None:
            return None

    return create_app(
        settings_loader=settings_loader,
        logging_configurer=logging_configurer,
    )


def test_cli_help_registers_foundation_commands() -> None:
    result = CliRunner().invoke(make_app(), ["--help"])

    assert result.exit_code == 0
    assert "version" in result.output
    assert "config" in result.output
    assert "status" in result.output
    assert "hello" not in result.output


def test_version_outputs_application_version() -> None:
    result = CliRunner().invoke(make_app(), ["version"])

    assert result.exit_code == 0
    assert "bug-triage-agent" in result.output
    assert "0.1.0" in result.output


def test_config_show_bootstraps_settings_and_logging_without_printing_secrets() -> None:
    calls: list[str] = []
    settings = make_settings()

    def settings_loader() -> Settings:
        calls.append("settings")
        return settings

    def logging_configurer(loaded_settings: Settings) -> None:
        assert loaded_settings is settings
        calls.append("logging")

    result = CliRunner().invoke(
        make_app(
            settings_loader=settings_loader,
            logging_configurer=logging_configurer,
        ),
        ["config", "show"],
    )

    assert result.exit_code == 0
    assert calls == ["settings", "logging"]
    assert "database_url: configured" in result.output
    assert "github_token_configured: True" in result.output
    assert "super-secret-token" not in result.output


def test_status_is_placeholder_until_service_layer_exists() -> None:
    result = CliRunner().invoke(make_app(), ["status"])

    assert result.exit_code == 0
    assert "Status service is not implemented yet." in result.output

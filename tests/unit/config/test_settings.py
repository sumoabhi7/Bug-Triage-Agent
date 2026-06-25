from pathlib import Path

import pytest
from pydantic import ValidationError

from bta.config.settings import Settings

CONFIG_ENV_VARS = (
    "ARTIFACT_ROOT",
    "AUTO_PUBLISH_PR",
    "CONFIDENCE_THRESHOLD",
    "DATABASE_ECHO",
    "DATABASE_URL",
    "EMBEDDING_DIMENSIONS",
    "EMBEDDING_MODEL",
    "GITHUB_TOKEN",
    "LOG_FORMAT",
    "LOG_LEVEL",
    "MAX_RETRIES",
    "OLLAMA_HOST",
    "OLLAMA_MODEL",
    "RETRY_INITIAL_SECONDS",
    "RETRY_MAX_SECONDS",
)

DATABASE_URL = "postgresql+asyncpg://bugtriage:bugtriage@localhost:5432/bugtriage"


@pytest.fixture(autouse=True)
def clear_config_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in CONFIG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def write_env(tmp_path: Path, content: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(content, encoding="utf-8")
    return path


def load_settings(env_file: Path) -> Settings:
    return Settings(_env_file=env_file)  # type: ignore[call-arg]


def test_settings_load_from_env_file_with_defaults(tmp_path: Path) -> None:
    env_file = write_env(
        tmp_path,
        f"""
        DATABASE_URL={DATABASE_URL}
        GITHUB_TOKEN=
        """,
    )

    settings = load_settings(env_file)

    assert settings.database_url == DATABASE_URL
    assert settings.github_token is None
    assert settings.database_echo is False
    assert settings.artifact_root == Path(".bta/artifacts")
    assert settings.ollama_model == "qwen2.5-coder:7b"
    assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.confidence_threshold == 0.75
    assert settings.max_retries == 3
    assert settings.log_level == "INFO"


def test_settings_require_database_url(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "")

    with pytest.raises(ValidationError, match="database_url"):
        load_settings(env_file)


@pytest.mark.parametrize("threshold", ["-0.01", "1.01"])
def test_settings_validate_confidence_threshold(tmp_path: Path, threshold: str) -> None:
    env_file = write_env(
        tmp_path,
        f"""
        DATABASE_URL={DATABASE_URL}
        CONFIDENCE_THRESHOLD={threshold}
        """,
    )

    with pytest.raises(ValidationError, match="confidence_threshold"):
        load_settings(env_file)


@pytest.mark.parametrize(
    "env_content,match",
    [
        ("MAX_RETRIES=-1", "max_retries"),
        ("RETRY_INITIAL_SECONDS=0", "retry_initial_seconds"),
        ("RETRY_INITIAL_SECONDS=5\nRETRY_MAX_SECONDS=1", "retry_max_seconds"),
    ],
)
def test_settings_validate_retry_values(tmp_path: Path, env_content: str, match: str) -> None:
    env_file = write_env(
        tmp_path,
        f"""
        DATABASE_URL={DATABASE_URL}
        {env_content}
        """,
    )

    with pytest.raises(ValidationError, match=match):
        load_settings(env_file)


def test_environment_overrides_env_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = write_env(
        tmp_path,
        f"""
        DATABASE_URL={DATABASE_URL}
        DATABASE_ECHO=false
        ARTIFACT_ROOT=.bta/artifacts
        LOG_LEVEL=INFO
        """,
    )
    override_url = "postgresql+asyncpg://override:override@localhost:5432/override"

    monkeypatch.setenv("DATABASE_URL", override_url)
    monkeypatch.setenv("DATABASE_ECHO", "true")
    monkeypatch.setenv("ARTIFACT_ROOT", "/tmp/bta-artifacts")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = load_settings(env_file)

    assert settings.database_url == override_url
    assert settings.database_echo is True
    assert settings.artifact_root == Path("/tmp/bta-artifacts")
    assert settings.log_level == "DEBUG"


def test_settings_reject_invalid_log_level(tmp_path: Path) -> None:
    env_file = write_env(
        tmp_path,
        f"""
        DATABASE_URL={DATABASE_URL}
        LOG_LEVEL=VERBOSE
        """,
    )

    with pytest.raises(ValidationError, match="log_level"):
        load_settings(env_file)


def test_settings_reject_invalid_log_format(tmp_path: Path) -> None:
    env_file = write_env(
        tmp_path,
        f"""
        DATABASE_URL={DATABASE_URL}
        LOG_FORMAT=xml
        """,
    )

    with pytest.raises(ValidationError, match="log_format"):
        load_settings(env_file)

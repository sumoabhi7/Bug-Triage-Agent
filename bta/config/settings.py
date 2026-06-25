from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import (
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from bta.config.constants import (
    ALLOWED_LOG_FORMATS,
    ALLOWED_LOG_LEVELS,
    DEFAULT_ARTIFACT_ROOT,
    DEFAULT_AUTO_PUBLISH_PR,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_DATABASE_ECHO,
    DEFAULT_EMBEDDING_DIMENSIONS,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_RETRY_INITIAL_SECONDS,
    DEFAULT_RETRY_MAX_SECONDS,
    LogFormat,
    LogLevel,
)


class Settings(BaseSettings):
    """Application configuration loaded from environment and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(min_length=1)
    database_echo: bool = DEFAULT_DATABASE_ECHO

    github_token: SecretStr | None = None

    ollama_host: str = Field(
        default=DEFAULT_OLLAMA_HOST,
        min_length=1,
    )
    ollama_model: str = Field(default=DEFAULT_OLLAMA_MODEL, min_length=1)

    embedding_model: str = Field(default=DEFAULT_EMBEDDING_MODEL, min_length=1)
    embedding_dimensions: int = Field(default=DEFAULT_EMBEDDING_DIMENSIONS, ge=1)

    confidence_threshold: float = Field(default=DEFAULT_CONFIDENCE_THRESHOLD, ge=0, le=1)
    max_retries: int = Field(default=DEFAULT_MAX_RETRIES, ge=0)
    retry_initial_seconds: float = Field(default=DEFAULT_RETRY_INITIAL_SECONDS, gt=0)
    retry_max_seconds: float = Field(default=DEFAULT_RETRY_MAX_SECONDS, gt=0)
    auto_publish_pr: bool = DEFAULT_AUTO_PUBLISH_PR

    artifact_root: Path = DEFAULT_ARTIFACT_ROOT

    log_level: LogLevel = DEFAULT_LOG_LEVEL
    log_format: LogFormat = DEFAULT_LOG_FORMAT

    @field_validator(
        "database_url",
        "ollama_host",
        "ollama_model",
        "embedding_model",
        mode="before",
    )
    @classmethod
    def _strip_required_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("database_url")
    @classmethod
    def _database_url_must_be_postgresql(cls, value: str) -> str:
        if not value.startswith("postgresql"):
            raise ValueError("database_url must use a PostgreSQL SQLAlchemy URL")
        return value

    @field_validator("github_token", mode="before")
    @classmethod
    def _blank_github_token_is_unset(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("artifact_root", mode="before")
    @classmethod
    def _artifact_root_must_not_be_blank(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("artifact_root must not be blank")
            return stripped
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("log_level")
    @classmethod
    def _log_level_must_be_supported(cls, value: LogLevel) -> LogLevel:
        if value not in ALLOWED_LOG_LEVELS:
            raise ValueError("log_level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL")
        return value

    @field_validator("log_format", mode="before")
    @classmethod
    def _normalize_log_format(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("log_format")
    @classmethod
    def _log_format_must_be_supported(cls, value: LogFormat) -> LogFormat:
        if value not in ALLOWED_LOG_FORMATS:
            raise ValueError("log_format must be either console or json")
        return value

    @model_validator(mode="after")
    def _retry_bounds_must_be_ordered(self) -> Settings:
        if self.retry_max_seconds < self.retry_initial_seconds:
            raise ValueError(
                "retry_max_seconds must be greater than or equal to retry_initial_seconds"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

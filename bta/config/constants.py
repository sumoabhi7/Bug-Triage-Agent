from __future__ import annotations

from pathlib import Path
from typing import Literal

LogFormat = Literal["console", "json"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

DEFAULT_ARTIFACT_ROOT = Path(".bta/artifacts")
DEFAULT_AUTO_PUBLISH_PR = False
DEFAULT_CONFIDENCE_THRESHOLD = 0.75
DEFAULT_DATABASE_ECHO = False
DEFAULT_EMBEDDING_DIMENSIONS = 384
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_LOG_FORMAT: LogFormat = "console"
DEFAULT_LOG_LEVEL: LogLevel = "INFO"
DEFAULT_MAX_RETRIES = 3
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b"
DEFAULT_RETRY_INITIAL_SECONDS = 1.0
DEFAULT_RETRY_MAX_SECONDS = 30.0

ALLOWED_LOG_FORMATS: frozenset[LogFormat] = frozenset(("console", "json"))
ALLOWED_LOG_LEVELS: frozenset[LogLevel] = frozenset(
    ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
)

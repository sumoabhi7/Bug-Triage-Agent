# Bug Triage Agent — Codex Context

## Overview

Terminal-first AI bug-triage agent for GitHub repositories.
Pipeline:

```text
GitHub Issue
→ Parsing
→ Retrieval
→ EvidencePack
→ Root Cause Hypothesis
→ Patch Draft
→ Validation
→ Optional PR
```

## The system is designed to be local-first, reproducible, benchmarkable, and evidence-driven.

## Fixed Architectural Decisions

### Workflow

- TriageCase is the canonical workflow object.
- AnalysisRun stores execution history and replay metadata.
- Workflow is state-machine driven.
- Validation occurs before publication.
- Generated patches must be validated in isolated git worktrees.

### AI

- Retrieval and reasoning are separate stages.
- EvidencePack is the only input to reasoning.
- Root-cause hypotheses must be evidence-backed.
- Retrieval results should be reusable and cacheable.

### Storage

- PostgreSQL is the primary database.
- pgvector is the vector search layer.
- SQLAlchemy is the ORM.
- Alembic manages migrations.

### Local Execution

- Ollama is the inference provider.
- Initial model: qwen2.5-coder:7b
- Planned upgrade: qwen3:14b
- Embeddings: sentence-transformers/all-MiniLM-L6-v2

---

## Technology Stack

### Runtime

- Python 3.12
- uv

### CLI

- Typer
- Rich

### Domain

- Pydantic
- pydantic-settings

### Database

- PostgreSQL
- pgvector
- SQLAlchemy
- asyncpg
- psycopg[binary]
- Alembic

### GitHub

- PyGithub
- GitPython

### AI

- Ollama
- sentence-transformers

### Utilities

- httpx
- tenacity
- Jinja2
- python-dotenv

### Quality

- pytest
- pytest-asyncio
- pytest-cov
- ruff
- mypy

---

## Environment Variables

```text
GITHUB_TOKEN
DATABASE_URL
LLM_MODEL
LLM_PROVIDER
EMBEDDING_MODEL
CONFIDENCE_THRESHOLD
AUTO_PUBLISH_PR
LOG_LEVEL
REVIEW_LLM
```

---

## Development Principles

- Keep module responsibilities stable.
- Avoid unnecessary abstraction layers.
- Prefer small, testable functions.
- Keep prompt templates separate from runtime logic.
- Preserve file and module boundaries once established.

# Bug Triage Agent — Codex Instructions

## Project goal

Build a CLI-first Python 3.12 application that triages GitHub issues, extracts stack traces, retrieves relevant repo context, proposes root-cause hypotheses, generates a patch draft, validates the patch in an isolated git worktree, and optionally opens a draft pull request.

## Core architecture rules

- Keep the workflow stateful and explicit.
- Use a single canonical `TriageCase` object across the whole pipeline.
- Keep reasoning separate from retrieval.
- Keep patching separate from validation.
- Never open a PR unless validation passes.
- Prefer small, safe, reviewable changes.
- Preserve the current architecture unless the user explicitly asks for a redesign.

## Required build order

1. Domain models
2. Config and settings
3. CLI skeleton
4. GitHub integration
5. Ollama integration
6. Storage and migrations
7. Retrieval and embeddings
8. Reasoning
9. Patching
10. Verification
11. Publishing
12. Evaluation and polish

## Tech stack rules

- Python 3.12
- uv for dependency and environment management
- Cursor as the IDE
- Ollama for local model inference
- Qwen2.5-Coder 7B initially; Qwen3 14B later
- Typer for CLI
- Rich for terminal output
- Pydantic for domain models and settings
- PyGithub for GitHub API
- GitPython for local git operations
- PostgreSQL with pgvector for storage and semantic search
- sentence-transformers for embeddings
- SQLAlchemy + Alembic for persistence and migrations
- httpx for HTTP calls
- tenacity for retries
- ruff for linting and formatting
- pytest and pytest-asyncio for tests

## Code style

- Prefer small modules and small functions.
- Keep business logic out of CLI handlers.
- Use Pydantic models for all structured data passed between stages.
- Use typed code throughout.
- Use async only when it clearly helps.
- Write code that can be tested without the UI.
- Favor explicit control flow over clever abstractions.

## Safety and correctness rules

- Do not assume a fix without evidence from the issue, logs, or codebase.
- When proposing a patch, include the exact files and lines that justify it.
- If confidence is low, stop at `NEEDS_REVIEW`.
- If the repo has tests, run them after patching.
- If a generated patch fails validation, retry only a small number of times.
- Do not create destructive git changes without asking.

## Output expectations

- Summarize the plan before editing files.
- Prefer minimal, targeted edits.
- Keep generated code consistent with the existing architecture.
- When multiple options exist, choose the simplest one that satisfies the requirements.
- Explain any tradeoffs briefly.

## Current project focus

Build the first working vertical slice:
GitHub issue → parse → retrieve context → root cause hypothesis → patch draft → validation.

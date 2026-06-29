
---

## `ProjectStructure.md`

```md
# Project Structure

> Consolidated layout — CLI, services, and domain remain separated; the rest are merged where the source structure was overly fragmented.


---

# Repository Layout

```text
bug-triage-agent/
├── README.md — project overview, installation steps, architecture summary, workflow notes, and demo guidance for humans and Codex
├── pyproject.toml — uv project config, dependency specification, CLI entry point, and tool configuration for linting, formatting, and testing
├── docker-compose.yml — PostgreSQL + pgvector service definition, local volume setup, and database startup configuration
├── Makefile — shortcuts for install, lint, format, test, db-up, db-migrate, db-down, and reset tasks
├── .env.example — sample environment variables for local development, including tokens, model names, thresholds, and database URL
├── .gitignore — ignores virtualenvs, caches, logs, env files, generated artifacts, and temporary worktrees
│
├── bta/
│   ├── cli/ — user-facing command entry points and thin wrappers around the service layer; keep the foundation now and wire the remaining command behavior later
│   │   ├── main.py — Typer app bootstrap, version setup, and command registration
│   │   └── commands/
│   │       ├── auth.py — GitHub token setup, validation, and auth status reporting
│   │       ├── scan.py — scan a repository’s issues and create triage cases from issue lists
│   │       ├── analyze.py — analyze a single issue deeply and print ranked findings
│   │       ├── dedupe.py — show duplicate clusters and similarity scores
│   │       ├── fix.py — generate or apply a fix from a selected hypothesis
│   │       ├── pr.py — create a draft pull request from a validated patch
│   │       ├── status.py — show triage dashboard, run status, and current workflow state
│   │       └── eval.py — run benchmark evaluation and emit metrics/report summaries
│   │
│   ├── services/ — application use-case layer between CLI and orchestrator; coordinates workflows and delegates to adapters
│   │   ├── auth.py — GitHub token setup and status checks used by the auth command
│   │   ├── analyze.py — analyze a single issue and coordinate the workflow steps
│   │   ├── scan.py — scan repository issues and create triage cases from issue lists
│   │   ├── dedupe.py — show duplicate clusters and similarity scores
│   │   ├── fix.py — generate or apply a fix from a selected hypothesis
│   │   ├── pr.py — create a draft pull request from a validated patch
│   │   ├── status.py — show triage dashboard, run status, and current workflow state
│   │   └── eval.py — run benchmark evaluation and emit metrics/report summaries
│   │
│   ├── orchestrator/ — workflow control, state transitions, retries, and trace capture invoked by services
│   │   ├── state_machine.py — workflow states, transitions, guards, and routing decisions
│   │   ├── triage_orchestrator.py — executes the workflow end-to-end and handles retry logic
│   │   └── workflow_tracer.py — structured trace logging for each run and failure
│   │
│   ├── domain/ — keep unchanged; pure Pydantic workflow models and runtime state objects
│   │   ├── triage_case.py — canonical workflow object for the whole pipeline, including parsed context and downstream results
│   │   ├── evidence_pack.py — retrieval output used by reasoning and persisted as grounded evidence
│   │   ├── hypothesis.py — ranked root-cause hypotheses with confidence and file-line references
│   │   ├── patch_draft.py — candidate patch output, diff content, and generation metadata
│   │   ├── validation_result.py — test/build/lint validation result from isolated worktree execution
│   │   ├── duplicate_group.py — grouped duplicate triage cases with similarity scores, cluster summary, and representative case tracking
│   │   ├── analysis_run.py — execution record, transition history, and trace metadata for replay/debugging
│   │   └── pr_draft.py — draft PR metadata, labels, publication status, and GitHub publication fields
│   │
│   ├── github/ — adapter layer used by services for auth, issue fetch, repo clone, branching, and PR publishing
│   │   └── service.py — unified GitHub adapter for auth, issue fetch, repo clone, branching, and PR publishing
│   │
│   ├── ai/ — domain intelligence components consumed by services and orchestrator
│   │   ├── parsers.py — issue parsing, log parsing, stack-trace parsing, and code parsing from raw issue/repo text
│   │   ├── retrieval.py — embeddings, vector search, duplicate detection, repo context retrieval, and EvidencePack assembly
│   │   ├── reasoning.py — Ollama client, prompt execution, hypothesis generation/ranking, and confidence scoring
│   │   ├── patching.py — unified diff generation, worktree patch application, and remediation planning
│   │   └── verification.py — test/build/lint execution, result capture, and validation aggregation
│   │
│   ├── storage/ — persistence and artifact handling used by services and orchestrator
│   │   ├── database.py — SQLAlchemy async engine and session factory
│   │   ├── models.py — ORM mappings for PostgreSQL tables and relationships
│   │   ├── vector_store.py — pgvector CRUD, embedding persistence, and similarity search
│   │   └── artifacts.py — local cache plus patch, test-output, trace, and workflow artifact storage
│   │
│   ├── evaluation/ — benchmark loading, evaluation execution, metrics, and report generation
│   │   └── benchmark.py — benchmark loading, evaluation execution, metrics, and report generation
│   │
│   ├── prompts/ — Jinja2 prompt templates for the AI layers
│   │   ├── root_cause.j2 — root-cause analysis prompt template
│   │   ├── hypothesis_ranking.j2 — hypothesis ranking prompt template
│   │   ├── patch_generation.j2 — unified diff generation prompt template
│   │   ├── pr_description.j2 — PR body prompt template
│   │   └── confidence_check.j2 — confidence calibration prompt template
│   │
│   └── config/ — pydantic-settings configuration for tokens, models, thresholds, and database URL
│       └── settings.py — pydantic-settings configuration for tokens, models, thresholds, and database URL
│
├── migrations/
│   ├── env.py — Alembic environment bootstrap
│   └── versions/
│       └── 0001_initial.py — vector extension, tables, and HNSW index creation
│
├── benchmarks/
│   └── cases/
│       ├── null_ref_python.json — benchmark case for a null-reference bug with expected behavior
│       ├── race_condition_asyncio.json — benchmark case for an async race bug with expected behavior
│       └── config_missing_key.json — benchmark case for a missing configuration bug with expected behavior
│
└── tests/
    ├── unit/ — pure unit tests for domain models, parsers, and utility logic
    ├── integration/ — tests that require PostgreSQL, pgvector, Ollama, and end-to-end workflow wiring
    └── fixtures/ — sample issues, stack traces, diffs, repo snippets, and other reusable test inputs
# Build Order

> Build from the inside out. Domain models define contracts, storage persists them, services coordinate application use cases, AI layers transform them, orchestration executes workflows, and the CLI exposes them.

---

# Phase 1 — Domain Models

Build first. Every other layer depends on these contracts.

### Files

- `domain/shared.py` — Shared enums, type aliases, metadata models, trace models, and transition models
- `domain/triage_case.py` — Central workflow object passed through the entire pipeline
- `domain/evidence_pack.py` — Retrieval output consumed by reasoning
- `domain/hypothesis.py` — Ranked root-cause hypotheses
- `domain/patch_draft.py` — Generated patch metadata and unified diff storage
- `domain/validation_result.py` — Test/build/lint validation results
- `domain/duplicate_group.py` — Duplicate triage-case clusters
- `domain/analysis_run.py` — Complete workflow execution record
- `domain/pr_draft.py` — Pull request metadata before publication

### Deliverables

- WorkflowState enum
- IssueType enum
- Severity enum
- PRStatus enum
- StateTransition model
- TraceEntry model
- Serialization support
- Validation rules
- Domain round-trip tests

### Tests

- Model validation
- JSON serialization round-trip
- Confidence bound validation
- State transition validation
- Nested model construction

---

# Phase 2 — Infrastructure & Storage

Build persistence before external integrations.

### Files

- `storage/database.py` — SQLAlchemy async engine and session management
- `storage/models.py` — ORM table mappings for all PostgreSQL tables
- `storage/vector_store.py` — pgvector CRUD and similarity search
- `storage/cache.py` — In-memory cache for repeated process-local lookups
- `storage/artifact_store.py` — Cache, traces, patches, and test-output persistence
- `migrations/versions/0001_extensions.py` — PostgreSQL extension setup
- `migrations/versions/0002_storage_schema.py` — PostgreSQL schema, indexes, and constraints
- `migrations/versions/0003_vector_indexes.py` — HNSW vector index creation

### Deliverables

- PostgreSQL running
- pgvector enabled
- Alembic migration working
- Async database session management
- ORM models mapped
- pgvector CRUD and similarity search
- Cache and artifact persistence

### Tests

- Database connectivity
- Migration execution
- Foreign-key validation
- HNSW index creation
- Vector search smoke test
- Cache eviction and TTL behavior
- Artifact storage smoke test

---

# Phase 3 — Configuration

Build environment and application settings before external integrations and CLI wiring.

### Files

- `config/settings.py` — Environment configuration and application settings
- `config/constants.py` — Non-secret defaults and validation constants
- `config/logging.py` — Logging bootstrap and log formatting
- `config/__init__.py` — Public configuration exports

### Deliverables

- Environment loading
- Database URL validation
- GitHub token handling
- Ollama settings
- Embedding settings
- Threshold and retry settings
- Logging bootstrap

### Tests

- Settings loading
- Required field validation
- Threshold validation
- Retry validation
- Environment override behavior
- Logging configuration bootstrap

---

# Phase 4 — CLI Foundation

Build the application entry point before feature implementation.

This phase establishes the public interface of the application without implementing workflow logic.

Only the CLI bootstrap and command surface are implemented during this phase. Business logic is intentionally deferred so that command handlers remain thin and delegate all work to the future Application Service layer.

### Files

- `cli/main.py`
- `cli/app.py`
- `cli/commands/base.py`
- `cli/commands/version.py`
- `cli/commands/config.py`
- `cli/commands/status.py`

### Responsibilities

- Typer application bootstrap
- Command registration
- Configuration loading
- Logging initialization
- Global CLI options
- Common error handling
- Placeholder command entry points

### Deliverables

- Stable CLI command surface
- Configuration bootstrap
- Logging bootstrap
- Help/version support
- Placeholder command handlers

### Tests

- Command registration
- CLI help
- Version output
- Configuration bootstrap
- Logging initialization

---

# Phase 5 — GitHub Integration & Parsing

Build external data ingestion.

### Files

#### `github/service.py`

Responsibilities:

- GitHub authentication
- Repository cloning
- Issue retrieval
- Worktree management
- Branch management
- Pull request publishing

#### `ai/parsers.py`

Responsibilities:

- Issue parsing
- Metadata extraction
- Log extraction
- Stack trace parsing
- Source code parsing

### Deliverables

- Fetch issue from GitHub
- Clone repository
- Create isolated worktrees
- Extract stack traces
- Extract logs and metadata

### Tests

- GitHub API mocking
- Repository cloning
- Worktree creation
- Stack trace parsing accuracy

---

# Phase 6 — Retrieval System

Build evidence gathering before reasoning.

### Files

#### `ai/retrieval.py`

Responsibilities:

- Embedding generation
- Similarity search
- Duplicate detection
- Repository context retrieval
- EvidencePack assembly
- Retrieval confidence scoring

### Deliverables

- Issue embeddings
- Duplicate case detection
- Relevant file retrieval
- Similar code retrieval
- Complete EvidencePack creation

### Tests

- Similarity search quality
- Duplicate clustering
- Retrieval consistency
- EvidencePack generation

---

# Phase 7 — Reasoning System

Build reasoning on top of stable retrieval outputs.

### Files

#### `ai/reasoning.py`

Responsibilities:

- Ollama communication
- Prompt execution
- Root-cause hypothesis generation
- Hypothesis ranking
- Confidence scoring

### Deliverables

- Ranked hypotheses
- Confidence calibration
- Evidence-grounded reasoning
- Top-hypothesis selection

### Tests

- Mock LLM responses
- Ranking correctness
- Confidence threshold validation
- Evidence grounding validation

---

# Phase 8 — Patch Generation & Validation

Build remediation and verification.

### Files

#### `ai/patching.py`

Responsibilities:

- Remediation planning
- Diff generation
- Patch application
- Branch preparation

#### `ai/verification.py`

Responsibilities:

- Test execution
- Build validation
- Lint validation
- Validation aggregation

### Deliverables

- Unified diff generation
- Patch application inside isolated worktrees
- Validation results
- Confidence adjustment after validation

### Tests

- Good patch passes
- Bad patch fails
- Retry loop behavior
- Validation aggregation correctness

---

# Phase 9 — Application Services

Build the application use-case layer after the functional components exist.

The Service Layer owns application use cases but owns no infrastructure.

### Files

- `services/auth.py`
- `services/scan.py`
- `services/analyze.py`
- `services/dedupe.py`
- `services/fix.py`
- `services/pr.py`
- `services/status.py`
- `services/eval.py`

### Responsibilities

- Coordinate GitHub, parsing, retrieval, reasoning, patching, verification, storage, and invoke the Workflow Orchestrator when executing complete workflows.
- Keep CLI handlers thin.
- Implement application use cases.
- Translate CLI requests into workflow execution.

### Deliverables

- AnalyzeService
- ScanService
- DedupeService
- FixService
- PublishService
- StatusService
- EvalService

### Tests

- Service unit tests
- Dependency mocking
- End-to-end use-case tests

---

# Phase 10 — Workflow Orchestration

Connect all lower-level components into a reusable workflow engine.

The Workflow Orchestrator is an internal execution engine invoked by the Application Service layer. It owns workflow execution but is never called directly by the CLI.

### Files

- `orchestrator/state_machine.py` — Workflow states, guards, and transitions
- `orchestrator/triage_orchestrator.py` — Main workflow executor
- `orchestrator/workflow_tracer.py` — Structured execution tracing

### Deliverables

- End-to-end workflow execution
- Retry management
- Error handling
- State persistence
- Audit trail generation
- AnalysisRun creation

### Tests

- Full workflow simulation
- State transition coverage
- Failure recovery scenarios
- Retry-path coverage

---

# Phase 11 — Evaluation & Benchmarking

Build objective measurement after workflow completion.

### Files

#### `evaluation/benchmark.py`

Responsibilities:

- Benchmark loading
- Evaluation execution
- Metrics calculation
- Report generation

### Deliverables

- Benchmark suite
- Precision/recall metrics
- Root-cause similarity scoring
- Evaluation reports

### Tests

- Benchmark execution
- Metrics correctness
- Report generation

---

# Phase 12 — CLI Command Completion

Complete the CLI now that the Application Service layer exists.

This phase wires every command to its corresponding service implementation.

No new business logic is introduced here. The CLI remains a thin presentation layer that delegates every command to its corresponding Application Service.

### Files

- `cli/commands/auth.py`
- `cli/commands/scan.py`
- `cli/commands/analyze.py`
- `cli/commands/dedupe.py`
- `cli/commands/fix.py`
- `cli/commands/pr.py`
- `cli/commands/status.py`
- `cli/commands/eval.py`

### Deliverables

- Fully functional CLI
- Rich output
- Progress indicators
- JSON output mode
- Error reporting

### Tests

- CLI integration tests
- End-to-end workflow tests
- Command output validation

---

# Dependency Chain

```text
Domain
    ↓
Storage
    ↓
Configuration
    ↓
CLI Foundation
    ↓
GitHub + Parsers
    ↓
Retrieval
    ↓
Reasoning
    ↓
Patching
    ↓
Verification
    ↓
Application Services
    ↓
Workflow Orchestration
    ↓
Evaluation
    ↓
Complete CLI
```

---

# Recommended Development Order

1. Domain
2. Storage & Infrastructure
3. Configuration
4. CLI Foundation
5. GitHub Service
6. Parsers
7. Retrieval
8. Reasoning
9. Patching
10. Verification
11. Application Services
12. Workflow Orchestration
13. Evaluation
14. Complete CLI

This order minimizes rework while preserving clean architectural boundaries. The CLI Foundation establishes a stable public interface early, the infrastructure and AI components are implemented independently, the Application Service layer exposes cohesive use cases, and the Workflow Orchestrator remains an internal execution engine responsible only for workflow coordination. The final CLI phase performs only command wiring, ensuring the CLI remains a thin presentation layer throughout the project's lifetime.

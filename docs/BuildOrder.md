# Build Order

> Build from the inside out. Domain models define contracts, storage persists them, services populate them, AI layers transform them, orchestration coordinates them, and the CLI exposes them.

---

# Phase 1 — Domain Models

Build first. Every other layer depends on these contracts.

### Files

* `domain/shared.py` — Shared enums, type aliases, metadata models, trace models, and transition models
* `domain/triage_case.py` — Central workflow object passed through the entire pipeline
* `domain/evidence_pack.py` — Retrieval output consumed by reasoning
* `domain/hypothesis.py` — Ranked root-cause hypotheses
* `domain/patch_draft.py` — Generated patch metadata and unified diff storage
* `domain/validation_result.py` — Test/build/lint validation results
* `domain/duplicate_group.py` — Duplicate triage-case clusters
* `domain/analysis_run.py` — Complete workflow execution record
* `domain/pr_draft.py` — Pull request metadata before publication

### Deliverables

* WorkflowState enum
* IssueType enum
* Severity enum
* PRStatus enum
* StateTransition model
* TraceEntry model
* Serialization support
* Validation rules
* Domain round-trip tests

### Tests

* Model validation
* JSON serialization round-trip
* Confidence bound validation
* State transition validation
* Nested model construction

---

# Phase 2 — Infrastructure & Storage

Build persistence before external integrations.

### Files

* `config/settings.py` — Environment configuration and application settings
* `storage/database.py` — SQLAlchemy async engine and session management
* `storage/models.py` — ORM table mappings for all PostgreSQL tables
* `storage/vector_store.py` — pgvector CRUD and similarity search
* `storage/artifacts.py` — Cache, traces, patches, and test-output persistence
* `migrations/versions/0001_initial.py` — PostgreSQL schema, extensions, indexes, and constraints

### Deliverables

* PostgreSQL running
* pgvector enabled
* Alembic migration working
* Async database session management
* ORM models mapped
* Repository layer for CRUD operations

### Tests

* Database connectivity
* Migration execution
* Foreign-key validation
* HNSW index creation
* Vector search smoke test

---

# Phase 3 — GitHub Integration & Parsing

Build external data ingestion.

### Files

#### `github/service.py`

Responsibilities:

* GitHub authentication
* Issue retrieval
* Repository cloning
* Worktree management
* Branch management
* Pull request publishing

#### `ai/parsers.py`

Responsibilities:

* Issue parsing
* Metadata extraction
* Log extraction
* Stack trace parsing
* Source code parsing

### Deliverables

* Fetch issue from GitHub
* Clone repository
* Create isolated worktrees
* Extract stack traces
* Extract logs and metadata

### Tests

* GitHub API mocking
* Repository cloning
* Worktree creation
* Stack trace parsing accuracy

---

# Phase 4 — Retrieval System

Build evidence gathering before reasoning.

### Files

#### `ai/retrieval.py`

Responsibilities:

* Embedding generation
* Similarity search
* Duplicate detection
* Repository context retrieval
* EvidencePack assembly
* Retrieval confidence scoring

### Deliverables

* Issue embeddings
* Duplicate case detection
* Relevant file retrieval
* Similar code retrieval
* Complete EvidencePack creation

### Tests

* Similarity search quality
* Duplicate clustering
* Retrieval consistency
* EvidencePack generation

---

# Phase 5 — Reasoning System

Build reasoning on top of stable retrieval outputs.

### Files

#### `ai/reasoning.py`

Responsibilities:

* Ollama communication
* Prompt execution
* Root-cause hypothesis generation
* Hypothesis ranking
* Confidence scoring

### Deliverables

* Ranked hypotheses
* Confidence calibration
* Evidence-grounded reasoning
* Top-hypothesis selection

### Tests

* Mock LLM responses
* Ranking correctness
* Confidence threshold validation
* Evidence grounding validation

---

# Phase 6 — Patch Generation & Validation

Build remediation and verification.

### Files

#### `ai/patching.py`

Responsibilities:

* Remediation planning
* Diff generation
* Patch application
* Branch preparation

#### `ai/verification.py`

Responsibilities:

* Test execution
* Build validation
* Lint validation
* Validation aggregation

### Deliverables

* Unified diff generation
* Patch application inside worktree
* Validation results
* Confidence adjustment after validation

### Tests

* Good patch passes
* Bad patch fails
* Retry loop behavior
* Validation aggregation correctness

---

# Phase 7 — Workflow Orchestration

Connect all previous layers into a complete workflow.

### Files

* `orchestrator/state_machine.py` — Workflow states, guards, and transitions
* `orchestrator/triage_orchestrator.py` — Main workflow executor
* `orchestrator/workflow_tracer.py` — Structured execution tracing

### Deliverables

* End-to-end workflow execution
* Retry management
* Error handling
* State persistence
* Audit trail generation
* AnalysisRun creation

### Tests

* Full workflow simulation
* State transition coverage
* Failure recovery scenarios
* Retry-path coverage

---

# Phase 8 — Evaluation & Benchmarking

Build objective measurement after workflow completion.

### Files

#### `evaluation/benchmark.py`

Responsibilities:

* Benchmark loading
* Evaluation execution
* Metrics calculation
* Report generation

### Deliverables

* Benchmark suite
* Precision/recall metrics
* Root-cause similarity scoring
* Evaluation reports

### Tests

* Benchmark execution
* Metrics correctness
* Report generation

---

# Phase 9 — CLI Commands

Expose completed functionality to users.

### Files

* `cli/commands/auth.py`
* `cli/commands/scan.py`
* `cli/commands/analyze.py`
* `cli/commands/dedupe.py`
* `cli/commands/fix.py`
* `cli/commands/pr.py`
* `cli/commands/status.py`
* `cli/commands/eval.py`

### Deliverables

* Complete user-facing interface
* Rich output panels
* JSON output mode
* Error reporting
* Progress indicators

### Tests

* Command integration tests
* End-to-end workflow tests
* CLI output validation

---

# Dependency Chain

```text
Domain
    ↓
Storage
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
Orchestrator
    ↓
Evaluation
    ↓
CLI
```

---

# Recommended Development Order

1. Domain
2. Storage & Infrastructure
3. GitHub Service
4. Parsers
5. Retrieval
6. Reasoning
7. Patching
8. Verification
9. Orchestrator
10. Evaluation
11. CLI

This order minimizes rework and ensures each layer has stable dependencies before implementation begins.

# System Architecture

> 7-layer architecture with explicit workflow orchestration, application services, evidence-first reasoning, isolated patch validation, and PostgreSQL + pgvector persistence.


---

# Layer Diagram

```text
User (Terminal)
      │
      ▼
╔══════════════════════════════════════════════════════════════╗
║           LAYER 1: CLI (Typer + Rich)                       ║
╚═══════════════════════════╦══════════════════════════════════╝
                            │
                            ▼
╔══════════════════════════════════════════════════════════════╗
║          LAYER 2: APPLICATION SERVICES                      ║
║                                                              ║
║  AuthService                                                ║
║  AnalyzeService                                             ║
║  ScanService                                                ║
║  DedupeService                                              ║
║  FixService                                                 ║
║  PublishService                                             ║
║  StatusService                                              ║
║  EvalService                                                ║
╚═══════════════════════════╦══════════════════════════════════╝
                            │
                            ▼
╔══════════════════════════════════════════════════════════════╗
║           LAYER 3: ORCHESTRATOR                             ║
║                                                             ║
║  TriageStateMachine                                         ║
║  TriageOrchestrator                                         ║
║  WorkflowTracer                                             ║
╚═══════════════════════════╦══════════════════════════════════╝
                            │
          ┌─────────────────┴─────────────────┐
          ▼                                   ▼

╔════════════════════╗      ╔══════════════════════════════════╗
║    LAYER 4         ║      ║    LAYER 5: INTELLIGENCE        ║
║    GITHUB          ║      ║                                ║
║                    ║      ║  Parsing                       ║
║  PyGithub          ║─────►║  Retrieval                     ║
║  GitPython         ║      ║  Reasoning                     ║
║                    ║      ║  Patching                      ║
╚════════════════════╝      ║  Verification                  ║
                            ╚══════════════╦═════════════════╝
                                           │
                                           ▼

╔══════════════════════════════════════════════════════════════╗
║                LAYER 6: STORAGE                             ║
║                                                             ║
║ PostgreSQL + pgvector                                       ║
║ SQLAlchemy + Alembic                                        ║
║ HNSW vector index                                           ║
╚═══════════════════════════╦══════════════════════════════════╝
                            │
                            ▼

╔══════════════════════════════════════════════════════════════╗
║               LAYER 7: EVALUATION                           ║
║                                                             ║
║ BenchmarkLoader                                             ║
║ Evaluator                                                   ║
║ Metrics                                                     ║
║ Report Generator                                            ║
╚══════════════════════════════════════════════════════════════╝

---

# Canonical Workflow Objects

## TriageCase

Canonical workflow object.

Every stage reads and writes the same TriageCase instance.

Contains:

* issue metadata
* parsed context
* retrieval output
* hypotheses
* patch drafts
* validation results
* publication metadata

---

## AnalysisRun

Persistent execution record.

Stores:

* workflow trace
* state transitions
* runtime metadata
* timing information
* evaluation inputs

Used for:

* replay
* debugging
* benchmarking
* auditing

---

# Application Services
Use-case boundary between the CLI and the orchestrator.

Application services coordinate end-user actions such as:

auth
analyze
scan
dedupe
fix
publish
status
eval

---

# Intelligence Layer

## Parsing

Input:

```text
GitHub Issue
```

Output:

```text
IssueMetadata
StackTrace
Logs
Error Messages
```

Parsed runtime artifacts remain available on TriageCase and may be persisted through `triage_cases.parsed_context`.

---

## Retrieval

Responsible for:

* embeddings
* vector search
* duplicate detection
* repository context gathering
* EvidencePack assembly

Output:

```text
EvidencePack
```

EvidencePack is persisted and becomes the sole reasoning input.

---

## Reasoning

Responsible for:

* LLM calls
* hypothesis generation
* hypothesis ranking
* confidence scoring

Input:

```text
EvidencePack
```

Output:

```text
list[RootCauseHypothesis]
```

Reasoning never performs retrieval directly.

---

## Patching

Responsible for:

* remediation planning
* diff generation
* patch creation

Output:

```text
PatchDraft
```

---

## Verification

Responsible for:

* tests
* build validation
* lint validation
* result aggregation

Output:

```text
ValidationResult
```

Validation artifacts are persisted.

Worktree paths remain ephemeral runtime state.

---

# Critical Architectural Constraints

## Retrieval and Reasoning Must Remain Separate

Retrieval is cacheable.

Reasoning is not.

This enables:

* incremental indexing
* retrieval benchmarking
* prompt experimentation
* independent evaluation

Reasoning consumes EvidencePack and never performs repository search directly.

---

## Evidence-First Workflow

Every RootCauseHypothesis must be grounded in:

* stack traces
* file references
* code snippets
* duplicate evidence
* retrieved context

Avoid speculative fixes whenever evidence exists.

---

## Isolated Validation

Generated patches must be validated in isolated git worktrees.

Never modify the primary repository checkout directly.

Validation consists of:

* tests
* build checks
* lint checks

Only validated patches may proceed to publication.

---

## Persistence

Persistent storage:

* PostgreSQL
* pgvector
* SQLAlchemy
* Alembic

Primary persistence targets:

* triage_cases
* issue_embeddings
* evidence_packs
* root_cause_hypotheses
* patch_drafts
* validation_results
* pull_requests
* duplicate_groups
* analysis_runs

Vector similarity uses:

```text
all-MiniLM-L6-v2
384 dimensions
cosine similarity
HNSW index
```

---
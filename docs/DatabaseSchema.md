# Database Schema

> PostgreSQL + pgvector persistence layer for workflow state, retrieval, reasoning, patch generation, validation, duplicate detection, telemetry, and evaluation.

---

# Required Extensions

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

## Notes

- UUID primary keys use `gen_random_uuid()` from `pgcrypto`.
- Embeddings use pgvector with cosine similarity search.
- HNSW indexes are used for fast nearest-neighbor retrieval.

---

# Database Design Principles

- `triage_cases` is the canonical persistent record for a GitHub issue.
- Runtime parsing artifacts are stored in `parsed_context`.
- Retrieval output is stored separately as `evidence_packs`.
- Reasoning output is stored separately as `root_cause_hypotheses`.
- Generated patches, validation results, and pull requests are independently persisted.
- Workflow telemetry is stored in `analysis_runs`.
- Flexible structures use JSONB to reduce migration churn.
- Application code validates enums while the database stores them as TEXT.

---

# Central State

## `triage_cases`

Primary persistent record for an issue under analysis.

| column          | type        | description                        |
| --------------- | ----------- | ---------------------------------- |
| id              | UUID        | Primary key                        |
| repo            | TEXT        | Repository in `owner/repo` format  |
| github_issue_id | BIGINT      | GitHub issue identifier            |
| issue_number    | INTEGER     | Repository-local issue number      |
| state           | TEXT        | Current workflow state             |
| issue_type      | TEXT        | Normalized issue type              |
| severity        | TEXT        | Normalized severity                |
| retry_count     | INTEGER     | Patch retry counter                |
| issue_metadata  | JSONB       | GitHub issue metadata              |
| parsed_context  | JSONB       | Logs, stack traces, error messages |
| created_at      | TIMESTAMPTZ | Creation timestamp                 |
| updated_at      | TIMESTAMPTZ | Update timestamp                   |

### Constraints

```text
UNIQUE(repo, github_issue_id)
```

---

# Vector Retrieval

## `issue_embeddings`

Stores embeddings used for retrieval and duplicate detection.

| column         | type        | description          |
| -------------- | ----------- | -------------------- |
| id             | UUID        | Primary key          |
| triage_case_id | UUID        | Related triage case  |
| embedding      | vector(384) | Embedding vector     |
| content_hash   | TEXT        | SHA-256 content hash |
| model_name     | TEXT        | Embedding model      |
| created_at     | TIMESTAMPTZ | Creation timestamp   |

### Index

```sql
CREATE INDEX issue_embeddings_hnsw
    ON issue_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

---

# Retrieval Output

## `evidence_packs`

Persisted retrieval output consumed by reasoning.

| column         | type        | description             |
| -------------- | ----------- | ----------------------- |
| id             | UUID        | Primary key             |
| triage_case_id | UUID        | Related triage case     |
| content        | JSONB       | Serialized EvidencePack |
| confidence     | FLOAT       | Retrieval confidence    |
| model_name     | TEXT        | Retrieval model         |
| created_at     | TIMESTAMPTZ | Creation timestamp      |

### Storage Decision

- One row represents one retrieval snapshot.
- Add `UNIQUE(triage_case_id)` only if a single active snapshot is desired.

---

# Reasoning Output

## `root_cause_hypotheses`

Stores ranked root-cause hypotheses.

| column         | type        | description                   |
| -------------- | ----------- | ----------------------------- |
| id             | UUID        | Primary key                   |
| triage_case_id | UUID        | Related triage case           |
| rank           | INTEGER     | Rank (1 = highest confidence) |
| hypothesis     | TEXT        | Root-cause explanation        |
| category       | TEXT        | Hypothesis category           |
| confidence     | FLOAT       | Confidence score              |
| evidence_refs  | JSONB       | Evidence references           |
| affected_files | JSONB       | Impacted files                |
| affected_lines | JSONB       | Impacted line ranges          |
| model_used     | TEXT        | LLM used                      |
| created_at     | TIMESTAMPTZ | Creation timestamp            |

### Constraints

```text
rank > 0
confidence between 0 and 1
```

---

# Patch Generation

## `patch_drafts`

Stores generated candidate fixes.

| column             | type        | description             |
| ------------------ | ----------- | ----------------------- |
| id                 | UUID        | Primary key             |
| triage_case_id     | UUID        | Related triage case     |
| hypothesis_id      | UUID        | Source hypothesis       |
| diff_content       | TEXT        | Unified diff            |
| files_modified     | JSONB       | Modified files          |
| branch_name        | TEXT        | Generated branch        |
| commit_message     | TEXT        | Proposed commit message |
| explanation        | TEXT        | Patch explanation       |
| generation_attempt | INTEGER     | Retry number            |
| model_used         | TEXT        | LLM used                |
| created_at         | TIMESTAMPTZ | Creation timestamp      |

---

# Validation

## `validation_results`

Stores validation outcomes for patch drafts.

| column           | type        | description           |
| ---------------- | ----------- | --------------------- |
| id               | UUID        | Primary key           |
| patch_draft_id   | UUID        | Related patch draft   |
| tests_passed     | BOOLEAN     | Test status           |
| tests_output     | TEXT        | Test output           |
| build_passed     | BOOLEAN     | Build status          |
| build_output     | TEXT        | Build output          |
| lint_passed      | BOOLEAN     | Lint status           |
| lint_output      | TEXT        | Lint output           |
| overall_passed   | BOOLEAN     | Aggregate result      |
| confidence_delta | FLOAT       | Confidence adjustment |
| validated_at     | TIMESTAMPTZ | Validation timestamp  |

### Notes

- One validation record per patch draft.
- Runtime-only values such as worktree paths are not persisted.

---

# Pull Requests

## `pull_requests`

Stores draft and published PR metadata.

| column           | type        | description         |
| ---------------- | ----------- | ------------------- |
| id               | UUID        | Primary key         |
| triage_case_id   | UUID        | Related triage case |
| patch_draft_id   | UUID        | Related patch       |
| title            | TEXT        | PR title            |
| body             | TEXT        | PR description      |
| base_branch      | TEXT        | Target branch       |
| head_branch      | TEXT        | Source branch       |
| labels           | JSONB       | Labels              |
| github_pr_number | INTEGER     | GitHub PR number    |
| pr_url           | TEXT        | PR URL              |
| status           | TEXT        | Publication status  |
| created_at       | TIMESTAMPTZ | Creation timestamp  |

### Storage Decision

- Multiple rows allow publication history.
- Add `UNIQUE(triage_case_id)` if only one final PR should exist.

---

# Duplicate Detection

## `duplicate_groups`

Stores clusters of triage cases representing the same underlying issue.

| column            | type        | description                |
| ----------------- | ----------- | -------------------------- |
| id                | UUID        | Primary key                |
| primary_case_id   | UUID        | Representative case        |
| member_case_ids   | JSONB       | Cluster member case IDs    |
| similarity_scores | JSONB       | Case ID → similarity score |
| cluster_summary   | TEXT        | Shared root-cause summary  |
| threshold_used    | FLOAT       | Similarity threshold       |
| detected_at       | TIMESTAMPTZ | Detection timestamp        |

---

# Workflow Telemetry

## `analysis_runs`

Stores replayable execution history.

| column               | type        | description              |
| -------------------- | ----------- | ------------------------ |
| id                   | UUID        | Primary key              |
| triage_case_id       | UUID        | Related triage case      |
| model_used           | TEXT        | Reasoning model          |
| embedding_model      | TEXT        | Embedding model          |
| confidence_threshold | FLOAT       | Threshold used           |
| duration_seconds     | FLOAT       | Total runtime            |
| state_transitions    | JSONB       | Serialized state history |
| workflow_trace       | JSONB       | Detailed execution trace |
| final_state          | TEXT        | Terminal workflow state  |
| created_at           | TIMESTAMPTZ | Creation timestamp       |

---

# Evaluation Harness

## `benchmark_cases`

Reference benchmark dataset.

| column                 | type        | description          |
| ---------------------- | ----------- | -------------------- |
| id                     | UUID        | Primary key          |
| repo                   | TEXT        | Repository           |
| github_issue_number    | INTEGER     | Benchmark issue      |
| expected_root_cause    | TEXT        | Expected diagnosis   |
| expected_categories    | JSONB       | Expected categories  |
| expected_duplicates    | JSONB       | Expected duplicates  |
| expected_patch_pattern | TEXT        | Expected patch shape |
| notes                  | TEXT        | Additional notes     |
| created_at             | TIMESTAMPTZ | Creation timestamp   |

---

## `evaluation_results`

Stores benchmark evaluation results.

| column                | type        | description          |
| --------------------- | ----------- | -------------------- |
| id                    | UUID        | Primary key          |
| benchmark_case_id     | UUID        | Related benchmark    |
| analysis_run_id       | UUID        | Related run          |
| root_cause_similarity | FLOAT       | Root-cause accuracy  |
| duplicate_precision   | FLOAT       | Duplicate precision  |
| duplicate_recall      | FLOAT       | Duplicate recall     |
| duplicate_f1          | FLOAT       | Duplicate F1         |
| patch_effectiveness   | FLOAT       | Patch quality        |
| overall_score         | FLOAT       | Aggregate score      |
| evaluated_at          | TIMESTAMPTZ | Evaluation timestamp |

---

# Key Relationships

```text
triage_cases
├── issue_embeddings
├── evidence_packs
├── root_cause_hypotheses
│   └── patch_drafts
│       ├── validation_results
│       └── pull_requests
├── duplicate_groups
└── analysis_runs

benchmark_cases
└── evaluation_results
    └── analysis_runs
```

---

# Storage Rules

- UUIDs use `gen_random_uuid()` from `pgcrypto`.
- Enums are stored as TEXT and validated by application code.
- Flexible structures use JSONB.
- Embeddings use `vector(384)` for compatibility with `all-MiniLM-L6-v2`.
- `triage_cases` stores active workflow state.
- `analysis_runs` stores replayable telemetry and execution history.
- `evidence_packs` and `pull_requests` may be versioned or constrained to one active record per case depending on product requirements.

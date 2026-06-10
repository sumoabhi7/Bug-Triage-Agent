# Workflow State Machine

> Bug triage is non-linear — duplicates short-circuit, low confidence retries, validation loops back

---

# State Flow (θ = confidence threshold, default 0.75)

```text
INGESTED
    ↓
NORMALIZED
    ↓
EXTRACTED
    ↓
RETRIEVED
    ↓
REASONED
    ├──────────────────────────────────────────────┐
    │ confidence ≥ θ AND NOT duplicate             │
    ▼                                              │
PATCH_DRAFTING                                     │
    ↓                                              │
PATCH_VALIDATING                                   │
    ├── validation_passed AND auto_publish=True ──► PUBLISHED
    │
    ├── NOT passed AND retry_count < 3 ───────────► PATCH_DRAFTING
    │                                               (retry loop)
    │
    └── NOT passed AND retry_count ≥ 3 ───────────► NEEDS_REVIEW

REASONED
    └── confidence < θ OR is_duplicate ───────────► NEEDS_REVIEW

Any state
    └── unrecoverable exception ──────────────────► FAILED
```

---

# All States

| state            | description                                                                   |
| ---------------- | ----------------------------------------------------------------------------- |
| INGESTED         | Raw GitHub issue fetched and stored                                           |
| NORMALIZED       | Metadata extracted; issue type and severity assigned                          |
| EXTRACTED        | Logs, stack traces, error messages parsed from body                           |
| RETRIEVED        | Embeddings computed; vector search done; EvidencePack assembled               |
| REASONED         | LLM generated and ranked RootCauseHypotheses                                  |
| PATCH_DRAFTING   | LLM generating unified diff from top-ranked hypothesis                        |
| PATCH_VALIDATING | Patch applied to git worktree; tests, build, and lint running                 |
| PUBLISHED        | Draft PR opened on GitHub with AI-written description                         |
| NEEDS_REVIEW     | Human required: confidence below θ, is duplicate, or retries exhausted        |
| FAILED           | Unrecoverable error — full trace and transition history stored in AnalysisRun |

---

# All Transitions

| from             | to               | condition                                                    |
| ---------------- | ---------------- | ------------------------------------------------------------ |
| INGESTED         | NORMALIZED       | always                                                       |
| NORMALIZED       | EXTRACTED        | always                                                       |
| EXTRACTED        | RETRIEVED        | always                                                       |
| RETRIEVED        | REASONED         | always                                                       |
| REASONED         | PATCH_DRAFTING   | confidence ≥ θ AND NOT is_known_duplicate                    |
| REASONED         | NEEDS_REVIEW     | confidence < θ OR is_known_duplicate                         |
| PATCH_DRAFTING   | PATCH_VALIDATING | always                                                       |
| PATCH_VALIDATING | PUBLISHED        | validation_passed AND auto_publish=True                      |
| PATCH_VALIDATING | PATCH_DRAFTING   | NOT passed AND retry_count < 3 (retry)                       |
| PATCH_VALIDATING | NEEDS_REVIEW     | NOT passed AND retry_count ≥ 3                               |
| Any state        | FAILED           | Unrecoverable exception (GitHub 5xx, Ollama down, disk full) |

---

# Architectural Notes

## State Machine Purpose

The state machine exists because bug triage is not a simple linear pipeline.

A case may:

- Exit early if identified as a duplicate.
- Loop back into patch generation after failed validation.
- Require human review when confidence is below threshold.
- Fail from any state due to infrastructure or runtime errors.

Runtime transition history is maintained on the active TriageCase during execution and persisted through AnalysisRun.state_transitions for storage, replay, and evaluation.

## Confidence Threshold

```text
θ = 0.75 (default)
```

Rules:

```text
confidence ≥ θ
AND
NOT is_known_duplicate
```

→ Continue to patch generation.

```text
confidence < θ
OR
is_known_duplicate
```

→ Route to NEEDS_REVIEW.

## Retry Policy

Maximum retries:

```text
retry_count < 3
```

Failure path:

```text
PATCH_VALIDATING
    ↓
PATCH_DRAFTING
```

After retries exhausted:

```text
PATCH_VALIDATING
    ↓
NEEDS_REVIEW
```

## Failure Handling

Every state may transition to:

```text
FAILED
```

Examples:

- GitHub API 5xx
- Ollama unavailable
- Database unavailable
- Disk full
- Worktree creation failure
- Unexpected unhandled exception

All failure details, workflow traces, and state transitions are stored in:

```text
AnalysisRun.workflow_trace
AnalysisRun.state_transitions
```

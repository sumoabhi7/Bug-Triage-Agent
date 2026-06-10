# Bug Triage Agent — Codex Instructions

## Project Goal

Build a CLI-first Python 3.12 application that:

- Ingests GitHub issues
- Extracts logs and stack traces
- Retrieves repository context
- Generates evidence-backed root-cause hypotheses
- Produces patch drafts
- Validates patches in isolated git worktrees
- Optionally publishes draft pull requests

---

## Documentation

Architecture documentation is available in the `docs/` directory.

Consult only the documents relevant to the current task.

Examples:

- tech stack and basic context of the system → `docs/readme-codex.md`
- Domain models → `docs/CoreDomainModels.md`
- Workflow/state transitions → `docs/WorkflowStateMachine.md`
- Architecture boundaries → `docs/SystemArchitecture.md`
- File layout → `docs/ProjectStructure.md`
- Persistence → `docs/DatabaseSchema.md`
- Planning/build sequencing → `docs/BuildOrder.md`

These documents are the source of truth.

Do not redesign the architecture unless explicitly requested.

---

## Core Constraints

- Use a single canonical `TriageCase`.
- Keep retrieval separate from reasoning.
- Keep patching separate from validation.
- Keep validation separate from publication.
- Never publish a PR unless validation succeeds.
- Preserve architectural boundaries.
- Prefer explicit workflows over hidden abstractions.
- Prefer minimal, reviewable changes.

---

## Workflow States

Allowed states:

- INGESTED
- NORMALIZED
- EXTRACTED
- RETRIEVED
- REASONED
- PATCH_DRAFTING
- PATCH_VALIDATING
- PUBLISHED
- NEEDS_REVIEW
- FAILED

Do not introduce additional workflow states without approval.

---

## Code Expectations

- Prefer typed Python.
- Prefer small modules.
- Prefer small functions.
- Keep business logic out of CLI handlers.
- Keep domain models infrastructure-agnostic.
- Keep AI logic separate from storage logic.
- Keep GitHub logic separate from reasoning logic.
- Write testable code.

---

## Implementation Expectations

Before modifying files:

- summarize the plan
- identify affected files
- mention major tradeoffs

During implementation:

- make focused changes
- avoid unnecessary refactors
- remain consistent with architecture

When multiple solutions exist:

- choose the simplest solution that satisfies requirements.

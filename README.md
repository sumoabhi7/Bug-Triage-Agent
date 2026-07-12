<div align="center">

# Bug Triage Agent

### AI-Powered GitHub Bug Triage, Root Cause Analysis & Automated Patch Generation Platform

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![AsyncIO](https://img.shields.io/badge/Async-First-009688?style=for-the-badge)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-Vector_Search-6E40C9?style=for-the-badge)](https://github.com/pgvector/pgvector)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?style=for-the-badge)](https://www.sqlalchemy.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge)](https://docs.pydantic.dev/)
[![Ollama](https://img.shields.io/badge/Ollama-LLM_Runtime-000000?style=for-the-badge)](https://ollama.com/)
[![GitHub API](https://img.shields.io/badge/GitHub-API-181717?style=for-the-badge&logo=github)](https://docs.github.com/)
[![GitPython](https://img.shields.io/badge/GitPython-Repository_Management-F05032?style=for-the-badge&logo=git)](https://gitpython.readthedocs.io/)
[![HTTPX](https://img.shields.io/badge/HTTPX-Async_Client-0097A7?style=for-the-badge)](https://www.python-httpx.org/)
[![Jinja2](https://img.shields.io/badge/Jinja2-Prompt_Rendering-B41717?style=for-the-badge)](https://jinja.palletsprojects.com/)
[![Pytest](https://img.shields.io/badge/Pytest-Tested-0A9EDC?style=for-the-badge&logo=pytest)](https://pytest.org/)
[![Ruff](https://img.shields.io/badge/Ruff-Linting-D7FF64?style=for-the-badge)](https://docs.astral.sh/ruff/)
[![MyPy](https://img.shields.io/badge/MyPy-Type_Checked-2A6DB2?style=for-the-badge)](https://mypy-lang.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Layered-success?style=for-the-badge)]()
[![Design](https://img.shields.io/badge/Design-DDD-blue?style=for-the-badge)]()
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

### Intelligent Software Engineering through Retrieval-Augmented Reasoning

_A modular AI platform that analyzes GitHub issues, retrieves repository context, generates evidence-grounded root cause hypotheses, proposes code patches, validates them in isolated Git worktrees, and prepares draft pull requests through a layered, production-oriented architecture._

---

</div>

> **Project Status**
>
> This project is currently under active development.
>
> The complete architectural foundation and core AI pipeline have been implemented, while workflow orchestration, end-to-end automation, evaluation, and production deployment components are being completed.

---

# Table of Contents

- [Overview](#overview)
- [Motivation](#motivation)
- [Problem Statement](#problem-statement)
- [Key Objectives](#key-objectives)
- [Core Features](#core-features)
- [Current Implementation Status](#current-implementation-status)
- [System Architecture](#system-architecture)
- [AI Processing Pipeline](#ai-processing-pipeline)
- [Domain Model](#domain-model)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Performance Considerations](#performance-considerations)
- [Roadmap](#roadmap)
- [License](#license)

---

# Overview

Modern software repositories receive thousands of bug reports throughout their lifetime. Although issue trackers simplify collaboration, identifying the actual root cause of a reported problem remains an expensive engineering activity requiring developers to manually:

- inspect issue reports,
- reproduce failures,
- locate relevant source files,
- analyze stack traces,
- search for similar historical issues,
- formulate possible causes,
- implement fixes,
- validate patches,
- and finally prepare pull requests.

For large repositories, this process becomes repetitive, time-consuming, and difficult to scale.

**Bug Triage Agent** explores how recent advances in Large Language Models, Retrieval-Augmented Generation (RAG), semantic vector search, and automated software engineering workflows can be combined into a unified system that assists developers throughout the early stages of the software maintenance lifecycle.

Instead of acting as a generic chatbot, the system follows a structured multi-stage reasoning pipeline that combines deterministic program analysis with LLM-assisted reasoning to produce evidence-grounded outputs suitable for human review.

---

# Motivation

Large Language Models demonstrate impressive reasoning capabilities but often lack sufficient project-specific context to produce reliable software engineering decisions.

Conversely, deterministic static analysis techniques provide precise contextual information but cannot independently infer high-level software behavior or likely root causes.

This project investigates a hybrid architecture where deterministic analysis and probabilistic reasoning complement one another rather than compete.

The overall design emphasizes:

- deterministic preprocessing,
- explicit evidence retrieval,
- grounded reasoning,
- modular service boundaries,
- strict separation of concerns,
- reproducibility,
- extensibility,
- and infrastructure independence.

Rather than treating an LLM as the entire application, the language model becomes one specialized component inside a larger software engineering pipeline.

---

# Problem Statement

Traditional issue triage often requires significant manual effort before meaningful debugging can even begin.

A developer typically needs to:

1. Read the issue report.
2. Interpret logs and stack traces.
3. Identify affected files.
4. Search historical issues.
5. Understand repository structure.
6. Infer possible root causes.
7. Produce candidate fixes.
8. Validate proposed changes.
9. Publish reviewed pull requests.

Many of these activities are repetitive and consume substantial engineering time before any actual implementation work begins.

The objective of Bug Triage Agent is **not** to replace developers, but to automate repetitive analysis while keeping human review central to the development workflow.

---

# Key Objectives

The project is designed around several engineering objectives:

- Automate GitHub issue ingestion and normalization.
- Build structured representations of issue metadata and runtime failures.
- Retrieve repository-specific context through semantic search.
- Ground AI reasoning using deterministic evidence.
- Generate ranked root cause hypotheses.
- Produce candidate code patches from validated hypotheses.
- Verify generated patches inside isolated Git worktrees.
- Prepare draft pull requests after successful validation.
- Maintain a modular architecture that allows components to evolve independently.

---

# Core Features

## Implemented

- GitHub issue ingestion
- Repository interaction layer
- Deterministic issue parsing
- Stack trace extraction
- Error signature extraction
- Repository source parsing
- Vector-based evidence retrieval
- Semantic duplicate detection
- Evidence assembly pipeline
- LLM-assisted root cause reasoning
- Confidence calibration
- Structured hypothesis ranking
- AI-assisted patch generation
- Unified diff validation
- Patch verification
- Isolated Git worktree validation
- Modular application service layer
- PostgreSQL persistence
- pgvector similarity search
- Async-first architecture
- Strong typing with Pydantic
- Comprehensive unit testing

---

## In Progress

- Workflow orchestration
- End-to-end execution pipeline
- CLI command integration
- Evaluation framework
- Automated benchmarking
- Production deployment tooling

---

## Planned

- Multi-provider LLM support
- Configurable inference backends
- Human-in-the-loop approval workflows
- Incremental repository indexing
- Advanced evaluation dashboards
- Performance benchmarking suite
- Observability and telemetry
- Distributed execution support

---

# Current Implementation Status

| Layer                     | Status         |
| ------------------------- | -------------- |
| Domain Models             | ✅ Complete    |
| Database & Persistence    | ✅ Complete    |
| Configuration             | ✅ Complete    |
| GitHub Integration        | ✅ Complete    |
| Parsing Engine            | ✅ Complete    |
| Retrieval Engine          | ✅ Complete    |
| Reasoning Engine          | ✅ Complete    |
| Patch Generation          | ✅ Complete    |
| Patch Verification        | ✅ Complete    |
| Application Service Layer | ✅ Complete    |
| Workflow Orchestration    | 🚧 In Progress |
| CLI Integration           | 🚧 In Progress |
| Evaluation Framework      | 🚧 Planned     |
| Production Deployment     | 🚧 Planned     |

---

# Design Principles

The architecture has been intentionally designed around modern software engineering practices rather than a monolithic AI application.

The system emphasizes:

- **Layered Architecture**
- **Dependency Inversion**
- **Domain-Driven Design**
- **Async-First Programming**
- **Deterministic Processing Pipelines**
- **Evidence-Grounded AI Reasoning**
- **Strong Type Safety**
- **Explicit Dependency Injection**
- **Infrastructure Isolation**
- **Comprehensive Testability**
- **Modular Component Design**
- **Separation of Concerns**

Each subsystem owns a clearly defined responsibility and communicates through typed domain models instead of infrastructure-specific objects, allowing implementations to evolve independently without affecting higher-level application logic.

---

# System Architecture

Bug Triage Agent follows a layered architecture in which each layer owns a single responsibility and communicates only through well-defined domain models.

Unlike monolithic AI applications that tightly couple prompts, business logic, persistence, and infrastructure, every major subsystem in Bug Triage Agent can evolve independently.

The system combines deterministic software engineering techniques with LLM-assisted reasoning while maintaining strict separation between application logic, infrastructure, AI inference, and persistence.

---

## High-Level Architecture

```text
                            GitHub Repository
                                   │
                                   ▼
                     GitHub Integration Layer
                                   │
                                   ▼
                     Parsing & Normalization Layer
                                   │
                                   ▼
                         Retrieval Engine (RAG)
                                   │
                                   ▼
                    Evidence-Grounded Reasoning
                                   │
                                   ▼
                      Patch Generation Engine
                                   │
                                   ▼
                    Verification & Validation
                                   │
                                   ▼
                       Application Services
                                   │
                                   ▼
                       Workflow Orchestrator
                                   │
                                   ▼
                      GitHub Draft Pull Request
```

Every stage transforms structured inputs into richer domain representations rather than passing around raw infrastructure objects.

---

# Layered Architecture

The project is organized into independent architectural layers.

Each layer has a well-defined responsibility and exposes only typed interfaces to higher layers.

```text
CLI
        │
        ▼
Application Services
        │
        ▼
AI Engines
        │
        ▼
Infrastructure
        │
        ▼
Persistence
        │
        ▼
Domain Models
```

---

## Domain Layer

The Domain Layer defines the canonical business objects used throughout the system.

It contains no database code, networking logic, AI implementation details, or framework-specific abstractions.

Responsibilities include:

- workflow state
- issue metadata
- evidence
- hypotheses
- patches
- validation
- pull request metadata
- analysis history

The remainder of the system depends on these domain models rather than directly interacting with external infrastructure.

This separation allows infrastructure implementations to change without affecting business logic.

---

## Storage Layer

The persistence layer provides durable storage for workflow execution and semantic retrieval.

Responsibilities include:

- PostgreSQL persistence
- pgvector similarity search
- ORM mappings
- transaction management
- workflow history
- analysis replay
- retrieval embeddings

The AI pipeline never directly manipulates database infrastructure.

Persistence decisions remain outside the reasoning process and are coordinated through application services.

---

## GitHub Integration Layer

This layer encapsulates all communication with GitHub.

Responsibilities include:

- authentication
- issue retrieval
- repository cloning
- worktree management
- branch creation
- push operations
- draft pull request publication

No business logic or AI reasoning resides here.

The GitHub layer simply translates between GitHub APIs and internal domain objects.

---

## Parsing Layer

The parsing subsystem transforms raw repository and issue data into structured information.

Responsibilities include:

- issue normalization
- metadata extraction
- stack trace parsing
- error extraction
- language detection
- repository parsing
- source snippet extraction

This stage is completely deterministic and does not invoke language models.

The goal is to maximize structured information before AI reasoning begins.

---

## Retrieval Layer

The Retrieval Engine performs semantic repository search using deterministic evidence gathering.

Its responsibilities include:

- embedding generation
- vector similarity search
- duplicate detection
- contextual source selection
- evidence assembly
- retrieval confidence estimation

Rather than asking the language model to inspect an entire repository, Retrieval constructs a focused Evidence Pack containing only the information most relevant to the reported issue.

This dramatically reduces context size while improving reasoning quality.

---

## Reasoning Layer

The Reasoning Engine is responsible for evidence-grounded hypothesis generation.

Instead of reasoning directly over raw repositories, it consumes only the Evidence Pack produced during retrieval.

Responsibilities include:

- prompt rendering
- structured inference
- hypothesis parsing
- confidence calibration
- evidence grounding
- deterministic ranking

The reasoning layer never communicates with GitHub, the database, repository parsers, or validation infrastructure.

Its only input is structured evidence.

---

## Patch Generation Layer

Once the strongest hypothesis has been identified, Patch Generation constructs a candidate software fix.

Responsibilities include:

- prompt rendering
- structured patch generation
- unified diff parsing
- patch validation
- draft assembly

The generated patch remains an isolated proposal.

No source code is modified during this phase.

---

## Verification Layer

Verification validates generated patches inside isolated Git worktrees.

Responsibilities include:

- patch application
- build execution
- test execution
- lint execution
- type checking
- validation aggregation

Verification never generates patches or reasons about software.

It simply determines whether a proposed patch satisfies configured validation steps.

---

## Application Service Layer

Application Services coordinate complete use cases by composing lower-level engines.

Examples include:

- issue analysis
- repository scanning
- duplicate lookup
- patch generation
- validation
- draft publication

Services own transaction boundaries, dependency composition, and persistence while remaining independent of presentation concerns.

---

## Workflow Orchestration Layer

The orchestrator coordinates long-running workflows and manages state transitions.

Responsibilities include:

- workflow progression
- retry policies
- failure handling
- publication gating
- execution lifecycle
- human-review routing

The orchestrator intentionally remains separate from application services to keep business workflows explicit and testable.

---

# End-to-End AI Pipeline

The complete processing pipeline follows a deterministic sequence before invoking language models.

```text
GitHub Issue
      │
      ▼
Metadata Extraction
      │
      ▼
Log Parsing
      │
      ▼
Stack Trace Parsing
      │
      ▼
Repository Parsing
      │
      ▼
Embedding Generation
      │
      ▼
Semantic Retrieval
      │
      ▼
Evidence Assembly
      │
      ▼
LLM Reasoning
      │
      ▼
Hypothesis Ranking
      │
      ▼
Patch Generation
      │
      ▼
Patch Verification
      │
      ▼
Draft Pull Request
```

The AI model is intentionally introduced only after deterministic preprocessing has completed.

This design minimizes hallucination risk while maximizing the amount of structured context available to downstream reasoning.

---

# Retrieval-Augmented Reasoning

Instead of relying solely on a language model, the platform follows a Retrieval-Augmented Reasoning workflow.

The reasoning engine operates exclusively on curated evidence assembled by the Retrieval layer.

This evidence may include:

- issue metadata
- relevant issue excerpts
- parsed stack frames
- extracted error signatures
- repository file references
- semantically related source snippets
- duplicate issue candidates

Because reasoning is grounded in deterministic evidence rather than unrestricted repository context, hypotheses remain explainable and traceable to their supporting information.

---

# Workflow State Machine

Bug triage is inherently non-linear.

Some issues require immediate human review, some are detected as duplicates, and others enter iterative patch validation loops.

The workflow therefore follows an explicit state machine rather than a simple linear pipeline.

```text
INGESTED
    │
    ▼
NORMALIZED
    │
    ▼
EXTRACTED
    │
    ▼
RETRIEVED
    │
    ▼
REASONED
    │
    ├──────────────► NEEDS_REVIEW
    │
    ▼
PATCH_DRAFTING
    │
    ▼
PATCH_VALIDATING
    │
    ├──────────────► PATCH_DRAFTING
    │
    ├──────────────► NEEDS_REVIEW
    │
    ▼
PUBLISHED
```

The explicit state model enables:

- deterministic workflow progression
- reproducible execution
- retry management
- auditability
- execution replay
- future distributed orchestration

---

# Design Philosophy

Bug Triage Agent was designed around a simple principle:

> **Use deterministic software engineering wherever possible, and use AI only where probabilistic reasoning provides clear value.**

Instead of allowing the language model to control the application, every stage constrains AI through structured inputs, explicit contracts, deterministic preprocessing, and strongly typed outputs.

The architecture therefore emphasizes:

- deterministic preprocessing
- explicit evidence grounding
- modular AI components
- dependency inversion
- infrastructure independence
- reproducibility
- explainability
- extensibility

This philosophy makes the platform suitable not only as a research prototype, but also as a foundation for production-oriented AI-assisted software engineering workflows.

---

# Core Domain Model

The Domain Layer represents the canonical language of the system.

Every subsystem communicates through these domain models rather than infrastructure-specific objects, ensuring that business logic remains independent of databases, APIs, language models, and presentation layers.

Each model is immutable in purpose, strongly typed, and designed around a single responsibility.

Unlike ORM entities or API DTOs, domain objects describe **what the system knows**, not **how it stores or transports that information**.

---

## Domain Workflow

```text
GitHub Issue
      │
      ▼
IssueMetadata
      │
      ▼
TriageCase
      │
      ▼
EvidencePack
      │
      ▼
RootCauseHypothesis
      │
      ▼
PatchDraft
      │
      ▼
ValidationResult
      │
      ▼
PRDraft
```

The domain evolves progressively as each AI subsystem enriches the information available for the current issue.

---

## Triage Case

The **Triage Case** is the central domain object representing a complete software issue throughout its lifecycle.

It accumulates progressively richer information as execution advances through the workflow.

Rather than passing independent objects between layers, the Triage Case acts as the canonical workflow state.

It contains:

- normalized issue metadata
- parsed runtime artifacts
- retrieval results
- reasoning outputs
- generated patches
- validation reports
- publication metadata
- workflow history

Each subsystem enriches the case without depending on the implementation details of previous stages.

---

## Evidence Pack

The Evidence Pack represents the complete contextual snapshot used by the reasoning engine.

Rather than allowing the language model unrestricted repository access, retrieval assembles a carefully curated evidence package containing only information relevant to the reported issue.

Typical evidence includes:

- relevant issue excerpts
- parsed stack frames
- extracted error signatures
- repository file references
- semantically similar code snippets
- duplicate issue candidates
- retrieval confidence

This makes reasoning both explainable and reproducible.

---

## Root Cause Hypothesis

Reasoning does not attempt to produce a single definitive answer.

Instead, it generates multiple competing hypotheses supported by explicit evidence.

Each hypothesis includes:

- natural-language explanation
- normalized category
- calibrated confidence
- evidence references
- affected files
- affected line ranges
- originating model metadata

Hypotheses are ranked deterministically before patch generation begins.

---

## Patch Draft

Patch Generation transforms the highest-ranked hypothesis into a proposed software modification.

The resulting Patch Draft represents a structured proposal rather than an immediately applied code change.

A draft contains:

- unified Git diff
- modified files
- branch metadata
- commit message
- generation attempt
- explanatory summary

Patch generation remains isolated from repository mutation and publication.

---

## Validation Result

Every generated patch must pass deterministic validation before publication.

Validation captures:

- patch application outcome
- build execution
- automated tests
- linting
- static analysis
- confidence adjustment

Validation results provide objective signals that complement the probabilistic outputs produced during reasoning.

---

## Pull Request Draft

Successful validation produces a draft Pull Request ready for publication.

The publication stage assembles:

- title
- description
- branch metadata
- labels
- publication status

Publishing remains a controlled workflow step rather than an automatic side effect of successful reasoning.

---

# Technology Stack

The project combines modern AI tooling with established software engineering technologies.

Rather than optimizing for a specific framework, technologies were selected based on modularity, reliability, and long-term maintainability.

| Category             | Technologies          |
| -------------------- | --------------------- |
| Programming Language | Python 3.12           |
| Data Validation      | Pydantic v2           |
| Database             | PostgreSQL            |
| Vector Database      | pgvector              |
| ORM                  | SQLAlchemy 2.x        |
| GitHub Integration   | PyGithub              |
| Git Operations       | GitPython             |
| LLM Runtime          | Ollama                |
| Embedding Models     | Sentence Transformers |
| HTTP Client          | HTTPX                 |
| Prompt Rendering     | Jinja2                |
| Testing              | Pytest                |
| Static Analysis      | MyPy                  |
| Linting              | Ruff                  |
| Version Control      | Git                   |

---

# Architectural Characteristics

The system has been intentionally designed around several architectural qualities.

## Modular

Each subsystem owns a single responsibility and exposes a well-defined interface.

Replacing or extending one layer should require minimal changes elsewhere.

---

## Strongly Typed

Business objects, requests, responses, and configuration are all represented through strongly typed models.

This reduces ambiguity and improves maintainability.

---

## Async First

External operations such as GitHub communication, database access, LLM inference, and validation workflows are designed around asynchronous execution.

This enables efficient coordination of long-running operations.

---

## Backend Agnostic

The core AI engines depend on provider abstractions rather than concrete implementations.

This allows future support for multiple inference backends without modifying business logic.

Examples include:

- Ollama
- OpenAI-compatible APIs
- Anthropic
- Gemini
- Amazon Bedrock
- Azure OpenAI
- Local inference servers

---

## Infrastructure Independent

Business logic never depends directly on:

- HTTP frameworks
- databases
- terminal interfaces
- GitHub APIs
- language model implementations

Instead, infrastructure is introduced only at composition boundaries.

---

## Testable

Every major subsystem is designed around dependency injection and protocol-oriented abstractions.

This enables deterministic unit testing without requiring:

- GitHub access
- databases
- language models
- external services

---

# Repository Structure

```text
Bug-Triage-Agent
│
├── bta
│   ├── ai
│   │   ├── parsers.py
│   │   ├── retrieval.py
│   │   ├── reasoning.py
│   │   ├── patching.py
│   │   └── verification.py
│   │
│   ├── config
│   │
│   ├── domain
│   │
│   ├── github
│   │
│   ├── prompts
│   │
│   ├── services
│   │
│   ├── storage
│   │
│   └── cli
│
├── tests
│   ├── unit
│   └── integration
│
├── docs
│
├── pyproject.toml
│
└── README.md
```

The repository organization intentionally mirrors the architectural boundaries of the system, allowing developers to navigate features according to responsibilities rather than implementation details.

---

# Project Modules

## Domain

Defines the canonical business objects shared across every subsystem.

---

## Storage

Responsible for persistence, vector search, and workflow history.

---

## GitHub

Provides repository management, issue ingestion, worktree handling, and draft pull request publication.

---

## AI

Contains the complete AI pipeline:

- Parsing
- Retrieval
- Reasoning
- Patch Generation
- Verification

Each stage operates independently and communicates through typed domain objects.

---

## Services

Implements application use cases by orchestrating interactions between AI engines, storage, and infrastructure while remaining presentation agnostic.

---

## CLI

Provides the user-facing command-line interface built on top of the application service layer.

---

# Dependency Direction

The project follows a unidirectional dependency graph.

```text
CLI
        │
        ▼
Services
        │
        ▼
AI Engines
        │
        ▼
GitHub / Storage
        │
        ▼
Domain
```

Lower layers never depend on higher layers.

This ensures:

- independent testing
- easier maintenance
- simpler refactoring
- clearer architectural boundaries

---

# Configuration Philosophy

Configuration is centralized and explicit.

Runtime settings are supplied during application composition rather than being accessed throughout the codebase.

This approach provides several advantages:

- easier testing
- reproducible execution
- environment independence
- simplified dependency injection
- cleaner service boundaries

Secrets such as API keys and access tokens are intentionally kept outside the repository and loaded only through runtime configuration.

---

# Engineering Principles

Throughout development the project follows several engineering principles.

- Single Responsibility Principle
- Dependency Inversion
- Explicit Composition
- Domain-Driven Design
- Infrastructure Isolation
- Deterministic Processing
- Evidence-Grounded AI
- Async Resource Management
- Strong Typing
- Comprehensive Testing
- Clean Architecture
- Extensibility by Design

Rather than treating AI as the application itself, the project treats language models as one specialized component inside a broader software engineering architecture built around explicit contracts, deterministic preprocessing, and modular system design.

---

# Development Roadmap

The project is being developed incrementally with each architectural layer designed, implemented, tested, and validated independently before integration. This approach keeps the system modular, maintainable, and easier to reason about.

---

## Completed

### Core Architecture

- [x] Domain Layer
- [x] Configuration System
- [x] PostgreSQL Persistence Layer
- [x] pgvector Semantic Storage
- [x] GitHub Integration Layer
- [x] Parsing Engine
- [x] Retrieval Engine
- [x] Evidence-Grounded Reasoning Engine
- [x] Patch Generation Engine
- [x] Patch Verification Engine
- [x] Application Service Layer

---

## Currently In Progress

- [ ] Workflow Orchestrator
- [ ] CLI Integration
- [ ] End-to-End Pipeline Integration

---

## Planned

- [ ] Multiple LLM Provider Support
- [ ] OpenAI-Compatible Provider Factory
- [ ] Anthropic Provider
- [ ] Google Gemini Provider
- [ ] Amazon Bedrock Provider
- [ ] Human-in-the-Loop Review Workflow
- [ ] Automated Benchmarking Framework
- [ ] Evaluation Dashboard
- [ ] Web Interface
- [ ] Distributed Execution
- [ ] Multi-Repository Support

---

# Current Capabilities

The current implementation provides the following capabilities:

- GitHub Issue Ingestion
- Issue Metadata Normalization
- Stack Trace Parsing
- Error Signature Extraction
- Repository Source Parsing
- Semantic Embedding Generation
- pgvector Similarity Search
- Duplicate Issue Detection
- Contextual Evidence Retrieval
- Evidence-Grounded Root Cause Analysis
- Structured LLM Reasoning
- Root Cause Ranking
- LLM-Assisted Patch Draft Generation
- Unified Diff Validation
- Patch Verification
- Build/Test/Lint/Type-Check Validation
- Draft Pull Request Preparation
- Dependency Injection Based Service Layer
- Async Resource Management
- Structured Persistence Pipeline

---

# Planned Features

The current architecture has been intentionally designed to support future expansion without major architectural changes.

Future work includes:

- Multi-Provider LLM Support
- Provider Factory
- OpenAI-Compatible API Support
- Anthropic Claude Support
- Gemini Support
- Amazon Bedrock Support
- MCP Tool Integration
- Autonomous Multi-Agent Workflow
- Automatic Repository Cloning
- Incremental Repository Indexing
- Incremental Embedding Updates
- Human Review Dashboard
- Continuous Evaluation Framework
- Execution Metrics Dashboard
- REST API
- Web Dashboard
- Distributed Worker Execution
- Multi-Repository Orchestration
- Enterprise Authentication

---

# Testing

The project follows a test-first development workflow.

Every architectural layer is independently tested before integration with the remaining system.

---

## Verification Pipeline

Every implementation is verified using:

- Pytest Unit Tests
- Integration Tests (where applicable)
- Ruff Linting
- Ruff Formatting
- MyPy Static Type Checking

---

## Current Test Status

- **129 Unit Tests Passing**
- **1 Integration Test Skipped (Environment Dependent)**

---

## Test Coverage Includes

- Domain Models
- Configuration
- Storage
- GitHub Integration
- Parsing
- Retrieval
- Reasoning
- Patch Generation
- Verification
- Application Services
- Dependency Injection
- Async Resource Management
- Provider Isolation
- Error Handling
- Persistence
- Transaction Boundaries

---

## Every new architectural layer is required to satisfy all verification checks before being considered complete.

# Quality Assurance

Code quality is enforced through automated tooling and strict architectural boundaries.

---

## Static Analysis

- MyPy
- Ruff
- Pydantic Validation

---

## Testing

- Pytest
- Async Testing
- Dependency Injection Testing
- Mock-Based Infrastructure Testing

---

## Engineering Standards

- Strong Typing
- Dependency Inversion
- Explicit Composition
- Stateless AI Components
- Deterministic Processing
- Immutable Configuration
- Structured Error Handling
- Explicit Resource Ownership

---

## Every completed implementation phase must pass all quality gates before development proceeds to the next architectural layer.

# Performance Considerations

The system architecture emphasizes efficient execution while maintaining deterministic and reproducible behavior.

Key design considerations include:

- Asynchronous I/O throughout infrastructure boundaries
- Semantic retrieval using pgvector
- Retrieval-Augmented Reasoning to minimize LLM context size
- Evidence-first processing before language model inference
- Stateless AI engines
- Provider reuse through long-lived clients
- Explicit transaction boundaries
- Dependency injection instead of global state
- Structured prompt rendering
- Efficient vector similarity search

## The architecture has been designed to scale horizontally as additional repositories, providers, and orchestration capabilities are introduced.

# Security Considerations

Security has been considered throughout the architecture even though the project is currently focused on local execution.

Current design principles include:

- Secrets are never committed to the repository.
- Runtime configuration is separated from source code.
- API keys are loaded through environment configuration.
- Language model providers are abstracted behind protocols.
- Patch generation is isolated from repository mutation.
- Patch publication requires successful validation.
- Verification occurs inside isolated Git worktrees.
- GitHub publication is policy-gated.
- Infrastructure dependencies are isolated from business logic.

## The project intentionally avoids embedding credentials, repository-specific configuration, or sensitive runtime information within the codebase.

# Current Limitations

This project is under active development.

The current implementation intentionally focuses on establishing a robust architectural foundation before expanding into additional functionality.

Current limitations include:

- Local Ollama is the only implemented LLM backend.
- Workflow orchestration is not yet implemented.
- CLI integration is still in progress.
- Automated benchmark execution has not been completed.
- Human review workflows are not yet available.
- Multi-provider inference is planned but not implemented.
- Distributed execution is not yet supported.
- Web interface has not yet been developed.
- Performance benchmarking will be added after full pipeline completion.

---

# Future Vision

The long-term objective of Bug Triage Agent is to evolve into a production-oriented autonomous software engineering assistant capable of supporting real-world development workflows.

Future capabilities include:

- Autonomous issue triage
- Repository-wide semantic understanding
- Multi-provider language model support
- Continuous repository indexing
- Automated patch generation
- Patch verification
- Human-supervised review workflows
- Draft Pull Request publication
- Benchmark-driven evaluation
- Distributed execution
- Multi-repository analysis
- Extensible plugin architecture
- Enterprise deployment support

Rather than replacing developers, the goal is to reduce repetitive engineering work while providing transparent, evidence-grounded, and verifiable AI-assisted software maintenance.# Future Vision

The long-term objective of Bug Triage Agent is to evolve into a production-oriented autonomous software engineering assistant capable of supporting real-world development workflows.

Future capabilities include:

- Autonomous issue triage
- Repository-wide semantic understanding
- Multi-provider language model support
- Continuous repository indexing
- Automated patch generation
- Patch verification
- Human-supervised review workflows
- Draft Pull Request publication
- Benchmark-driven evaluation
- Distributed execution
- Multi-repository analysis
- Extensible plugin architecture
- Enterprise deployment support

## Rather than replacing developers, the goal is to reduce repetitive engineering work while providing transparent, evidence-grounded, and verifiable AI-assisted software maintenance.

# License

This project is licensed under the **MIT License**.

## See the `LICENSE` file for complete license information.

# Acknowledgements

This project builds upon the excellent work of the open-source community.

Core technologies used include:

- Python
- PostgreSQL
- pgvector
- SQLAlchemy
- PyGithub
- GitPython
- Ollama
- Sentence Transformers
- Jinja2
- HTTPX
- Pydantic
- Pytest
- Ruff
- MyPy

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import VECTOR  # type: ignore[import-untyped]
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from bta.domain import (
    AnalysisRun,
    DuplicateGroup,
    EvidencePack,
    IssueMetadata,
    IssueType,
    PatchDraft,
    PRDraft,
    RootCauseHypothesis,
    Severity,
    StackTrace,
    StateTransition,
    TriageCase,
    ValidationResult,
)
from bta.domain.shared import PRStatus, WorkflowState

JsonObject = dict[str, Any]


def _json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def content_hash(value: Any) -> str:
    payload = json.dumps(_json(value), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TriageCaseRecord(TimestampMixin, Base):
    __tablename__ = "triage_cases"
    __table_args__ = (
        CheckConstraint("issue_number > 0", name="ck_triage_cases_issue_number_positive"),
        CheckConstraint("retry_count >= 0", name="ck_triage_cases_retry_count_nonnegative"),
        UniqueConstraint("repo", "issue_number", name="uq_triage_cases_repo_issue_number"),
        Index("ix_triage_cases_repo_state", "repo", "state"),
        Index(
            "uq_triage_cases_repo_github_issue_id",
            "repo",
            "github_issue_id",
            unique=True,
            postgresql_where=text("github_issue_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    repo: Mapped[str] = mapped_column(Text, nullable=False)
    github_issue_id: Mapped[int | None] = mapped_column(BigInteger)
    issue_number: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    issue_type: Mapped[str | None] = mapped_column(String(32))
    severity: Mapped[str | None] = mapped_column(String(32))
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    issue_metadata: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
    parsed_context: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )

    embeddings: Mapped[list[IssueEmbeddingRecord]] = relationship(
        back_populates="triage_case", cascade="all, delete-orphan"
    )
    evidence_packs: Mapped[list[EvidencePackRecord]] = relationship(
        back_populates="triage_case", cascade="all, delete-orphan"
    )
    hypotheses: Mapped[list[RootCauseHypothesisRecord]] = relationship(
        back_populates="triage_case", cascade="all, delete-orphan"
    )
    patch_drafts: Mapped[list[PatchDraftRecord]] = relationship(
        back_populates="triage_case", cascade="all, delete-orphan"
    )
    pull_requests: Mapped[list[PullRequestRecord]] = relationship(
        back_populates="triage_case", cascade="all, delete-orphan"
    )
    analysis_runs: Mapped[list[AnalysisRunRecord]] = relationship(
        back_populates="triage_case", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list[ArtifactRecord]] = relationship(
        back_populates="triage_case", cascade="all, delete-orphan"
    )

    @classmethod
    def from_domain(cls, case: TriageCase) -> TriageCaseRecord:
        validate_case_provenance(case)
        record = cls(
            id=case.id,
        )
        return record.apply_domain(case)

    def apply_domain(self, case: TriageCase) -> TriageCaseRecord:
        """Update the canonical case projection without replacing history rows."""
        if self.id != case.id:
            raise ValueError("cannot apply a different triage case to an existing record")
        validate_case_provenance(case)
        self.repo = case.repo
        self.github_issue_id = case.issue_metadata.github_issue_id
        self.issue_number = case.issue_number
        self.state = case.state.value
        self.issue_type = case.issue_type.value if case.issue_type else None
        self.severity = case.severity.value if case.severity else None
        self.retry_count = case.retry_count
        self.issue_metadata = _json(case.issue_metadata)
        self.parsed_context = {
            "raw_logs": case.raw_logs,
            "stack_traces": [_json(item) for item in case.stack_traces],
            "error_messages": case.error_messages,
        }
        return self


class IssueEmbeddingRecord(TimestampMixin, Base):
    __tablename__ = "issue_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "triage_case_id", "model_name", "content_hash", name="uq_issue_embeddings_identity"
        ),
        Index("ix_issue_embeddings_case_model", "triage_case_id", "model_name"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    triage_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("triage_cases.id", ondelete="CASCADE"), nullable=False
    )
    embedding: Mapped[list[float]] = mapped_column(VECTOR(384), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    triage_case: Mapped[TriageCaseRecord] = relationship(back_populates="embeddings")


class EvidencePackRecord(TimestampMixin, Base):
    __tablename__ = "evidence_packs"
    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_evidence_packs_confidence"),
        UniqueConstraint(
            "triage_case_id", "model_name", "content_hash", name="uq_evidence_packs_identity"
        ),
        Index(
            "ix_evidence_packs_case_retrieved",
            "triage_case_id",
            text("retrieval_timestamp DESC"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    triage_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("triage_cases.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[JsonObject] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieval_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    triage_case: Mapped[TriageCaseRecord] = relationship(back_populates="evidence_packs")
    hypotheses: Mapped[list[RootCauseHypothesisRecord]] = relationship(
        back_populates="evidence_pack"
    )

    @classmethod
    def from_domain(cls, case_id: UUID, pack: EvidencePack) -> EvidencePackRecord:
        return cls(
            triage_case_id=case_id,
            content=_json(pack),
            confidence=pack.confidence,
            model_name=pack.embedding_model,
            content_hash=content_hash(pack),
            retrieval_timestamp=pack.retrieval_timestamp,
        )

    def to_domain(self) -> EvidencePack:
        return EvidencePack.model_validate(self.content)


class RootCauseHypothesisRecord(TimestampMixin, Base):
    __tablename__ = "root_cause_hypotheses"
    __table_args__ = (
        CheckConstraint("rank > 0", name="ck_hypotheses_rank_positive"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_hypotheses_confidence"),
        Index("ix_hypotheses_case_rank", "triage_case_id", "rank"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    triage_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("triage_cases.id", ondelete="CASCADE"), nullable=False
    )
    evidence_pack_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_packs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    evidence_references: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    affected_files: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    affected_lines: Mapped[list[list[Any]]] = mapped_column(JSONB, nullable=False)
    model_used: Mapped[str] = mapped_column(Text, nullable=False)
    triage_case: Mapped[TriageCaseRecord] = relationship(back_populates="hypotheses")
    evidence_pack: Mapped[EvidencePackRecord] = relationship(back_populates="hypotheses")
    patch_drafts: Mapped[list[PatchDraftRecord]] = relationship(back_populates="hypothesis")

    @classmethod
    def from_domain(
        cls, case_id: UUID, evidence_pack_id: UUID, item: RootCauseHypothesis
    ) -> RootCauseHypothesisRecord:
        return cls(
            id=item.id,
            triage_case_id=case_id,
            evidence_pack_id=evidence_pack_id,
            rank=item.rank,
            hypothesis=item.hypothesis,
            category=item.category,
            confidence=item.confidence,
            evidence_references=item.evidence_references,
            affected_files=item.affected_files,
            affected_lines=[list(line) for line in item.affected_lines],
            model_used=item.model_used,
        )

    def to_domain(self) -> RootCauseHypothesis:
        return RootCauseHypothesis.model_validate(
            {
                "id": self.id,
                "rank": self.rank,
                "hypothesis": self.hypothesis,
                "category": self.category,
                "confidence": self.confidence,
                "evidence_references": self.evidence_references,
                "affected_files": self.affected_files,
                "affected_lines": self.affected_lines,
                "model_used": self.model_used,
            }
        )


class PatchDraftRecord(TimestampMixin, Base):
    __tablename__ = "patch_drafts"
    __table_args__ = (
        CheckConstraint("generation_attempt > 0", name="ck_patch_drafts_attempt_positive"),
        Index("ix_patch_drafts_case_attempt", "triage_case_id", "generation_attempt"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    triage_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("triage_cases.id", ondelete="CASCADE"), nullable=False
    )
    hypothesis_id: Mapped[UUID] = mapped_column(
        ForeignKey("root_cause_hypotheses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    diff_content: Mapped[str] = mapped_column(Text, nullable=False)
    files_modified: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    branch_name: Mapped[str] = mapped_column(Text, nullable=False)
    commit_message: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    generation_attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    model_used: Mapped[str] = mapped_column(Text, nullable=False)
    triage_case: Mapped[TriageCaseRecord] = relationship(back_populates="patch_drafts")
    hypothesis: Mapped[RootCauseHypothesisRecord] = relationship(back_populates="patch_drafts")
    validation_result: Mapped[ValidationResultRecord | None] = relationship(
        back_populates="patch_draft", cascade="all, delete-orphan", uselist=False
    )
    pull_requests: Mapped[list[PullRequestRecord]] = relationship(back_populates="patch_draft")
    artifacts: Mapped[list[ArtifactRecord]] = relationship(back_populates="patch_draft")

    @classmethod
    def from_domain(cls, case_id: UUID, item: PatchDraft) -> PatchDraftRecord:
        return cls(id=item.id, triage_case_id=case_id, **item.model_dump(exclude={"id"}))

    def to_domain(self) -> PatchDraft:
        return PatchDraft.model_validate(
            {key: getattr(self, key) for key in PatchDraft.model_fields}
        )


class ValidationResultRecord(Base):
    __tablename__ = "validation_results"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    patch_draft_id: Mapped[UUID] = mapped_column(
        ForeignKey("patch_drafts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    tests_passed: Mapped[bool | None] = mapped_column(Boolean)
    tests_output: Mapped[str | None] = mapped_column(Text)
    build_passed: Mapped[bool | None] = mapped_column(Boolean)
    build_output: Mapped[str | None] = mapped_column(Text)
    lint_passed: Mapped[bool | None] = mapped_column(Boolean)
    lint_output: Mapped[str | None] = mapped_column(Text)
    overall_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    confidence_delta: Mapped[float] = mapped_column(Float, nullable=False)
    worktree_path: Mapped[str] = mapped_column(Text, nullable=False)
    validated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    patch_draft: Mapped[PatchDraftRecord] = relationship(back_populates="validation_result")

    @classmethod
    def from_domain(cls, item: ValidationResult) -> ValidationResultRecord:
        return cls(**item.model_dump())

    def to_domain(self) -> ValidationResult:
        return ValidationResult.model_validate(
            {key: getattr(self, key) for key in ValidationResult.model_fields}
        )


class PullRequestRecord(TimestampMixin, Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("patch_draft_id", name="uq_pull_requests_patch_draft"),
        Index("ix_pull_requests_case_created", "triage_case_id", text("created_at DESC")),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    triage_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("triage_cases.id", ondelete="CASCADE"), nullable=False
    )
    patch_draft_id: Mapped[UUID] = mapped_column(
        ForeignKey("patch_drafts.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    base_branch: Mapped[str] = mapped_column(Text, nullable=False)
    head_branch: Mapped[str] = mapped_column(Text, nullable=False)
    labels: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    github_pr_number: Mapped[int | None] = mapped_column(Integer)
    pr_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    triage_case: Mapped[TriageCaseRecord] = relationship(back_populates="pull_requests")
    patch_draft: Mapped[PatchDraftRecord] = relationship(back_populates="pull_requests")

    @classmethod
    def from_domain(cls, case_id: UUID, item: PRDraft) -> PullRequestRecord:
        values = item.model_dump()
        values["status"] = item.status.value
        return cls(triage_case_id=case_id, **values)

    def to_domain(self) -> PRDraft:
        values = {key: getattr(self, key) for key in PRDraft.model_fields}
        values["status"] = PRStatus(self.status)
        return PRDraft.model_validate(values)


class DuplicateGroupRecord(Base):
    __tablename__ = "duplicate_groups"
    __table_args__ = (
        CheckConstraint("threshold_used BETWEEN 0 AND 1", name="ck_duplicate_groups_threshold"),
        Index("ix_duplicate_groups_members", "member_case_ids", postgresql_using="gin"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    primary_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("triage_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_case_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    similarity_scores: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    cluster_summary: Mapped[str] = mapped_column(Text, nullable=False)
    threshold_used: Mapped[float] = mapped_column(Float, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @classmethod
    def from_domain(cls, item: DuplicateGroup) -> DuplicateGroupRecord:
        return cls(
            id=item.id,
            primary_case_id=item.primary_case_id,
            member_case_ids=[str(value) for value in item.member_case_ids],
            similarity_scores=item.similarity_scores,
            cluster_summary=item.cluster_summary,
            threshold_used=item.threshold_used,
        )

    def to_domain(self) -> DuplicateGroup:
        return DuplicateGroup.model_validate(
            {
                "id": self.id,
                "primary_case_id": self.primary_case_id,
                "member_case_ids": self.member_case_ids,
                "similarity_scores": self.similarity_scores,
                "cluster_summary": self.cluster_summary,
                "threshold_used": self.threshold_used,
            }
        )


class AnalysisRunRecord(TimestampMixin, Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        CheckConstraint("confidence_threshold BETWEEN 0 AND 1", name="ck_analysis_runs_threshold"),
        CheckConstraint("duration_seconds >= 0", name="ck_analysis_runs_duration"),
        Index("ix_analysis_runs_case_created", "triage_case_id", text("created_at DESC")),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    triage_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("triage_cases.id", ondelete="CASCADE"), nullable=False
    )
    model_used: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    state_transitions: Mapped[list[JsonObject]] = mapped_column(JSONB, nullable=False)
    workflow_trace: Mapped[list[JsonObject]] = mapped_column(JSONB, nullable=False)
    final_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    triage_case: Mapped[TriageCaseRecord] = relationship(back_populates="analysis_runs")
    artifacts: Mapped[list[ArtifactRecord]] = relationship(back_populates="analysis_run")

    @classmethod
    def from_domain(cls, item: AnalysisRun) -> AnalysisRunRecord:
        return cls(
            id=item.id,
            triage_case_id=item.triage_case_id,
            model_used=item.model_used,
            embedding_model=item.embedding_model,
            confidence_threshold=item.confidence_threshold,
            duration_seconds=item.duration_seconds,
            state_transitions=[_json(value) for value in item.state_transitions],
            workflow_trace=[_json(value) for value in item.workflow_trace],
            final_state=item.final_state.value,
        )

    def to_domain(self) -> AnalysisRun:
        return AnalysisRun.model_validate(
            {
                "id": self.id,
                "triage_case_id": self.triage_case_id,
                "model_used": self.model_used,
                "embedding_model": self.embedding_model,
                "confidence_threshold": self.confidence_threshold,
                "duration_seconds": self.duration_seconds,
                "state_transitions": self.state_transitions,
                "workflow_trace": self.workflow_trace,
                "final_state": self.final_state,
            }
        )


class ArtifactRecord(TimestampMixin, Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("relative_path", name="uq_artifacts_relative_path"),
        UniqueConstraint("sha256", "kind", name="uq_artifacts_hash_kind"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    triage_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("triage_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    patch_draft_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("patch_drafts.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    media_type: Mapped[str] = mapped_column(Text, nullable=False)
    triage_case: Mapped[TriageCaseRecord] = relationship(back_populates="artifacts")
    analysis_run: Mapped[AnalysisRunRecord | None] = relationship(back_populates="artifacts")
    patch_draft: Mapped[PatchDraftRecord | None] = relationship(back_populates="artifacts")


def hydrate_triage_case(record: TriageCaseRecord) -> TriageCase:
    """Hydrate a case from a record whose relationships were eagerly loaded."""
    latest_run = max(record.analysis_runs, key=lambda row: (row.created_at, row.id), default=None)
    latest_evidence = max(
        record.evidence_packs,
        key=lambda row: (row.retrieval_timestamp, row.id),
        default=None,
    )
    hypotheses = sorted(record.hypotheses, key=lambda row: (row.created_at, row.rank, row.id))
    patches = sorted(
        record.patch_drafts, key=lambda row: (row.created_at, row.generation_attempt, row.id)
    )
    validations = [row.validation_result for row in patches if row.validation_result is not None]
    latest_validation = max(validations, key=lambda row: (row.validated_at, row.id), default=None)
    latest_pr = max(record.pull_requests, key=lambda row: (row.created_at, row.id), default=None)
    metadata = IssueMetadata.model_validate(record.issue_metadata)
    parsed = record.parsed_context
    evidence = latest_evidence.to_domain() if latest_evidence else None
    return TriageCase(
        id=record.id,
        repo=record.repo,
        issue_number=record.issue_number,
        state=WorkflowState(record.state),
        state_history=(
            [StateTransition.model_validate(item) for item in latest_run.state_transitions]
            if latest_run
            else []
        ),
        retry_count=record.retry_count,
        issue_metadata=metadata,
        issue_type=IssueType(record.issue_type) if record.issue_type else None,
        severity=Severity(record.severity) if record.severity else None,
        raw_logs=parsed.get("raw_logs", []),
        stack_traces=[StackTrace.model_validate(item) for item in parsed.get("stack_traces", [])],
        error_messages=parsed.get("error_messages", []),
        evidence=evidence,
        candidate_duplicates=evidence.duplicate_candidates if evidence else [],
        hypotheses=[row.to_domain() for row in hypotheses],
        patch_drafts=[row.to_domain() for row in patches],
        validation_result=latest_validation.to_domain() if latest_validation else None,
        pr_draft=latest_pr.to_domain() if latest_pr else None,
    )


def validate_case_provenance(case: TriageCase) -> None:
    """Reject inconsistent child identifiers before persistence."""
    hypothesis_ids = {item.id for item in case.hypotheses}
    patch_ids = {item.id for item in case.patch_drafts}
    for patch in case.patch_drafts:
        if patch.hypothesis_id not in hypothesis_ids:
            raise ValueError(f"patch {patch.id} references a hypothesis outside the triage case")
    if case.validation_result and case.validation_result.patch_draft_id not in patch_ids:
        raise ValueError("validation_result references a patch outside the triage case")
    if case.pr_draft and case.pr_draft.patch_draft_id not in patch_ids:
        raise ValueError("pr_draft references a patch outside the triage case")

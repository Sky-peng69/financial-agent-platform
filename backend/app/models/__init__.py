import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ORG_USER = "org_user"
    INVESTOR = "investor"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FileStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSED = "parsed"
    FAILED = "failed"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    members: Mapped[list["User"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.INVESTOR, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    organization: Mapped[Organization | None] = relationship(back_populates="members")
    tasks: Mapped[list["Task"]] = relationship(back_populates="user")
    files: Mapped[list["ResearchFile"]] = relationship(back_populates="user")
    research_subjects: Mapped[list["ResearchSubject"]] = relationship(back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    input_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_references: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="tasks")
    files: Mapped[list["ResearchFile"]] = relationship(back_populates="task")


class ResearchSubject(Base):
    __tablename__ = "research_subjects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    current_view: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evidence_strength: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_view_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="research_subjects")
    files: Mapped[list["ResearchFile"]] = relationship(back_populates="research_subject")
    evidence_items: Mapped[list["DocumentEvidence"]] = relationship(back_populates="research_subject")
    claims: Mapped[list["ResearchClaim"]] = relationship(back_populates="research_subject", cascade="all, delete-orphan")
    assumptions: Mapped[list["ResearchAssumption"]] = relationship(back_populates="research_subject", cascade="all, delete-orphan")
    challenges: Mapped[list["ResearchChallenge"]] = relationship(back_populates="research_subject", cascade="all, delete-orphan")
    decision_memos: Mapped[list["DecisionMemo"]] = relationship(back_populates="research_subject", cascade="all, delete-orphan")
    financing_needs: Mapped[list["FinancingNeed"]] = relationship(back_populates="research_subject", cascade="all, delete-orphan")
    business_events: Mapped[list["BusinessEvent"]] = relationship(back_populates="research_subject", cascade="all, delete-orphan")
    event_impacts: Mapped[list["BusinessEventImpact"]] = relationship(back_populates="research_subject", cascade="all, delete-orphan")
    action_recommendations: Mapped[list["ActionRecommendation"]] = relationship(back_populates="research_subject", cascade="all, delete-orphan")
    asset_audits: Mapped[list["ResearchAssetAudit"]] = relationship(back_populates="research_subject", cascade="all, delete-orphan")


class ResearchFile(Base):
    __tablename__ = "research_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    research_subject_id: Mapped[str | None] = mapped_column(ForeignKey("research_subjects.id"), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[FileStatus] = mapped_column(SAEnum(FileStatus), default=FileStatus.UPLOADED, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="files")
    research_subject: Mapped[ResearchSubject | None] = relationship(back_populates="files")
    task: Mapped[Task | None] = relationship(back_populates="files")
    evidence_items: Mapped[list["DocumentEvidence"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
    )


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    research_subject_id: Mapped[str | None] = mapped_column(ForeignKey("research_subjects.id"), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    report_style: Mapped[str] = mapped_column(String(50), nullable=False, default="institutional")
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    file_manifest: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="ai_draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class DocumentEvidence(Base):
    __tablename__ = "document_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id: Mapped[str] = mapped_column(ForeignKey("research_files.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    research_subject_id: Mapped[str | None] = mapped_column(ForeignKey("research_subjects.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="pdf")
    page_number: Mapped[int | None] = mapped_column(nullable=True)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    location_label: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    file: Mapped[ResearchFile] = relationship(back_populates="evidence_items")
    research_subject: Mapped[ResearchSubject | None] = relationship(back_populates="evidence_items")


class ResearchClaim(Base):
    __tablename__ = "research_claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    research_subject_id: Mapped[str] = mapped_column(ForeignKey("research_subjects.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False, default="neutral")
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    evidence_strength: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="needs_review")
    evidence_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="needs_review")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    research_subject: Mapped[ResearchSubject] = relationship(back_populates="claims")


class BusinessEvent(Base):
    __tablename__ = "business_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    research_subject_id: Mapped[str] = mapped_column(ForeignKey("research_subjects.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="user_input")
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    research_subject: Mapped[ResearchSubject] = relationship(back_populates="business_events")


class BusinessEventImpact(Base):
    __tablename__ = "business_event_impacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    research_subject_id: Mapped[str] = mapped_column(ForeignKey("research_subjects.id"), nullable=False, index=True)
    business_event_id: Mapped[str] = mapped_column(ForeignKey("business_events.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    impact_summary: Mapped[str] = mapped_column(Text, nullable=False)
    affected_claim_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_recommendation_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_assumptions: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_gaps: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    research_subject: Mapped[ResearchSubject] = relationship(back_populates="event_impacts")
    business_event: Mapped[BusinessEvent] = relationship()


class FinancingNeed(Base):
    __tablename__ = "financing_needs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    research_subject_id: Mapped[str] = mapped_column(ForeignKey("research_subjects.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    need_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    urgency: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    evidence_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="needs_review")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    research_subject: Mapped[ResearchSubject] = relationship(back_populates="financing_needs")


class ActionRecommendation(Base):
    __tablename__ = "action_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    research_subject_id: Mapped[str] = mapped_column(ForeignKey("research_subjects.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    evidence_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_claim_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_assumption_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="needs_review")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    research_subject: Mapped[ResearchSubject] = relationship(back_populates="action_recommendations")


class ResearchAssumption(Base):
    __tablename__ = "research_assumptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    research_subject_id: Mapped[str] = mapped_column(ForeignKey("research_subjects.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="business")
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    evidence_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="needs_review")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    research_subject: Mapped[ResearchSubject] = relationship(back_populates="assumptions")


class ResearchAssetAudit(Base):
    __tablename__ = "research_asset_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    research_subject_id: Mapped[str] = mapped_column(ForeignKey("research_subjects.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    previous_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    research_subject: Mapped[ResearchSubject] = relationship(back_populates="asset_audits")


class ResearchChallenge(Base):
    __tablename__ = "research_challenges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    research_subject_id: Mapped[str] = mapped_column(ForeignKey("research_subjects.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("research_claims.id"), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    research_subject: Mapped[ResearchSubject] = relationship(back_populates="challenges")


class DecisionMemo(Base):
    __tablename__ = "decision_memos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    research_subject_id: Mapped[str] = mapped_column(ForeignKey("research_subjects.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    current_conclusion: Mapped[str] = mapped_column(Text, nullable=False)
    key_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    biggest_uncertainty: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="ai_draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    research_subject: Mapped[ResearchSubject] = relationship(back_populates="decision_memos")

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.enums import (
    AnswerStatus,
    DocumentStatus,
    DocumentType,
    ProjectStatus,
    QuestionCategory,
    RFPType,
    RiskLevel,
    UserRole,
)
from src.infrastructure.database.connection import Base
from src.core.config import settings


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    users: Mapped[list["User"]] = relationship(back_populates="tenant")
    projects: Mapped[list["Project"]] = relationship(back_populates="tenant")
    knowledge_base: Mapped[list["KnowledgeBase"]] = relationship(back_populates="tenant")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.ANALYST)
    is_active: Mapped[bool] = mapped_column(default=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="users")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    knowledge_entries: Mapped[list["KnowledgeBase"]] = relationship(back_populates="created_by_user")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.DRAFT
    )
    rfp_type: Mapped[RFPType] = mapped_column(
        Enum(RFPType), default=RFPType.UNKNOWN
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    client_name: Mapped[str | None] = mapped_column(String(255))
    project_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    tenant: Mapped["Tenant"] = relationship(back_populates="projects")
    documents: Mapped[list["Document"]] = relationship(back_populates="project")
    questions: Mapped[list["Question"]] = relationship(back_populates="project")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType), default=DocumentType.UNKNOWN
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PENDING
    )
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int | None] = mapped_column(Integer)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    doc_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")
    questions: Mapped[list["Question"]] = relationship(back_populates="document")


class Chunk(Base, TimestampMixin):
    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    document_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.embedding_dimensions)
    )
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    page_number: Mapped[int | None] = mapped_column(Integer)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    document: Mapped["Document"] = relationship(back_populates="chunks")
    citations: Mapped[list["Citation"]] = relationship(back_populates="chunk")


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    document_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id")
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[QuestionCategory] = mapped_column(
        Enum(QuestionCategory), default=QuestionCategory.GENERAL
    )
    priority: Mapped[int] = mapped_column(Integer, default=1)
    question_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    project: Mapped["Project"] = relationship(back_populates="questions")
    document: Mapped["Document"] = relationship(back_populates="questions")
    answer: Mapped["Answer | None"] = relationship(back_populates="question")


class Answer(Base, TimestampMixin):
    __tablename__ = "answers"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    question_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id"), unique=True, nullable=False
    )
    suggested_text: Mapped[str] = mapped_column(Text, nullable=False)
    final_text: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column()
    needs_review: Mapped[bool] = mapped_column(default=True)
    risk_level: Mapped[RiskLevel | None] = mapped_column(Enum(RiskLevel))
    compliance_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[AnswerStatus] = mapped_column(
        Enum(AnswerStatus), default=AnswerStatus.PENDING
    )
    approved_by: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_comments: Mapped[str | None] = mapped_column(Text)

    question: Mapped["Question"] = relationship(back_populates="answer")
    citations: Mapped[list["Citation"]] = relationship(back_populates="answer")


class Citation(Base, TimestampMixin):
    __tablename__ = "citations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    answer_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("answers.id"), nullable=False
    )
    chunk_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id")
    )
    document_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    relevance_score: Mapped[float] = mapped_column(default=0.0)

    answer: Mapped["Answer"] = relationship(back_populates="citations")
    chunk: Mapped["Chunk"] = relationship(back_populates="citations")


class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "knowledge_base"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.embedding_dimensions)
    )
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    category: Mapped[str | None] = mapped_column(String(100))
    approved: Mapped[bool] = mapped_column(default=False)
    usage_count: Mapped[int] = mapped_column(default=0)
    created_by: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="knowledge_base")
    created_by_user: Mapped["User"] = relationship(back_populates="knowledge_entries")


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User | None"] = relationship(back_populates="audit_logs")

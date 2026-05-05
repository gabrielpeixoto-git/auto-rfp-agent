from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.enums import (
    AnswerStatus,
    ConfidenceLevel,
    DocumentStatus,
    DocumentType,
    ProjectStatus,
    QuestionCategory,
    RFPType,
    RiskLevel,
    UserRole,
)


class SourceCitation(BaseModel):
    title: str
    document_id: UUID
    chunk_id: UUID | None = None
    page: int | None = None
    relevance_score: float = Field(ge=0.0, le=1.0)


class GeneratedAnswer(BaseModel):
    id: str = Field(..., pattern=r"^Q-\d{3,}$")
    question_text: str
    suggested_answer: str
    answer_confidence: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    needs_review: bool
    risk_level: RiskLevel
    compliance_flags: list[str] = Field(default_factory=list)
    source_citations: list[SourceCitation] = Field(default_factory=list)
    retrieval_notes: str
    edited_answer: str | None = None
    status: AnswerStatus = AnswerStatus.GENERATED

    @field_validator("confidence_level", mode="before")
    @classmethod
    def set_confidence_level(cls, v, info):
        if v is not None:
            return v
        confidence = info.data.get("answer_confidence", 0)
        if confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif confidence > 0:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.UNKNOWN


class ProjectOutput(BaseModel):
    project_summary: str
    questions: list[GeneratedAnswer]
    missing_information: list[str]
    next_actions: list[str]


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.ANALYST
    tenant_id: UUID | None = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    tenant_id: UUID
    is_active: bool
    created_at: datetime


class UserWithToken(BaseModel):
    user: UserResponse
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class TokenPair(BaseModel):
    """Token pair response with access and refresh tokens."""
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # Seconds until access token expires


class AuthResponse(BaseModel):
    """
    Authentication response for secure token handling.
    
    Refresh token is NOT included - it's set as httpOnly cookie.
    Only access token is returned in response body.
    """
    user: UserResponse
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # Seconds until access token expires


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    rfp_type: RFPType = RFPType.UNKNOWN
    due_date: datetime | None = None
    client_name: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        serialization_alias="metadata"
    )

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None = None
    status: ProjectStatus
    rfp_type: RFPType
    due_date: datetime | None = None
    client_name: str | None = None
    project_metadata: dict[str, Any] = Field(default_factory=dict, serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime


class DocumentUpload(BaseModel):
    filename: str
    content_type: str
    size: int


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    project_id: UUID
    filename: str
    original_filename: str
    document_type: DocumentType
    status: DocumentStatus
    size_bytes: int
    page_count: int | None = None
    extracted_text: str | None = None
    doc_metadata: dict[str, Any] = Field(default_factory=dict, serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime


class AnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_id: UUID
    suggested_text: str
    final_text: str | None = None
    confidence: float | None = None
    needs_review: bool
    risk_level: RiskLevel | None = None
    compliance_flags: list[str]
    status: AnswerStatus
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    review_comments: str | None = None
    created_at: datetime
    updated_at: datetime


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False, populate_by_name=True)

    id: UUID
    project_id: UUID
    document_id: UUID | None = None
    question_text: str
    category: QuestionCategory
    priority: int = Field(default=1, ge=1, le=10)
    question_metadata: dict[str, Any] = Field(default_factory=dict, serialization_alias="metadata")
    created_at: datetime
    answer: AnswerResponse | None = None


class AnswerUpdate(BaseModel):
    edited_answer: str | None = None
    status: AnswerStatus | None = None
    review_comments: str | None = None


class KnowledgeBaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    category: str | None = None


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    title: str
    content: str
    tags: list[str]
    category: str | None = None
    approved: bool
    usage_count: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    user_id: UUID | None = None
    action: str
    entity_type: str
    entity_id: UUID | None = None
    details: dict[str, Any]
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class HealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy", "degraded"]
    version: str
    timestamp: datetime
    services: dict[str, Literal["up", "down"]]

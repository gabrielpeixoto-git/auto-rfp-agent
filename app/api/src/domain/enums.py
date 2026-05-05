from enum import Enum, auto


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    READY_FOR_REVIEW = "ready_for_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class RFPType(str, Enum):
    RFP = "rfp"
    RFI = "rfi"
    DDQ = "ddq"
    SECURITY_QUESTIONNAIRE = "security_questionnaire"
    PROPOSAL = "proposal"
    UNKNOWN = "unknown"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    INDEXING = "indexing"
    PROCESSED = "processed"
    FAILED = "failed"


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    XLS = "xls"
    TXT = "txt"
    CSV = "csv"
    UNKNOWN = "unknown"


class AnswerStatus(str, Enum):
    PENDING = "pending"
    GENERATED = "generated"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    UPLOAD = "upload"
    PROCESS = "process"
    GENERATE = "generate"
    APPROVE = "approve"
    REJECT = "reject"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESH = "token_refresh"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    CROSS_TENANT_ACCESS_ATTEMPT = "cross_tenant_access_attempt"


class QuestionCategory(str, Enum):
    COMPANY_OVERVIEW = "company_overview"
    TECHNICAL = "technical"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    PRICING = "pricing"
    TIMELINE = "timeline"
    REFERENCES = "references"
    SLA = "sla"
    GENERAL = "general"

class DomainException(Exception):
    """Base exception for domain errors."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundException(DomainException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} with id '{identifier}' not found",
            code="NOT_FOUND"
        )


class AlreadyExistsException(DomainException):
    """Resource already exists."""

    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            message=f"{resource} with {field} '{value}' already exists",
            code="ALREADY_EXISTS"
        )


class UnauthorizedException(DomainException):
    """User not authorized."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message=message, code="UNAUTHORIZED")


class ForbiddenException(DomainException):
    """User forbidden from action."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message=message, code="FORBIDDEN")


class ValidationException(DomainException):
    """Validation error."""

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message=message, code="VALIDATION_ERROR")


class TenantIsolationException(DomainException):
    """Tenant isolation violation."""

    def __init__(self, message: str = "Tenant isolation violation"):
        super().__init__(message=message, code="TENANT_ISOLATION")


class SecurityException(DomainException):
    """Security violation (e.g., missing tenant_id, access control)."""

    def __init__(self, message: str = "Security violation"):
        super().__init__(message=message, code="SECURITY_VIOLATION")


class DocumentProcessingException(DomainException):
    """Document processing error."""

    def __init__(self, message: str, document_id: str | None = None):
        self.document_id = document_id
        super().__init__(message=message, code="DOCUMENT_PROCESSING_ERROR")


class AIProviderException(DomainException):
    """AI provider error."""

    def __init__(self, message: str, provider: str | None = None):
        self.provider = provider
        super().__init__(message=message, code="AI_PROVIDER_ERROR")

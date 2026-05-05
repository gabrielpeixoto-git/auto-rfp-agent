"""
Base service with mandatory tenant isolation enforcement.

This ensures ALL data access operations include tenant filtering,
preventing developer errors that could reintroduce security vulnerabilities.
"""

from abc import ABC
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging_config import get_logger
from src.domain.exceptions import ForbiddenException

logger = get_logger(__name__)


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


class TenantRequiredError(SecurityError):
    """Raised when tenant_id is missing in a security-critical operation."""
    pass


class BaseService(ABC):
    """
    Base service class with enforced tenant isolation.
    
    All service classes MUST inherit from this to ensure:
    1. tenant_id is always provided
    2. All queries filter by tenant
    3. Runtime validation prevents security bypass
    
    Example:
        class ProjectService(BaseService):
            async def get_project(self, project_id: UUID) -> Project:
                # This will validate tenant_id is set
                self._validate_tenant_context()
                
                # Repository receives mandatory tenant_id
                return await self._repo.get_by_id(project_id, tenant_id=self._tenant_id)
    """
    
    def __init__(
        self,
        session: AsyncSession,
        user_id: UUID,
        tenant_id: UUID,
        role: str
    ):
        self._session = session
        self._user_id = user_id
        self._tenant_id = tenant_id
        self._role = role
        
        # Validate on initialization
        self._validate_tenant_context()
    
    def _validate_tenant_context(self) -> None:
        """
        Validate that tenant context is properly set.
        
        Raises:
            TenantRequiredError: If tenant_id is missing or invalid
        """
        if not self._tenant_id:
            logger.error(
                "Security violation: Service initialized without tenant_id",
                user_id=str(self._user_id) if self._user_id else "unknown",
                service_type=self.__class__.__name__
            )
            raise TenantRequiredError(
                f"{self.__class__.__name__} requires tenant_id for security isolation"
            )
        
        if not self._user_id:
            logger.error(
                "Security violation: Service initialized without user_id",
                tenant_id=str(self._tenant_id),
                service_type=self.__class__.__name__
            )
            raise TenantRequiredError(
                f"{self.__class__.__name__} requires user_id for audit trail"
            )
        
        logger.debug(
            "Service initialized with security context",
            service=self.__class__.__name__,
            user_id=str(self._user_id),
            tenant_id=str(self._tenant_id),
            role=self._role
        )
    
    def _require_tenant_id(self, operation: str) -> UUID:
        """
        Get tenant_id with validation for any operation.
        
        Args:
            operation: Name of operation for error messages
            
        Returns:
            tenant_id
            
        Raises:
            TenantRequiredError: If tenant_id is missing
        """
        if not self._tenant_id:
            logger.error(
                "Security violation: Operation attempted without tenant context",
                operation=operation,
                user_id=str(self._user_id) if self._user_id else "unknown",
                service_type=self.__class__.__name__
            )
            raise TenantRequiredError(
                f"Operation '{operation}' requires tenant_id for security isolation"
            )
        return self._tenant_id
    
    def _verify_tenant_match(
        self,
        resource_tenant_id: UUID,
        resource_type: str,
        resource_id: UUID
    ) -> None:
        """
        Verify that a resource belongs to the current tenant.
        
        Args:
            resource_tenant_id: The tenant_id of the resource
            resource_type: Type of resource (for logging)
            resource_id: ID of resource (for logging)
            
        Raises:
            ForbiddenException: If resource belongs to different tenant
        """
        if str(resource_tenant_id) != str(self._tenant_id):
            logger.warning(
                "Security violation: Cross-tenant access attempt detected",
                user_id=str(self._user_id),
                user_tenant=str(self._tenant_id),
                resource_tenant=str(resource_tenant_id),
                resource_type=resource_type,
                resource_id=str(resource_id)
            )
            raise ForbiddenException(
                f"Access denied to {resource_type}"
            )
    
    def _require_role(self, allowed_roles: list[str], operation: str) -> None:
        """
        Verify user has required role for operation.
        
        Args:
            allowed_roles: List of roles that can perform operation
            operation: Name of operation for error messages
            
        Raises:
            ForbiddenException: If user doesn't have required role
        """
        if self._role not in allowed_roles:
            logger.warning(
                "Security violation: Unauthorized role access attempt",
                user_id=str(self._user_id),
                user_role=self._role,
                required_roles=allowed_roles,
                operation=operation
            )
            raise ForbiddenException(
                f"Insufficient permissions for '{operation}'"
            )


class SecureRepositoryMixin:
    """
    Mixin for repositories to enforce tenant isolation.
    
    Provides helper methods that fail securely if tenant_id is not provided.
    """
    
    def _require_tenant_id(self, method_name: str, tenant_id: UUID | None) -> UUID:
        """
        Validate tenant_id is provided.
        
        Args:
            method_name: Name of calling method
            tenant_id: Tenant ID to validate
            
        Returns:
            Validated tenant_id
            
        Raises:
            TenantRequiredError: If tenant_id is None
        """
        if tenant_id is None:
            logger.error(
                "Security violation: Repository method called without tenant_id",
                method=method_name,
                repository=self.__class__.__name__
            )
            raise TenantRequiredError(
                f"{self.__class__.__name__}.{method_name}() requires tenant_id parameter"
            )
        return tenant_id
    
    def _apply_tenant_filter(self, query, tenant_id: UUID, model_class, join_path: str | None = None):
        """
        Apply tenant filter to query with optional join path.
        
        Args:
            query: SQLAlchemy query
            tenant_id: Tenant ID to filter by
            model_class: Model class that has tenant_id column
            join_path: Optional join path (e.g., "Project" for Document->Project.tenant_id)
            
        Returns:
            Filtered query
        """
        if join_path:
            # For joined queries (e.g., Document->Project)
            from sqlalchemy import select
            related_model = join_path
            query = query.where(related_model.tenant_id == tenant_id)
        else:
            query = query.where(model_class.tenant_id == tenant_id)
        
        return query

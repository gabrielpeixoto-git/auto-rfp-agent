from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging_config import get_logger
from src.domain.enums import AuditAction, ProjectStatus
from src.domain.exceptions import ForbiddenException, NotFoundException
from src.domain.schemas import PaginatedResponse, ProjectCreate, ProjectResponse
from src.infrastructure.database.repositories import (
    SQLAlchemyAuditLogRepository,
    SQLAlchemyProjectRepository,
)

logger = get_logger(__name__)


class ProjectService:
    def __init__(self, session: AsyncSession, user_id: UUID, tenant_id: UUID, role: str):
        self._session = session
        self._user_id = user_id
        self._tenant_id = tenant_id
        self._role = role
        self._project_repo = SQLAlchemyProjectRepository(session)
        self._audit_repo = SQLAlchemyAuditLogRepository(session)

    async def list_projects(
        self, skip: int = 0, limit: int = 100
    ) -> PaginatedResponse:
        projects = await self._project_repo.get_by_tenant(
            self._tenant_id, skip=skip, limit=limit
        )
        # Note: total count should be fetched separately in production
        return PaginatedResponse(
            items=projects,
            total=len(projects),
            page=skip // limit + 1,
            page_size=limit,
            total_pages=(len(projects) + limit - 1) // limit,
        )

    async def get_project(self, project_id: UUID) -> ProjectResponse:
        """Get project by ID with tenant isolation verification."""
        # Query with tenant filtering to ensure isolation at database level
        project = await self._project_repo.get_by_id(
            project_id, tenant_id=self._tenant_id
        )
        if not project:
            raise NotFoundException("Project", str(project_id))
        return project

    async def create_project(self, data: ProjectCreate) -> ProjectResponse:
        # Only admin, manager, and analyst can create projects
        if self._role not in ["admin", "manager", "analyst"]:
            raise ForbiddenException("Insufficient permissions to create projects")

        project = await self._project_repo.create(
            tenant_id=self._tenant_id,
            data=data.model_dump(exclude_unset=True),
        )

        await self._audit_repo.create(
            {
                "tenant_id": self._tenant_id,
                "user_id": self._user_id,
                "action": AuditAction.CREATE,
                "entity_type": "Project",
                "entity_id": project.id,
                "details": {"name": project.name},
            }
        )

        logger.info(
            "Project created",
            project_id=str(project.id),
            tenant_id=str(self._tenant_id),
        )

        return project

    async def update_project(
        self, project_id: UUID, data: dict[str, Any]
    ) -> ProjectResponse:
        project = await self.get_project(project_id)

        if self._role not in ["admin", "manager", "analyst"]:
            raise ForbiddenException("Insufficient permissions to update projects")

        # SECURITY: tenant_id obrigatório para isolamento
        updated = await self._project_repo.update(project_id, data, tenant_id=self._tenant_id)
        if not updated:
            raise NotFoundException("Project", str(project_id))

        await self._audit_repo.create(
            {
                "tenant_id": self._tenant_id,
                "user_id": self._user_id,
                "action": AuditAction.UPDATE,
                "entity_type": "Project",
                "entity_id": project_id,
                "details": data,
            }
        )

        return updated

    async def delete_project(self, project_id: UUID) -> bool:
        project = await self.get_project(project_id)

        if self._role not in ["admin", "manager"]:
            raise ForbiddenException("Insufficient permissions to delete projects")

        # Soft delete or actual delete depending on requirements
        # For now, we'll just mark as deleted in audit
        await self._audit_repo.create(
            {
                "tenant_id": self._tenant_id,
                "user_id": self._user_id,
                "action": AuditAction.DELETE,
                "entity_type": "Project",
                "entity_id": project_id,
                "details": {"name": project.name},
            }
        )

        logger.info(
            "Project deleted",
            project_id=str(project_id),
            tenant_id=str(self._tenant_id),
        )

        return True

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import ForbiddenException, NotFoundException
from src.domain.schemas import (
    PaginatedResponse,
    ProjectCreate,
    ProjectResponse,
    UserResponse,
)
from src.infrastructure.database.connection import get_db
from src.api.dependencies import get_current_user, get_current_user_with_context
from src.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


async def get_project_service(
    user_context: Annotated[
        tuple[UserResponse, UUID, UUID, str],
        Depends(get_current_user_with_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectService:
    """Factory for project service with user context."""
    _, user_id, tenant_id, role = user_context
    return ProjectService(session, user_id, tenant_id, role)


@router.get("", response_model=PaginatedResponse)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: ProjectService = Depends(get_project_service),
):
    """List projects for the current tenant."""
    return await service.list_projects(skip=skip, limit=limit)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    service: ProjectService = Depends(get_project_service),
):
    """Create a new project."""
    try:
        return await service.create_project(data)
    except ForbiddenException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
):
    """Get a specific project."""
    try:
        return await service.get_project(project_id)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except ForbiddenException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: dict[str, Any],
    service: ProjectService = Depends(get_project_service),
):
    """Update a project."""
    try:
        return await service.update_project(project_id, data)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except ForbiddenException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
):
    """Delete a project."""
    try:
        await service.delete_project(project_id)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except ForbiddenException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )

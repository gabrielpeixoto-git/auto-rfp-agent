from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AuditAction
from src.domain.exceptions import ForbiddenException
from src.domain.schemas import AuditLogResponse, PaginatedResponse, UserResponse
from src.infrastructure.database.connection import get_db
from src.api.dependencies import get_current_user, require_admin
from src.infrastructure.database.repositories import SQLAlchemyAuditLogRepository

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=PaginatedResponse)
async def list_audit_logs(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    action: AuditAction | None = None,
    entity_type: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """List audit logs for the current tenant."""
    audit_repo = SQLAlchemyAuditLogRepository(session)
    logs = await audit_repo.get_by_tenant(
        current_user.tenant_id, skip=skip, limit=limit
    )
    
    # Filter if needed (should be done at DB level in production)
    if action:
        logs = [l for l in logs if l.action == action.value]
    if entity_type:
        logs = [l for l in logs if l.entity_type == entity_type]
    
    return PaginatedResponse(
        items=logs,
        total=len(logs),
        page=skip // limit + 1,
        page_size=limit,
        total_pages=(len(logs) + limit - 1) // limit,
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(require_admin)],
):
    """Get a specific audit log (admin only)."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Get single audit log endpoint needs implementation",
    )

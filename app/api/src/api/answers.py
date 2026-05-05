from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AuditAction
from src.domain.exceptions import ForbiddenException, NotFoundException
from src.domain.schemas import AnswerResponse, AnswerUpdate, PaginatedResponse, UserResponse
from src.infrastructure.database.connection import get_db
from src.api.dependencies import get_current_user, get_current_user_with_context
from src.infrastructure.database.repositories import (
    SQLAlchemyAnswerRepository,
    SQLAlchemyAuditLogRepository,
    SQLAlchemyQuestionRepository,
)
from src.services.project_service import ProjectService

router = APIRouter(prefix="/answers", tags=["answers"])


@router.get("/project/{project_id}")
async def list_project_answers(
    project_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Get all questions and answers for a project.
    
    Requires authentication and project ownership (tenant isolation).
    """
    import uuid
    import hashlib
    from datetime import datetime
    
    request_id = f"api_{uuid.uuid4().hex[:8]}"
    
    from src.core.logging_config import get_logger
    logger = get_logger(__name__)
    
    logger.info("[RUNTIME_TRACE] API_ENDPOINT_ENTERED",
               request_id=request_id,
               endpoint="list_project_answers",
               file="answers.py",
               project_id=str(project_id),
               user_id=str(current_user.id),
               timestamp=datetime.utcnow().isoformat())
    
    # Verify project access with tenant isolation
    from src.services.project_service import ProjectService
    project_service = ProjectService(
        session, current_user.id, current_user.tenant_id, current_user.role.value
    )
    try:
        await project_service.get_project(project_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied",
        )
    
    # Get questions
    question_repo = SQLAlchemyQuestionRepository(session)
    # SECURITY: tenant_id obrigatório para isolamento
    questions = await question_repo.get_by_project(project_id, tenant_id=current_user.tenant_id)
    
    logger.info("[RUNTIME_TRACE] Questions retrieved",
               request_id=request_id,
               question_count=len(questions),
               question_ids=[str(q.id) for q in questions[:5]])  # Log apenas os primeiros 5

    # Get answers for each question
    answer_repo = SQLAlchemyAnswerRepository(session)
    result = []
    for idx, question in enumerate(questions):
        # SECURITY: tenant_id obrigatório para isolamento
        answer = await answer_repo.get_by_question(question.id, tenant_id=current_user.tenant_id)
        
        if answer:
            answer_hash = hashlib.sha256(answer.suggested_text.encode()).hexdigest()[:16]
            
            # CUTOVER: Detectar se resposta é do pipeline novo ou legada
            is_new_pipeline = False
            if answer.compliance_flags:
                # Novo pipeline adiciona flags específicas
                is_new_pipeline = any(
                    f.startswith(("entity_", "evidence_hash_", "specificity_", "semantic_sim_"))
                    for f in answer.compliance_flags
                )
            
            if not is_new_pipeline:
                logger.warning("[CUTOVER] STALE ANSWER DETECTED - from old pipeline",
                           request_id=request_id,
                           question_index=idx,
                           question_id=str(question.id),
                           answer_id=str(answer.id),
                           answer_hash=answer_hash,
                           compliance_flags=answer.compliance_flags,
                           created_at=str(answer.created_at) if hasattr(answer, 'created_at') else 'unknown',
                           action="ANSWER_NEEDS_REGENERATION")
            else:
                logger.info("[RUNTIME_TRACE] Answer retrieved from database",
                           request_id=request_id,
                           question_index=idx,
                           question_id=str(question.id),
                           answer_id=str(answer.id),
                           answer_hash=answer_hash,
                           answer_preview=answer.suggested_text[:80],
                           compliance_flags=answer.compliance_flags,
                           created_at=str(answer.created_at) if hasattr(answer, 'created_at') else 'unknown',
                           updated_at=str(answer.updated_at) if hasattr(answer, 'updated_at') else 'unknown')
        else:
            logger.info("[RUNTIME_TRACE] No answer found for question",
                       request_id=request_id,
                       question_index=idx,
                       question_id=str(question.id))
        
        result.append({
            "question": question,
            "answer": answer,
        })
    
    logger.info("[RUNTIME_TRACE] API_ENDPOINT_RETURNING",
               request_id=request_id,
               result_count=len(result),
               answers_found=sum(1 for r in result if r["answer"] is not None))

    return result


@router.get("/{answer_id}", response_model=AnswerResponse)
async def get_answer(
    answer_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Get a specific answer."""
    answer_repo = SQLAlchemyAnswerRepository(session)
    
    # Note: This needs to be implemented in repository
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Get single answer endpoint needs implementation",
    )


@router.patch("/{answer_id}", response_model=AnswerResponse)
async def update_answer(
    answer_id: UUID,
    data: AnswerUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Update an answer (review/edit).
    
    Requires authentication, project ownership, and appropriate role.
    """
    if current_user.role.value not in ["admin", "manager", "analyst"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to edit answers",
        )
    
    # Verify answer ownership through question -> project -> tenant chain
    from src.infrastructure.database.models import Answer, Question, Project
    from sqlalchemy import select
    
    result = await session.execute(
        select(Answer, Question, Project)
        .join(Question, Answer.question_id == Question.id)
        .join(Project, Question.project_id == Project.id)
        .where(Answer.id == answer_id)
        .where(Project.tenant_id == current_user.tenant_id)
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found or access denied",
        )
    
    answer_repo = SQLAlchemyAnswerRepository(session)

    update_data = data.model_dump(exclude_unset=True)

    # If approving, set approved_by and approved_at
    if data.status and data.status.value in ["approved"]:
        from datetime import datetime, timezone
        update_data["approved_by"] = current_user.id
        update_data["approved_at"] = datetime.now(timezone.utc)

    # SECURITY: tenant_id obrigatório para isolamento
    updated = await answer_repo.update(answer_id, update_data, tenant_id=current_user.tenant_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found",
        )
    
    # Log audit
    audit_repo = SQLAlchemyAuditLogRepository(session)
    await audit_repo.create({
        "tenant_id": current_user.tenant_id,
        "user_id": current_user.id,
        "action": AuditAction.UPDATE if data.status != "approved" else AuditAction.APPROVE,
        "entity_type": "Answer",
        "entity_id": answer_id,
        "details": update_data,
    })
    
    return updated


@router.post("/project/{project_id}/generate")
async def generate_answers(
    project_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Trigger answer generation for a project.
    
    Requires authentication, project ownership, and appropriate role.
    """
    if current_user.role.value not in ["admin", "manager", "analyst"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    
    # Verify project access with tenant isolation
    from src.services.project_service import ProjectService
    project_service = ProjectService(
        session, current_user.id, current_user.tenant_id, current_user.role.value
    )
    try:
        await project_service.get_project(project_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied",
        )
    
    # Trigger generation task
    from src.workers.tasks import generate_answers_task
    generate_answers_task.delay(str(project_id))
    
    return {"status": "queued", "project_id": str(project_id)}

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AnswerStatus, AuditAction
from src.domain.exceptions import NotFoundException
from src.domain.schemas import AnswerResponse, AnswerUpdate, QuestionResponse, UserResponse
from src.infrastructure.database.connection import get_db
from src.api.dependencies import get_current_user
from src.infrastructure.database.repositories import (
    SQLAlchemyAnswerRepository,
    SQLAlchemyAuditLogRepository,
    SQLAlchemyQuestionRepository,
)
from src.services.rag_service import RAGService
from src.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Get a specific question by ID.
    
    Requires authentication and project ownership (tenant isolation).
    """
    from src.infrastructure.database.models import Question, Project
    from sqlalchemy import select
    
    # Query question with project ownership verification via tenant_id
    result = await session.execute(
        select(Question)
        .join(Project, Question.project_id == Project.id)
        .where(Question.id == question_id)
        .where(Project.tenant_id == current_user.tenant_id)
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found or access denied",
        )
    
    # Build QuestionResponse manually to avoid from_attributes issues
    return QuestionResponse(
        id=question.id,
        project_id=question.project_id,
        document_id=question.document_id,
        question_text=question.question_text,
        category=question.category,
        priority=question.priority,
        question_metadata=question.question_metadata or {},
        created_at=question.created_at,
    )


@router.get("/{question_id}/answer", response_model=AnswerResponse | None)
async def get_question_answer(
    question_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Get answer for a specific question."""
    answer_repo = SQLAlchemyAnswerRepository(session)
    # SECURITY: tenant_id obrigatório para isolamento
    answer = await answer_repo.get_by_question(question_id, tenant_id=current_user.tenant_id)
    return answer


@router.put("/{question_id}/answer", response_model=AnswerResponse)
async def update_question_answer(
    question_id: UUID,
    data: AnswerUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Update or create answer for a question."""
    answer_repo = SQLAlchemyAnswerRepository(session)
    
    # Check if answer exists
    # SECURITY: tenant_id obrigatório para isolamento
    existing = await answer_repo.get_by_question(question_id, tenant_id=current_user.tenant_id)

    if existing:
        # Update existing answer
        update_data = data.model_dump(exclude_unset=True)

        # If approving, set approved_by and approved_at
        if data.status and data.status.value == "approved":
            from datetime import datetime, timezone
            update_data["approved_by"] = current_user.id
            update_data["approved_at"] = datetime.now(timezone.utc)

        # SECURITY: tenant_id obrigatório para isolamento
        updated = await answer_repo.update(existing.id, update_data, tenant_id=current_user.tenant_id)
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
            "action": AuditAction.UPDATE,
            "entity_type": "Answer",
            "entity_id": existing.id,
            "details": update_data,
        })
        
        return updated
    else:
        # Create new answer
        from datetime import datetime, timezone
        
        create_data = {
            "suggested_text": data.edited_answer or "",
            "final_text": data.edited_answer,
            "confidence": 1.0,
            "needs_review": False,
            "status": data.status or AnswerStatus.REVIEWED,
            "review_comments": data.review_comments,
        }
        
        if data.status and data.status.value == "approved":
            create_data["approved_by"] = current_user.id
            create_data["approved_at"] = datetime.now(timezone.utc)
        
        new_answer = await answer_repo.create(question_id, create_data)
        
        # Log audit
        audit_repo = SQLAlchemyAuditLogRepository(session)
        await audit_repo.create({
            "tenant_id": current_user.tenant_id,
            "user_id": current_user.id,
            "action": AuditAction.CREATE,
            "entity_type": "Answer",
            "entity_id": new_answer.id,
            "details": create_data,
        })
        
        return new_answer


@router.post("/{question_id}/answer/approve", response_model=AnswerResponse)
async def approve_question_answer(
    question_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Approve answer for a question."""
    if current_user.role.value not in ["admin", "manager", "analyst"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to approve answers",
        )
    
    answer_repo = SQLAlchemyAnswerRepository(session)
    
    # Check if answer exists
    # SECURITY: tenant_id obrigatório para isolamento
    existing = await answer_repo.get_by_question(question_id, tenant_id=current_user.tenant_id)

    from datetime import datetime, timezone

    if existing:
        # Update existing answer to approved
        update_data = {
            "status": AnswerStatus.APPROVED,
            "approved_by": current_user.id,
            "approved_at": datetime.now(timezone.utc),
        }

        # SECURITY: tenant_id obrigatório para isolamento
        updated = await answer_repo.update(existing.id, update_data, tenant_id=current_user.tenant_id)
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
            "action": AuditAction.APPROVE,
            "entity_type": "Answer",
            "entity_id": existing.id,
            "details": {"status": "approved"},
        })
        
        return updated
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No answer found to approve. Generate an answer first.",
        )


@router.post("/{question_id}/answer/generate", response_model=AnswerResponse)
async def generate_question_answer(
    question_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Generate answer for a question using AI."""
    if current_user.role.value not in ["admin", "manager", "analyst"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to generate answers",
        )
    
    # Get question details
    from src.infrastructure.database.models import Question
    from sqlalchemy import select
    
    result = await session.execute(
        select(Question).where(Question.id == question_id)
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )
    
    # CUTOVER: Initialize 3-stage pipeline
    from src.services.answer_pipeline import AnswerPipeline
    rag_service = RAGService(session, current_user.tenant_id)
    pipeline = AnswerPipeline()
    
    try:
        # CUTOVER: Generate answer using 3-stage pipeline
        logger.info("[CUTOVER] API using 3-stage pipeline for answer generation",
                   question_id=str(question_id))
        
        validated_answer = await pipeline.generate_answer(
            question=question.question_text,
            question_id=f"Q-API-{str(question_id)[:8]}",
            rag_service=rag_service,
            document_id=str(question.document_id) if question.document_id else str(question.project_id),
            project_id=str(question.project_id),
            max_retries=2
        )
        
        # Save answer to database
        answer_repo = SQLAlchemyAnswerRepository(session)
        
        # Check if answer already exists
        # SECURITY: tenant_id obrigatório para isolamento
        existing = await answer_repo.get_by_question(question_id, tenant_id=current_user.tenant_id)

        answer_data = {
            "suggested_text": validated_answer.text,
            "final_text": None,  # User needs to review
            "confidence": validated_answer.confidence,
            "needs_review": not validated_answer.validation_passed or validated_answer.confidence < 0.8,
            "risk_level": "low" if validated_answer.validation_passed else "medium",
            "compliance_flags": [
                f"entity_{validated_answer.answer_plan.entity_principal}",
                f"evidence_hash_{validated_answer.evidence_set.evidence_hash}",
                f"specificity_{round(validated_answer.specificity_score, 2)}",
                f"validated_{validated_answer.validation_passed}",
            ],
            "status": AnswerStatus.GENERATED if validated_answer.validation_passed else AnswerStatus.PENDING,
            "review_comments": f"Chunks: {validated_answer.evidence_set.chunk_ids}",
        }

        if existing:
            # Update existing answer
            # SECURITY: tenant_id obrigatório para isolamento
            answer = await answer_repo.update(existing.id, answer_data, tenant_id=current_user.tenant_id)
        else:
            # Create new answer
            answer = await answer_repo.create(question_id, answer_data)
        
        logger.info("[CUTOVER] API answer saved",
                   question_id=str(question_id),
                   answer_hash=validated_answer.answer_hash)
        
        # Log audit
        audit_repo = SQLAlchemyAuditLogRepository(session)
        await audit_repo.create({
            "tenant_id": current_user.tenant_id,
            "user_id": current_user.id,
            "action": AuditAction.CREATE,
            "entity_type": "Answer",
            "entity_id": answer.id,
            "details": {
                "confidence": validated_answer.confidence,
                "needs_review": not validated_answer.validation_passed,
                "answer_hash": validated_answer.answer_hash,
            },
        })
        
        return answer
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(e)}",
        )

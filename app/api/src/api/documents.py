from datetime import datetime
from typing import Annotated
from uuid import UUID

import re
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import (
    DocumentProcessingException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from src.domain.schemas import DocumentResponse, QuestionResponse, UserResponse
from src.infrastructure.database.connection import get_db
from src.infrastructure.database.repositories import SQLAlchemyQuestionRepository
from src.api.dependencies import get_current_user, get_current_user_with_context
from src.services.document_service import DocumentService
from src.services.project_service import ProjectService
from src.workers.tasks import cleanup_stale_pending_documents

router = APIRouter(prefix="/documents", tags=["documents"])


async def get_document_service(
    user_context: Annotated[
        tuple[UserResponse, UUID, UUID, str],
        Depends(get_current_user_with_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentService:
    """Factory for document service with user context."""
    _, user_id, tenant_id, role = user_context
    return DocumentService(session, user_id, tenant_id, role)


@router.get("/project/{project_id}", response_model=list[DocumentResponse])
async def list_project_documents(
    project_id: UUID,
    user_context: Annotated[
        tuple[UserResponse, UUID, UUID, str],
        Depends(get_current_user_with_context),
    ],  # CRITICAL: Authentication is now mandatory - removed = None
    service: DocumentService = Depends(get_document_service),
):
    """List documents for a project.

    Also runs watchdog to fix any documents stuck in PENDING.
    """
    try:
        # CRITICAL: user_context is now mandatory - FastAPI dependency ensures auth
        _, user_id, tenant_id, role = user_context
        # Debug logging (only for development)
        # print(f"[BACKEND LIST DEBUG] project_id: {project_id}, tenant_id: {tenant_id}, user_id: {user_id}")
        
        # CRITICAL: Run watchdog before listing to fix any stuck documents
        try:
            fixed_count = await cleanup_stale_pending_documents()
            if fixed_count > 0:
                print(f"[WATCHDOG] Fixed {fixed_count} stale documents")
        except Exception as watchdog_error:
            print(f"[WATCHDOG] Error running watchdog: {watchdog_error}")
            print(f"[BACKEND LIST DEBUG] role: {role}")
        
        documents = await service.list_project_documents(project_id)
        
        # 🔴 RASTREAMENTO CRÍTICO: Log dos status retornados
        print(f"\n[TRACKING-API] ============================================")
        print(f"[TRACKING-API] event: LIST_DOCUMENTS")
        print(f"[TRACKING-API] project_id: {project_id}")
        print(f"[TRACKING-API] documents_found: {len(documents)}")
        if documents:
            for d in documents:
                print(f"[TRACKING-API] doc: id={d.id} status={d.status} filename={d.original_filename}")
        print(f"[TRACKING-API] timestamp: {datetime.utcnow().isoformat()}")
        print(f"[TRACKING-API] ============================================\n")
        
        return documents
    except ForbiddenException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )


@router.post("/upload/{project_id}", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
):
    """Upload a document to a project."""
    try:
        print(f"\n[BACKEND UPLOAD START] ============================================")
        print(f"[BACKEND UPLOAD START] project_id: {project_id}")
        print(f"[BACKEND UPLOAD START] file.filename: {file.filename}")
        print(f"[BACKEND UPLOAD START] file.content_type: {file.content_type}")
        print(f"[BACKEND UPLOAD START] file.file object: {type(file.file)}")
        
        # Validate file
        if not file.filename:
            raise ValidationException("No filename provided", field="file")

        content_type = file.content_type or "application/octet-stream"
        
        # Read file to check content before passing to service
        file.file.seek(0, 2)
        backend_size = file.file.tell()
        file.file.seek(0)
        
        print(f"[BACKEND UPLOAD START] Backend file size: {backend_size} bytes")
        
        # Read first 100 bytes for content preview
        content_preview = file.file.read(100)
        file.file.seek(0)
        print(f"[BACKEND UPLOAD START] Content preview (first 100 bytes): {content_preview}")
        print(f"[BACKEND UPLOAD START] Content preview hex: {content_preview.hex()}")
        
        # Check if content looks like text
        try:
            text_preview = content_preview.decode('utf-8', errors='replace')
            print(f"[BACKEND UPLOAD START] Text preview: {text_preview}")
            print(f"[BACKEND UPLOAD START] Contains Portuguese chars: {bool(re.search(r'[ãõáéíóúç]', text_preview))}")
        except:
            print(f"[BACKEND UPLOAD START] Content is not decodable as text")
        
        result = await service.upload_document(
            project_id=project_id,
            file=file.file,
            filename=file.filename,
            content_type=content_type,
        )
        
        # 🔴 RASTREAMENTO CRÍTICO: Log estruturado com document_id e status
        print(f"\n[TRACKING] ============================================")
        print(f"[TRACKING] document_id: {result.id}")
        print(f"[TRACKING] project_id: {result.project_id}")
        print(f"[TRACKING] status: {result.status}")
        print(f"[TRACKING] filename: {result.original_filename}")
        print(f"[TRACKING] task_triggered: process_document_task.delay")
        print(f"[TRACKING] timestamp: {datetime.utcnow().isoformat()}")
        print(f"[TRACKING] ============================================\n")
        
        print(f"[BACKEND UPLOAD COMPLETE] ============================================")
        return result
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except ForbiddenException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )
    except DocumentProcessingException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    service: DocumentService = Depends(get_document_service),
):
    """Get a specific document."""
    try:
        return await service.get_document(document_id)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.post("/{document_id}/process", status_code=status.HTTP_200_OK)
async def process_document_sync(
    document_id: UUID,
    service: DocumentService = Depends(get_document_service),
):
    """Process document synchronously (for testing Ollama integration)."""
    try:
        result = await service.process_document_sync(document_id)
        return {"status": "success", "result": result}
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    service: DocumentService = Depends(get_document_service),
):
    """Delete a document."""
    try:
        await service.delete_document(document_id)
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


@router.get("/{document_id}/questions", response_model=list[QuestionResponse])
async def list_document_questions(
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    user_context: Annotated[
        tuple[UserResponse, UUID, UUID, str],
        Depends(get_current_user_with_context),
    ],
):
    """List questions extracted from a document."""
    import traceback
    
    # 🔴 DEBUG COMPLETO - Capturar qualquer exceção
    try:
        # 🔴 RASTREAMENTO CRÍTICO
        print(f"\n[DEBUG-API] ============================================")
        print(f"[DEBUG-API] event: LIST_QUESTIONS_REQUEST")
        print(f"[DEBUG-API] document_id: {document_id}")
        print(f"[DEBUG-API] timestamp: {datetime.utcnow().isoformat()}")
        
        # Authentication is now mandatory via Depends
        _, user_id, tenant_id, role = user_context
        print(f"[DEBUG-API] user_id: {user_id}, tenant_id: {tenant_id}, role: {role}")
        
        from src.infrastructure.database.repositories import SQLAlchemyAnswerRepository, SQLAlchemyDocumentRepository
        
        # SECURITY: Get tenant_id from authenticated user
        tenant_id = user_context[2]
        
        # Verify document exists and user has access through tenant isolation
        print(f"[DEBUG-API] Buscando documento {document_id}...")
        doc_repo = SQLAlchemyDocumentRepository(session)
        document = await doc_repo.get_by_id(document_id, tenant_id=tenant_id)
        
        if not document:
            print(f"[DEBUG-API] ERRO: Documento {document_id} nao encontrado!")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )
        
        print(f"[DEBUG-API] Documento encontrado: id={document.id}, project_id={document.project_id}, status={document.status}")

        # SECURITY: Verify project ownership through tenant_id
        print(f"[DEBUG-API] Verificando ownership do projeto {document.project_id}...")
        from src.infrastructure.database.models import Project
        from sqlalchemy import select
        project_result = await session.execute(
            select(Project).where(Project.id == document.project_id, Project.tenant_id == tenant_id)
        )
        if not project_result.scalar_one_or_none():
            print(f"[DEBUG-API] ERRO: Acesso negado ao projeto {document.project_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this document",
            )
        print(f"[DEBUG-API] Ownership verificado OK")

        question_repo = SQLAlchemyQuestionRepository(session)
        answer_repo = SQLAlchemyAnswerRepository(session)

        # Fetch questions
        print(f"[DEBUG-API] Buscando perguntas do documento {document_id}...")
        questions = await question_repo.get_by_document(document_id, tenant_id=tenant_id)
        print(f"[DEBUG-API] Encontradas {len(questions)} perguntas")

        # Build response with answers
        result = []
        for idx, question in enumerate(questions):
            print(f"\n[DEBUG-API] ========== PERGUNTA {idx+1}/{len(questions)} ==========")
            print(f"[DEBUG-API] question.id: {question.id}")
            print(f"[DEBUG-API] question.project_id: {question.project_id}")
            print(f"[DEBUG-API] question.document_id: {question.document_id}")
            print(f"[DEBUG-API] question.question_text: {repr(question.question_text)}")
            print(f"[DEBUG-API] question.category: {repr(question.category)}")
            print(f"[DEBUG-API] question.category TYPE: {type(question.category)}")
            print(f"[DEBUG-API] question.priority: {question.priority}")
            print(f"[DEBUG-API] question.question_metadata: {question.question_metadata}")
            print(f"[DEBUG-API] question.created_at: {question.created_at}")
            
            # Fetch answer
            answer = None
            try:
                answer = await answer_repo.get_by_question(question.id, tenant_id=tenant_id)
                print(f"[DEBUG-API] answer: {answer}")
            except Exception as e:
                print(f"[DEBUG-API] ERRO ao buscar answer: {type(e).__name__}: {e}")
                answer = None
            
            # Log todos os campos do answer se existir
            if answer:
                print(f"[DEBUG-API] answer.id: {answer.id}")
                print(f"[DEBUG-API] answer.question_id: {answer.question_id}")
                print(f"[DEBUG-API] answer.suggested_text: {repr(answer.suggested_text[:50] if answer.suggested_text else None)}")
                print(f"[DEBUG-API] answer.final_text: {repr(answer.final_text[:50] if answer.final_text else None)}")
                print(f"[DEBUG-API] answer.confidence: {answer.confidence}")
                print(f"[DEBUG-API] answer.needs_review: {answer.needs_review}")
                print(f"[DEBUG-API] answer.status: {answer.status}")
                print(f"[DEBUG-API] answer.status TYPE: {type(answer.status)}")
                print(f"[DEBUG-API] answer.risk_level: {answer.risk_level}")
                print(f"[DEBUG-API] answer.compliance_flags: {answer.compliance_flags}")
                print(f"[DEBUG-API] answer.approved_by: {answer.approved_by}")
                print(f"[DEBUG-API] answer.approved_at: {answer.approved_at}")
                print(f"[DEBUG-API] answer.review_comments: {answer.review_comments}")
                print(f"[DEBUG-API] answer.created_at: {answer.created_at}")
                print(f"[DEBUG-API] answer.updated_at: {answer.updated_at}")
                
                # Tentar criar AnswerResponse separadamente para diagnosticar
                try:
                    from src.domain.schemas import AnswerResponse
                    answer_response_test = AnswerResponse.model_validate(answer)
                    print(f"[DEBUG-API] AnswerResponse.model_validate: OK")
                except Exception as answer_error:
                    print(f"[DEBUG-API] AnswerResponse.model_validate: FALHOU - {type(answer_error).__name__}: {answer_error}")
            
            # Preparar dados para QuestionResponse
            response_data = {
                "id": question.id,
                "project_id": question.project_id,
                "document_id": question.document_id,
                "question_text": question.question_text,
                "category": question.category,  # Passar diretamente primeiro
                "priority": question.priority,
                "question_metadata": question.question_metadata or {},
                "created_at": question.created_at,
                "answer": answer,
            }
            print(f"[DEBUG-API] Dados para QuestionResponse: {response_data}")
            
            # Tentar criar QuestionResponse
            try:
                q_response = QuestionResponse(**response_data)
                result.append(q_response)
                print(f"[DEBUG-API] ✓ QuestionResponse criado OK")
            except Exception as validation_error:
                print(f"[DEBUG-API] ✗ ERRO ao criar QuestionResponse: {type(validation_error).__name__}: {validation_error}")
                
                # Tentar diagnosticar qual campo está inválido
                print(f"\n[DEBUG-API] === DIAGNÓSTICO DE CAMPOS ===")
                for field_name, field_value in response_data.items():
                    print(f"[DEBUG-API]   {field_name}: {repr(field_value)} (type: {type(field_value)})")
                
                # Re-lançar para capturar no except externo
                raise

        print(f"[DEBUG-API] event: LIST_QUESTIONS_RESULT")
        print(f"[DEBUG-API] document_id: {document_id}")
        print(f"[DEBUG-API] questions_found: {len(result)}")
        print(f"[DEBUG-API] timestamp: {datetime.utcnow().isoformat()}")
        print(f"[DEBUG-API] ============================================\n")

        return result
        
    except HTTPException:
        raise
    except Exception as e:
        # 🔴 CAPTURAR QUALQUER ERRO E LOGAR COMPLETAMENTE
        error_traceback = traceback.format_exc()
        print(f"\n[DEBUG-API] ============================================")
        print(f"[DEBUG-API] CRITICAL ERROR in list_document_questions")
        print(f"[DEBUG-API] document_id: {document_id}")
        print(f"[DEBUG-API] error_type: {type(e).__name__}")
        print(f"[DEBUG-API] error_message: {str(e)}")
        print(f"[DEBUG-API] traceback:")
        print(error_traceback)
        print(f"[DEBUG-API] ============================================\n")
        
        # Retornar erro detalhado para facilitar diagnóstico
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": error_traceback,
                "document_id": str(document_id),
            }
        )


@router.post("/{document_id}/force-status")
async def force_document_status(
    document_id: UUID,
    status: str,  # processed, failed, needs_review
    session: Annotated[AsyncSession, Depends(get_db)],
    user_context: Annotated[
        tuple[UserResponse, UUID, UUID, str],
        Depends(get_current_user_with_context),
    ],
):
    """Force a document to a specific status (admin/debug only).
    
    Use this to manually fix documents stuck in PENDING.
    Requires admin or manager role.
    """
    from src.infrastructure.database.repositories import SQLAlchemyDocumentRepository
    from src.domain.enums import DocumentStatus
    
    # Authentication is now mandatory via Depends
    _, user_id, tenant_id, role = user_context
    if role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or managers can force document status"
        )
    
    # Map string to enum
    status_map = {
        "processed": DocumentStatus.PROCESSED,
        "failed": DocumentStatus.FAILED,
        "needs_review": DocumentStatus.NEEDS_REVIEW,
        "pending": DocumentStatus.PENDING,
    }
    
    if status not in status_map:
        raise ValidationException(f"Invalid status. Must be one of: {', '.join(status_map.keys())}")
    
    doc_repo = SQLAlchemyDocumentRepository(session)
    # SECURITY: tenant_id obrigatório para isolamento
    document = await doc_repo.get_by_id(document_id, tenant_id=tenant_id)

    if not document:
        raise NotFoundException("Document", str(document_id))

    old_status = document.status
    # SECURITY: tenant_id obrigatório para isolamento
    await doc_repo.update_status(document_id, status_map[status], tenant_id=tenant_id)
    
    logger.warning(
        "Document status forced manually",
        document_id=str(document_id),
        old_status=old_status,
        new_status=status,
        forced_by=str(user_id)
    )
    
    return {
        "document_id": str(document_id),
        "old_status": old_status,
        "new_status": status,
        "message": f"Document status forced from {old_status} to {status}"
    }


@router.get("/debug/stuck-documents")
async def get_stuck_documents(
    session: Annotated[AsyncSession, Depends(get_db)],
    user_context: Annotated[
        tuple[UserResponse, UUID, UUID, str],
        Depends(get_current_user_with_context),
    ],
):
    """Get list of documents stuck in PENDING for debugging.
    
    Also triggers the watchdog to fix them.
    Requires admin or manager role.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from src.infrastructure.database.models import Document
    
    # Authentication is now mandatory via Depends
    _, user_id, tenant_id, role = user_context
    if role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or managers can access debug endpoints"
        )
    
    # Run watchdog
    fixed_count = await cleanup_stale_pending_documents()
    
    # Get current stuck documents for this tenant only
    cutoff_time = datetime.utcnow() - timedelta(seconds=60)
    stmt = select(Document).where(
        Document.status == DocumentStatus.PENDING,
        Document.processing_started_at.isnot(None),
        Document.processing_started_at < cutoff_time
    )
    result = await session.execute(stmt)
    stuck_docs = result.scalars().all()
    
    return {
        "fixed_by_watchdog": fixed_count,
        "currently_stuck": [
            {
                "id": str(d.id),
                "filename": d.original_filename,
                "status": d.status,
                "processing_started_at": str(d.processing_started_at),
                "elapsed_seconds": (datetime.utcnow() - d.processing_started_at).total_seconds() if d.processing_started_at else None
            }
            for d in stuck_docs
        ],
        "total_stuck": len(stuck_docs)
    }

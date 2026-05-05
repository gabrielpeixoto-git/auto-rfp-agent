from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.domain.enums import UserRole
from src.domain.exceptions import NotFoundException, SecurityException
from src.domain.interfaces import (
    AnswerRepository,
    AuditLogRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
    ProjectRepository,
    QuestionRepository,
    TenantRepository,
    UserRepository,
)
from src.domain.schemas import (
    AnswerResponse,
    AuditLogResponse,
    DocumentResponse,
    KnowledgeBaseResponse,
    ProjectResponse,
    QuestionResponse,
    TenantResponse,
    UserResponse,
)
from src.infrastructure.database.models import (
    Answer,
    AuditLog,
    Document,
    KnowledgeBase,
    Project,
    Question,
    Tenant,
    User,
)


class SQLAlchemyTenantRepository(TenantRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, id: UUID) -> TenantResponse | None:
        result = await self._session.execute(
            select(Tenant).where(Tenant.id == id)
        )
        tenant = result.scalar_one_or_none()
        if tenant:
            return TenantResponse.model_validate(tenant)
        return None

    async def create(self, name: str) -> TenantResponse:
        tenant = Tenant(name=name)
        self._session.add(tenant)
        await self._session.commit()
        await self._session.refresh(tenant)
        return TenantResponse.model_validate(tenant)


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, id: UUID) -> UserResponse | None:
        result = await self._session.execute(
            select(User).where(User.id == id)
        )
        user = result.scalar_one_or_none()
        if user:
            return UserResponse.model_validate(user)
        return None

    async def get_by_email(self, email: str) -> UserResponse | None:
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        if user:
            return UserResponse.model_validate(user)
        return None

    async def create(
        self, email: str, password_hash: str, role: str, tenant_id: UUID
    ) -> UserResponse:
        user = User(
            email=email,
            password_hash=password_hash,
            role=UserRole(role),
            tenant_id=tenant_id,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return UserResponse.model_validate(user)


class SQLAlchemyProjectRepository(ProjectRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, id: UUID, tenant_id: UUID) -> ProjectResponse | None:
        """Get project by ID with mandatory tenant isolation.

        SECURITY: tenant_id is mandatory. Query will fail if tenant_id is not provided.
        """
        if not tenant_id:
            raise SecurityException("tenant_id is required for project access")

        # SECURITY: Always filter by tenant_id
        query = select(Project).where(Project.id == id).where(Project.tenant_id == tenant_id)
        result = await self._session.execute(query)
        project = result.scalar_one_or_none()
        if project:
            return ProjectResponse.model_validate(project)
        return None

    async def get_by_tenant(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[ProjectResponse]:
        result = await self._session.execute(
            select(Project)
            .where(Project.tenant_id == tenant_id)
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        projects = result.scalars().all()
        return [ProjectResponse.model_validate(p) for p in projects]

    async def create(self, tenant_id: UUID, data: dict) -> ProjectResponse:
        project = Project(tenant_id=tenant_id, **data)
        self._session.add(project)
        await self._session.commit()
        await self._session.refresh(project)
        return ProjectResponse.model_validate(project)

    async def update(self, id: UUID, data: dict, tenant_id: UUID) -> ProjectResponse | None:
        """Update project with mandatory tenant isolation.

        SECURITY: tenant_id is mandatory. Will return None if project does not belong to tenant.
        """
        if not tenant_id:
            raise SecurityException("tenant_id is required for project update")

        # SECURITY: Verify project belongs to tenant before updating
        query = select(Project).where(Project.id == id).where(Project.tenant_id == tenant_id)
        result = await self._session.execute(query)
        project = result.scalar_one_or_none()
        if not project:
            return None

        for key, value in data.items():
            setattr(project, key, value)
        await self._session.commit()
        await self._session.refresh(project)
        return ProjectResponse.model_validate(project)

    async def delete(self, id: UUID, tenant_id: UUID) -> bool:
        """Delete project with mandatory tenant isolation.

        SECURITY: tenant_id is mandatory. Will return False if project does not belong to tenant.
        """
        if not tenant_id:
            raise SecurityException("tenant_id is required for project deletion")

        # SECURITY: Verify project belongs to tenant before deleting
        query = select(Project).where(Project.id == id).where(Project.tenant_id == tenant_id)
        result = await self._session.execute(query)
        project = result.scalar_one_or_none()
        if not project:
            return False

        await self._session.delete(project)
        await self._session.commit()
        return True


class SQLAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, id: UUID, tenant_id: UUID) -> DocumentResponse | None:
        """Get document by ID with mandatory tenant isolation.

        SECURITY: tenant_id is mandatory. Query will fail if tenant_id is not provided.
        """
        if not tenant_id:
            raise SecurityException("tenant_id is required for document access")

        # SECURITY: Always filter by tenant_id - join with Project to enforce isolation
        query = (
            select(Document)
            .join(Project)  # Join required for tenant filtering
            .where(Document.id == id)
            .where(Project.tenant_id == tenant_id)
        )
        result = await self._session.execute(query)
        doc = result.scalar_one_or_none()
        if doc:
            return DocumentResponse.model_validate(doc)
        return None

    async def get_by_project(self, project_id: UUID, tenant_id: UUID) -> list[DocumentResponse]:
        """Get documents by project_id with mandatory tenant isolation.

        SECURITY: tenant_id is mandatory. Query will fail if tenant_id is not provided.
        """
        if not tenant_id:
            raise SecurityException("tenant_id is required for document access")

        # SECURITY: Always filter by tenant_id - join with Project to enforce isolation
        query = (
            select(Document)
            .join(Project)  # Join required for tenant filtering
            .where(Document.project_id == project_id)
            .where(Project.tenant_id == tenant_id)
            .order_by(Document.created_at.desc())
        )
        result = await self._session.execute(query)
        docs = result.scalars().all()
        return [DocumentResponse.model_validate(d) for d in docs]

    async def create(self, project_id: UUID, data: dict) -> DocumentResponse:
        document = Document(project_id=project_id, **data)
        self._session.add(document)
        await self._session.commit()
        await self._session.refresh(document)
        return DocumentResponse.model_validate(document)

    async def update_status(self, id: UUID, status: str, tenant_id: UUID) -> DocumentResponse | None:
        """Update document status with mandatory tenant isolation.

        SECURITY: tenant_id is mandatory. Will return None if document does not belong to tenant.
        """
        if not tenant_id:
            raise SecurityException("tenant_id is required for document update")

        # SECURITY: Verify document belongs to tenant before updating
        query = (
            select(Document)
            .join(Project)
            .where(Document.id == id)
            .where(Project.tenant_id == tenant_id)
        )
        result = await self._session.execute(query)
        doc = result.scalar_one_or_none()
        if not doc:
            return None
        doc.status = status
        await self._session.commit()
        await self._session.refresh(doc)
        return DocumentResponse.model_validate(doc)

    async def delete(self, id: UUID, tenant_id: UUID) -> bool:
        """Delete document with mandatory tenant isolation."""
        if not tenant_id:
            raise SecurityException("tenant_id is required for document deletion")
        
        query = (
            select(Document)
            .join(Project)
            .where(Document.id == id)
            .where(Project.tenant_id == tenant_id)
        )
        result = await self._session.execute(query)
        doc = result.scalar_one_or_none()
        if not doc:
            return False
        
        await self._session.delete(doc)
        await self._session.commit()
        return True


class SQLAlchemyQuestionRepository(QuestionRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_project(self, project_id: UUID, tenant_id: UUID) -> list[Question]:
        """Get questions by project_id with mandatory tenant isolation."""
        if not tenant_id:
            raise SecurityException("tenant_id is required for question access")

        query = (
            select(Question)
            .join(Project)
            .where(Question.project_id == project_id)
            .where(Project.tenant_id == tenant_id)
            .order_by(Question.priority.desc(), Question.created_at)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_document(self, document_id: UUID, tenant_id: UUID) -> list[Question]:
        """Get questions by document_id with mandatory tenant isolation."""
        if not tenant_id:
            raise SecurityException("tenant_id is required for question access")

        query = (
            select(Question)
            .join(Document)
            .join(Project)
            .where(Question.document_id == document_id)
            .where(Project.tenant_id == tenant_id)
            .order_by(Question.priority.desc(), Question.created_at)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create_many(
        self, project_id: UUID, questions: list[dict]
    ) -> list[QuestionResponse]:
        created = []
        for q_data in questions:
            question = Question(project_id=project_id, **q_data)
            self._session.add(question)
            created.append(question)
        await self._session.commit()
        for question in created:
            await self._session.refresh(question)
        # Criar QuestionResponse manualmente para evitar from_attributes issues
        return [
            QuestionResponse(
                id=q.id,
                project_id=q.project_id,
                document_id=q.document_id,
                question_text=q.question_text,
                category=q.category,
                priority=q.priority,
                question_metadata=q.question_metadata or {},
                created_at=q.created_at,
            )
            for q in created
        ]


class SQLAlchemyAnswerRepository(AnswerRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_question(self, question_id: UUID, tenant_id: UUID) -> AnswerResponse | None:
        """Get answer by question_id with mandatory tenant isolation."""
        if not tenant_id:
            raise SecurityException("tenant_id is required for answer access")

        query = (
            select(Answer)
            .join(Question)
            .join(Project)
            .where(Answer.question_id == question_id)
            .where(Project.tenant_id == tenant_id)
        )
        result = await self._session.execute(query)
        answer = result.scalar_one_or_none()
        if answer:
            return AnswerResponse.model_validate(answer)
        return None

    async def create(self, question_id: UUID, data: dict) -> AnswerResponse:
        answer = Answer(question_id=question_id, **data)
        self._session.add(answer)
        await self._session.commit()
        await self._session.refresh(answer)
        return AnswerResponse.model_validate(answer)

    async def update(self, id: UUID, data: dict, tenant_id: UUID) -> AnswerResponse | None:
        """Update answer with mandatory tenant isolation."""
        if not tenant_id:
            raise SecurityException("tenant_id is required for answer update")

        query = (
            select(Answer)
            .join(Question)
            .join(Project)
            .where(Answer.id == id)
            .where(Project.tenant_id == tenant_id)
        )
        result = await self._session.execute(query)
        answer = result.scalar_one_or_none()
        if not answer:
            return None
        for key, value in data.items():
            setattr(answer, key, value)
        await self._session.commit()
        await self._session.refresh(answer)
        return AnswerResponse.model_validate(answer)

    async def create_or_update(self, question_id: UUID, data: dict, tenant_id: UUID) -> AnswerResponse:
        """Create or update answer for a question."""
        # Check if answer exists
        existing = await self.get_by_question(question_id, tenant_id)
        if existing:
            # Update existing
            return await self.update(existing.id, data, tenant_id)
        else:
            # Create new
            return await self.create(question_id, data)

    async def delete(self, id: UUID, tenant_id: UUID) -> bool:
        """Delete answer with mandatory tenant isolation."""
        if not tenant_id:
            raise SecurityException("tenant_id is required for answer delete")

        from sqlalchemy import delete as sql_delete

        query = (
            select(Answer)
            .join(Question)
            .join(Project)
            .where(Answer.id == id)
            .where(Project.tenant_id == tenant_id)
        )
        result = await self._session.execute(query)
        answer = result.scalar_one_or_none()
        if not answer:
            return False

        await self._session.delete(answer)
        await self._session.commit()
        return True


class SQLAlchemyKnowledgeBaseRepository(KnowledgeBaseRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def search(
        self, tenant_id: UUID, query: str, limit: int = 10
    ) -> list[KnowledgeBaseResponse]:
        # Placeholder - actual vector search implemented in service layer
        result = await self._session.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.tenant_id == tenant_id)
            .where(KnowledgeBase.approved == True)
            .limit(limit)
        )
        entries = result.scalars().all()
        return [KnowledgeBaseResponse.model_validate(e) for e in entries]

    async def create(
        self, tenant_id: UUID, created_by: UUID, data: dict
    ) -> KnowledgeBaseResponse:
        entry = KnowledgeBase(
            tenant_id=tenant_id, created_by=created_by, **data
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return KnowledgeBaseResponse.model_validate(entry)


class SQLAlchemyAuditLogRepository(AuditLogRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, data: dict) -> AuditLogResponse:
        log = AuditLog(**data)
        self._session.add(log)
        await self._session.commit()
        await self._session.refresh(log)
        return AuditLogResponse.model_validate(log)

    async def get_by_tenant(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[AuditLogResponse]:
        result = await self._session.execute(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        logs = result.scalars().all()
        return [AuditLogResponse.model_validate(log) for log in logs]

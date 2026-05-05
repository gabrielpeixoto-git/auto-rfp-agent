from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

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

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> T | None:
        pass

    @abstractmethod
    async def create(self, data: dict) -> T:
        pass

    @abstractmethod
    async def update(self, id: UUID, data: dict) -> T | None:
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        pass


class TenantRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> TenantResponse | None:
        pass

    @abstractmethod
    async def create(self, name: str) -> TenantResponse:
        pass


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> UserResponse | None:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> UserResponse | None:
        pass

    @abstractmethod
    async def create(self, email: str, password_hash: str, role: str, tenant_id: UUID) -> UserResponse:
        pass


class ProjectRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID, tenant_id: UUID) -> ProjectResponse | None:
        """
        Get project by ID - REQUIRES tenant_id for security.
        
        Raises:
            ValueError: If tenant_id is not provided
        """
        pass

    @abstractmethod
    async def get_by_tenant(self, tenant_id: UUID, skip: int = 0, limit: int = 100) -> list[ProjectResponse]:
        pass

    @abstractmethod
    async def create(self, tenant_id: UUID, data: dict) -> ProjectResponse:
        pass

    @abstractmethod
    async def update(self, id: UUID, tenant_id: UUID, data: dict) -> ProjectResponse | None:
        """
        Update project - REQUIRES tenant_id for security verification.
        
        Raises:
            ValueError: If tenant_id is not provided
        """
        pass

    @abstractmethod
    async def delete(self, id: UUID, tenant_id: UUID) -> bool:
        """
        Delete project - REQUIRES tenant_id for security verification.
        
        Raises:
            ValueError: If tenant_id is not provided
        """
        pass


class DocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID, tenant_id: UUID) -> DocumentResponse | None:
        """
        Get document by ID - REQUIRES tenant_id for security.
        
        Raises:
            ValueError: If tenant_id is not provided
        """
        pass

    @abstractmethod
    async def get_by_project(
        self, project_id: UUID, tenant_id: UUID
    ) -> list[DocumentResponse]:
        """
        Get documents by project - REQUIRES tenant_id for security.
        
        Raises:
            ValueError: If tenant_id is not provided
        """
        pass

    @abstractmethod
    async def create(self, project_id: UUID, data: dict) -> DocumentResponse:
        pass

    @abstractmethod
    async def update_status(
        self, id: UUID, tenant_id: UUID, status: str
    ) -> DocumentResponse | None:
        """
        Update document status - REQUIRES tenant_id for security verification.
        
        Raises:
            ValueError: If tenant_id is not provided
        """
        pass

    @abstractmethod
    async def delete(self, id: UUID, tenant_id: UUID) -> bool:
        """
        Delete document - REQUIRES tenant_id for security verification.
        
        Raises:
            ValueError: If tenant_id is not provided
        """
        pass


class QuestionRepository(ABC):
    @abstractmethod
    async def get_by_project(self, project_id: UUID, tenant_id: UUID) -> list[QuestionResponse]:
        """
        Get questions by project - REQUIRES tenant_id for security.
        
        Raises:
            ValueError: If tenant_id is not provided
        """
        pass

    @abstractmethod
    async def get_by_document(self, document_id: UUID, tenant_id: UUID) -> list[QuestionResponse]:
        """
        Get questions by document - REQUIRES tenant_id for security.
        
        Raises:
            ValueError: If tenant_id is not provided
        """
        pass

    @abstractmethod
    async def create_many(self, project_id: UUID, questions: list[dict]) -> list[QuestionResponse]:
        pass


class AnswerRepository(ABC):
    @abstractmethod
    async def get_by_question(
        self, question_id: UUID, tenant_id: UUID
    ) -> AnswerResponse | None:
        """
        Get answer by question - REQUIRES tenant_id for security.
        
        Raises:
            ValueError: If tenant_id is not provided
        """
        pass

    @abstractmethod
    async def create(self, question_id: UUID, data: dict) -> AnswerResponse:
        pass

    @abstractmethod
    async def update(
        self, id: UUID, tenant_id: UUID, data: dict
    ) -> AnswerResponse | None:
        """
        Update answer - REQUIRES tenant_id for security verification.
        
        Raises:
            ValueError: If tenant_id is not provided
        """
        pass

    @abstractmethod
    async def delete(self, id: UUID, tenant_id: UUID) -> bool:
        """
        Delete answer - REQUIRES tenant_id for security verification.
        
        Raises:
            ValueError: If tenant_id is not provided
        """
        pass


class KnowledgeBaseRepository(ABC):
    @abstractmethod
    async def search(
        self, tenant_id: UUID, query: str, limit: int = 10
    ) -> list[KnowledgeBaseResponse]:
        pass

    @abstractmethod
    async def create(self, tenant_id: UUID, created_by: UUID, data: dict) -> KnowledgeBaseResponse:
        pass


class AuditLogRepository(ABC):
    @abstractmethod
    async def create(self, data: dict) -> AuditLogResponse:
        pass

    @abstractmethod
    async def get_by_tenant(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[AuditLogResponse]:
        pass

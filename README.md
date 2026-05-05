# Auto-RFP Agent

AI-powered SaaS B2B platform for processing RFPs, RFIs, DDQs, and security questionnaires.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Smart Document Processing**: Upload and parse PDFs, DOCX, XLSX, and TXT files with automatic question extraction
- **AI Answer Generation**: RAG-powered responses with source citations from your knowledge base
- **Local AI Support**: 100% local LLM option with Ollama (no API costs!)
- **Multi-tenant Architecture**: Complete isolation between organizations
- **RBAC Security**: Role-based access control (admin, manager, analyst, viewer)
- **Security Hardening**: XSS protection, rate limiting, security headers, audit logging
- **Human Review Workflow**: Edit, approve, and audit all AI-generated content
- **Async Processing**: Celery background tasks with Flower monitoring

## Tech Stack

| Camada | Tecnologias |
|--------|-------------|
| **Frontend** | Next.js 14 + TypeScript + TailwindCSS + shadcn/ui |
| **Backend** | FastAPI + Python 3.11+ + Pydantic v2 + SQLAlchemy 2.0 |
| **Database** | PostgreSQL 15 + pgvector (embeddings) |
| **Cache/Jobs** | Redis + Celery + Flower |
| **AI Options** | Ollama (local), OpenAI, Groq, Anthropic |
| **Security** | JWT tokens, httpOnly cookies, RBAC, rate limiting |
| **Deploy** | Docker Compose (dev + production ready) |

## Project Structure

```
auto-rfp-agent/
├── docker-compose.yml
├── .env.example
├── app/
│   ├── api/                    # FastAPI backend
│   │   ├── src/
│   │   │   ├── main.py         # FastAPI app
│   │   │   ├── core/           # Config, logging, security
│   │   │   ├── domain/         # Entities, schemas, enums
│   │   │   ├── services/       # Business logic
│   │   │   ├── infrastructure/ # DB, AI, repositories
│   │   │   ├── api/            # Routers, controllers
│   │   │   └── workers/        # Celery tasks
│   │   └── tests/
│   └── web/                    # Next.js frontend
│       ├── app/                # App router
│       └── components/
└── init-scripts/               # PostgreSQL init
```

## Architecture

### Domain Layer
- Enums: UserRole, ProjectStatus, DocumentType, etc.
- Schemas: Pydantic models for input/output
- Interfaces: Repository contracts
- Exceptions: Domain-specific errors

### Service Layer
- AuthService: JWT authentication
- ProjectService: Project CRUD with RBAC
- DocumentService: Upload and processing
- RAGService: AI answer generation

### Infrastructure Layer
- SQLAlchemy models + async repositories
- OpenAI/Anthropic provider abstraction
- pgvector for semantic search
- Celery for async processing

### API Layer
- RESTful routers with dependency injection
- JWT authentication with tenant isolation
- Structured error handling

## Pipeline

```
Upload → Parse → Chunk → Embed → Index
                            ↓
                    Question Extraction
                            ↓
                    RAG Answer Generation
                            ↓
                    Human Review
                            ↓
                    Export/Approval
```

## API Endpoints

### Auth
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/tenants` - Create tenant

### Projects
- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}` - Get project
- `PATCH /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Documents
- `GET /api/v1/documents/project/{id}` - List documents
- `POST /api/v1/documents/upload/{project_id}` - Upload document
- `GET /api/v1/documents/{id}` - Get document
- `DELETE /api/v1/documents/{id}` - Delete document

### Answers
- `GET /api/v1/answers/project/{id}` - Get project answers
- `PATCH /api/v1/answers/{id}` - Update answer
- `POST /api/v1/answers/project/{id}/generate` - Trigger generation

### Audit
- `GET /api/v1/audit/logs` - List audit logs

## Quick Start (Docker - Recommended)

### Prerequisites
- Docker + Docker Compose
- Git

### Setup

1. Clone the repository:
```bash
git clone https://github.com/<SEU_USUARIO>/auto-rfp-agent.git
cd auto-rfp-agent
```

> ⚠️ **Importante**: Verifique se não há arquivos temporários antes de commitar:  
> Delete manualmente se existirem: `.env`, `token.txt`, scripts `test_*.py`, `debug_*.py`, etc.

### 1. AI Provider Setup

**Option 1: Ollama (Recommended - 100% FREE, local AI)**
```bash
# 1. Install Ollama: https://ollama.com/download
# 2. Pull required models:
ollama pull llama3.1
ollama pull nomic-embed-text
# 3. Ensure Ollama is running on http://localhost:11434
```

**Option 2: OpenAI (Cloud API)**
- Get your API key at: https://platform.openai.com/api-keys

### 2. Clone and Configure
```bash
git clone <your-repo-url>
cd auto-rfp-agent
cp .env.example .env
# Edit .env with your settings
```

### 3. Start Services
```bash
docker-compose up -d
```

### 4. Access
| Service | URL | Description |
|---------|-----|-------------|
| Web UI | http://localhost:3000 | Frontend application |
| API | http://localhost:8000 | Backend API |
| API Docs | http://localhost:8000/docs | Swagger documentation |
| Flower | http://localhost:5555 | Celery task monitor |

### First Steps
1. Register at http://localhost:3000/register
2. Create your first project
3. Upload an RFP document (PDF, DOCX, XLSX)
4. Wait for AI processing
5. Review and export AI-generated answers

## Development (without Docker)

### Backend
```bash
cd app/api
pip install -e ".[dev]"

# Configure environment
cp ../../.env.example ../../.env
# Edit .env with local settings

# Run database migrations
alembic upgrade head

# Start API
uvicorn src.main:app --reload --port 8000
```

### Frontend
```bash
cd app/web
npm install
npm run dev
```

### Celery Worker
```bash
cd app/api
celery -A src.workers.celery_app worker --loglevel=info
```

### Run Tests
```bash
cd app/api
pytest
```

## Deployment

1. Build images:
```bash
docker-compose build
```

2. Production env:
```bash
# Update .env with production values
ENVIRONMENT=production
SECRET_KEY=<strong-random-key>
```

3. Deploy:
```bash
docker-compose -f docker-compose.yml up -d
```

## Roadmap

- [x] Core backend with FastAPI
- [x] Multi-tenant RBAC
- [x] Document upload and parsing
- [x] RAG answer generation
- [x] Basic Next.js frontend
- [ ] Advanced document parsing (tables, images)
- [ ] Version control for answers
- [ ] Export to PDF/Word
- [ ] Analytics dashboard
- [ ] Slack/Teams integration
- [ ] Production cloud deployment (AWS/GCP)

## License

MIT

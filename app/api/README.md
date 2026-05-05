# Auto-RFP Agent API

FastAPI backend for Auto-RFP Agent - AI-powered RFP processing SaaS.

## Features

- Document parsing (PDF, DOCX, XLSX, TXT)
- RAG-based answer generation with Ollama (local LLM)
- Multi-tenant architecture with RBAC
- Async processing with Celery
- PostgreSQL + pgvector for embeddings

## Tech Stack

- FastAPI + Python 3.11
- SQLAlchemy 2.0 + asyncpg
- Celery + Redis
- Ollama (llama3.1 + nomic-embed-text)

## Development

```bash
pip install -e ".[dev]"
uvicorn src.main:app --reload
```

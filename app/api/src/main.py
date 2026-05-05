"""Auto-RFP Agent API - FastAPI Application"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import settings
from src.core.logging_config import configure_logging, get_logger
from src.infrastructure.database.connection import init_db
from src.infrastructure.middleware.rate_limiter import RateLimitMiddleware
from src.infrastructure.middleware.security_headers import (
    SecurityHeadersMiddleware,
    AuditLogMiddleware,
)
from src.infrastructure.middleware.xss_protection import XSSProtectionMiddleware
from src.api.health import router as health
from src.api.auth import router as auth
from src.api.projects import router as projects
from src.api.documents import router as documents
from src.api.questions import router as questions
from src.api.answers import router as answers
from src.api.export import router as export
from src.api.audit import router as audit

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Auto-RFP Agent API", version="0.1.0")
    
    # Initialize database
    await init_db()
    
    yield
    
    # Cleanup
    logger.info("Shutting down Auto-RFP Agent API")


# Create FastAPI app
app = FastAPI(
    title="Auto-RFP Agent API",
    description="AI-powered RFP/RFI/DDQ processing platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,  # Disable docs in production
    redoc_url="/redoc" if not settings.is_production else None,
)

# XSS Protection middleware (must be first for CSP headers)
app.add_middleware(XSSProtectionMiddleware)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Audit logging middleware
app.add_middleware(AuditLogMiddleware)

# Rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    auth_limit=5,  # 5 auth attempts per minute
    auth_window=60,
    general_limit=100,  # 100 requests per minute
    general_window=60,
    ai_limit=10,  # 10 AI requests per minute
    ai_window=60
)

# CORS middleware - RESTRICTIVE configuration
# In production, ONLY allow specific origins
cors_origins = getattr(settings, 'cors_origins', None)
if not cors_origins:
    if settings.is_production:
        # Production: NO wildcard allowed
        cors_origins = []  # Must be configured explicitly
    else:
        # Development only
        cors_origins = ["http://localhost:3000", "http://localhost:3001"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # NEVER use ["*"] in production
    allow_credentials=True,  # Required for httpOnly cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        # "X-Refresh-Token" removed - refresh token now in httpOnly cookie
    ],
    expose_headers=[
        "X-Total-Count",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset"
    ],
    max_age=600,
)


# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    import traceback
    error_details = traceback.format_exc()
    
    # Log security-relevant exceptions
    if isinstance(exc, PermissionError):
        logger.warning(
            "Permission denied",
            path=request.url.path,
            method=request.method,
            client_ip=request.client.host if request.client else "unknown"
        )
    else:
        logger.error(
            "Unhandled exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
            traceback=error_details,
        )
    
    # Don't leak internal errors in production
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__ if settings.is_development else "InternalError",
            "error": str(exc) if settings.is_development else "An unexpected error occurred",
        },
    )


# Include routers
app.include_router(health, prefix="/api/v1")
app.include_router(auth, prefix="/api/v1")
app.include_router(projects, prefix="/api/v1")
app.include_router(documents, prefix="/api/v1")
app.include_router(questions, prefix="/api/v1")
app.include_router(answers, prefix="/api/v1")
app.include_router(export, prefix="/api/v1")
app.include_router(audit, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": "Auto-RFP Agent API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)

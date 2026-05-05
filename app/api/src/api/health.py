from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from redis import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db
from src.core.config import settings
from src.core.logging_config import get_logger
from src.domain.schemas import HealthResponse

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    session: AsyncSession = Depends(get_db),
):
    """Health check endpoint."""
    services = {
        "database": "down",
        "redis": "down",
    }
    
    # Check database
    try:
        result = await session.execute(text("SELECT 1"))
        services["database"] = "up"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
    
    # Check Redis
    try:
        redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        redis_client.ping()
        services["redis"] = "up"
        redis_client.close()
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
    
    # Determine overall status
    if all(s == "up" for s in services.values()):
        status_val = "healthy"
    elif any(s == "up" for s in services.values()):
        status_val = "degraded"
    else:
        status_val = "unhealthy"
    
    return HealthResponse(
        status=status_val,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
        services=services,
    )


@router.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes."""
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """Liveness probe for Kubernetes."""
    return {"alive": True}

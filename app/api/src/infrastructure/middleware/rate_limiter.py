"""Rate limiting middleware for API endpoints."""

import time
from typing import Callable
from uuid import UUID

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.logging_config import get_logger
from src.infrastructure.cache.token_cache import token_cache

logger = get_logger(__name__)


class RateLimiter:
    """Redis-based rate limiter."""
    
    def __init__(self):
        self._redis = None
    
    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            import redis.asyncio as redis
            from src.core.config import settings
            self._redis = await redis.from_url(
                settings.redis_url,
                decode_responses=True
            )
        return self._redis
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int  # seconds
    ) -> tuple[bool, dict]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Rate limit key (e.g., IP address or user ID)
            limit: Maximum number of requests
            window: Time window in seconds
        
        Returns:
            tuple of (is_allowed, rate_limit_info)
        """
        redis_client = await self._get_redis()
        now = int(time.time())
        window_start = now - window
        
        # Remove old entries
        await redis_client.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        current = await redis_client.zcard(key)
        
        if current >= limit:
            # Get oldest request to calculate retry-after
            oldest = await redis_client.zrange(key, 0, 0, withscores=True)
            retry_after = int(oldest[0][1] + window - now) if oldest else window
            
            return False, {
                "limit": limit,
                "remaining": 0,
                "reset": oldest[0][1] + window if oldest else now + window,
                "retry_after": max(1, retry_after)
            }
        
        # Add current request
        await redis_client.zadd(key, {str(now): now})
        await redis_client.expire(key, window)
        
        return True, {
            "limit": limit,
            "remaining": limit - current - 1,
            "reset": now + window
        }


# Global instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting API requests."""
    
    def __init__(
        self,
        app: ASGIApp,
        auth_limit: int = 5,  # 5 attempts
        auth_window: int = 60,  # per minute
        general_limit: int = 100,  # 100 requests
        general_window: int = 60,  # per minute
        ai_limit: int = 10,  # 10 AI requests
        ai_window: int = 60  # per minute
    ):
        super().__init__(app)
        self.auth_limit = auth_limit
        self.auth_window = auth_window
        self.general_limit = general_limit
        self.general_window = general_window
        self.ai_limit = ai_limit
        self.ai_window = ai_window
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_auth_endpoint(self, path: str) -> bool:
        """Check if path is an authentication endpoint."""
        return path.startswith("/api/v1/auth/login") or \
               path.startswith("/api/v1/auth/register")
    
    def _is_ai_endpoint(self, path: str) -> bool:
        """Check if path is an AI/RAG endpoint."""
        return "/generate" in path or "/process" in path or "/rag" in path
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        path = request.url.path
        client_ip = self._get_client_ip(request)
        
        # Determine rate limit based on endpoint
        if self._is_auth_endpoint(path):
            limit = self.auth_limit
            window = self.auth_window
            key = f"rate_limit:auth:{client_ip}"
            endpoint_type = "auth"
        elif self._is_ai_endpoint(path):
            limit = self.ai_limit
            window = self.ai_window
            key = f"rate_limit:ai:{client_ip}"
            endpoint_type = "ai"
        else:
            limit = self.general_limit
            window = self.general_window
            key = f"rate_limit:general:{client_ip}"
            endpoint_type = "general"
        
        # Check rate limit
        is_allowed, rate_info = await rate_limiter.is_allowed(key, limit, window)
        
        if not is_allowed:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                endpoint=path,
                endpoint_type=endpoint_type,
                limit=limit,
                window=window
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": rate_info["retry_after"]
                },
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(rate_info["reset"])),
                    "Retry-After": str(rate_info["retry_after"])
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(rate_info["reset"]))
        
        return response


# Decorator for endpoint-specific rate limiting
def rate_limit(limit: int, window: int, key_func: Callable = None):
    """
    Decorator to apply rate limiting to specific endpoints.
    
    Args:
        limit: Maximum number of requests
        window: Time window in seconds
        key_func: Function to extract rate limit key from request
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs or args
            request = kwargs.get('request')
            if not request and args:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if request:
                if key_func:
                    key = key_func(request)
                else:
                    # Default: use client IP
                    forwarded = request.headers.get("X-Forwarded-For")
                    if forwarded:
                        ip = forwarded.split(",")[0].strip()
                    elif request.headers.get("X-Real-IP"):
                        ip = request.headers.get("X-Real-IP")
                    elif request.client:
                        ip = request.client.host
                    else:
                        ip = "unknown"
                    key = f"rate_limit:decorator:{ip}:{request.url.path}"
                
                is_allowed, rate_info = await rate_limiter.is_allowed(key, limit, window)
                
                if not is_allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded. Please try again later.",
                        headers={
                            "Retry-After": str(rate_info["retry_after"])
                        }
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

"""Security headers middleware for production hardening."""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    
    These headers help protect against common web vulnerabilities:
    - XSS attacks
    - Clickjacking
    - MIME-type sniffing
    - Information leakage
    """
    
    def __init__(
        self,
        app: ASGIApp,
        csp_policy: str | None = None
    ):
        super().__init__(app)
        # Default Content Security Policy
        self.csp_policy = csp_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "camera=(), "
            "microphone=(), "
            "geolocation=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "speaker=()"
        )
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.csp_policy
        
        # Strict Transport Security (HTTPS only in production)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Remove server identification
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests for security audit."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        from src.core.logging_config import get_logger
        self.logger = get_logger(__name__)
    
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
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request details."""
        import time
        
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log request (skip health checks)
        path = request.url.path
        if not path.endswith("/health") and not path.endswith("/ready") and not path.endswith("/live"):
            self.logger.info(
                "API request",
                method=request.method,
                path=path,
                status_code=response.status_code,
                client_ip=client_ip,
                user_agent=request.headers.get("User-Agent"),
                duration_ms=round(duration * 1000, 2),
                content_length=response.headers.get("Content-Length"),
            )
            
            # Log security events for suspicious activity
            if response.status_code in (401, 403):
                self.logger.warning(
                    "Security event - unauthorized access attempt",
                    method=request.method,
                    path=path,
                    status_code=response.status_code,
                    client_ip=client_ip,
                    user_agent=request.headers.get("User-Agent"),
                )
        
        return response

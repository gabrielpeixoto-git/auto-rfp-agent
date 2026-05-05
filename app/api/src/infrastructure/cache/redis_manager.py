"""
Redis connection manager with circuit breaker pattern.

Implements safe-fail behavior: if Redis is unavailable, deny requests
that depend on Redis (like token validation) rather than allowing them.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable
from uuid import UUID

import redis.asyncio as redis

from src.core.config import settings
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker pattern for Redis operations.
    
    - CLOSED: Normal operation, requests pass through
    - OPEN: After threshold failures, reject requests immediately
    - HALF_OPEN: After timeout, allow one test request
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,  # seconds
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: datetime | None = None
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Raises:
            RedisUnavailableException: If circuit is open
            Exception: If function fails
        """
        async with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self._last_failure_time:
                    elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
                    if elapsed >= self.recovery_timeout:
                        logger.info("Circuit breaker entering half-open state")
                        self._state = CircuitState.HALF_OPEN
                    else:
                        raise RedisUnavailableException(
                            f"Redis circuit breaker is OPEN. Retry after {self.recovery_timeout - elapsed:.0f}s"
                        )
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset circuit if half-open
            async with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    logger.info("Circuit breaker closed - Redis recovered")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._last_failure_time = None
            
            return result
            
        except self.expected_exception as e:
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = datetime.now(timezone.utc)
                
                if self._failure_count >= self.failure_threshold:
                    if self._state != CircuitState.OPEN:
                        logger.error(
                            "Circuit breaker opened due to repeated failures",
                            failure_count=self._failure_count,
                            last_error=str(e)
                        )
                        self._state = CircuitState.OPEN
            
            raise


class RedisUnavailableException(Exception):
    """Raised when Redis is unavailable and circuit breaker is open."""
    pass


class RedisManager:
    """
    Redis connection manager with circuit breaker.
    
    Implements safe-fail security behavior:
    - When Redis is unavailable, security-critical operations FAIL (deny access)
    - This prevents tokens from being accepted when we can't validate blacklists
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._redis = None
            cls._instance._circuit_breaker = CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=30
            )
            cls._instance._healthy = False
        return cls._instance
    
    async def _get_connection(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                self._redis = await redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
                # Test connection
                await self._redis.ping()
                self._healthy = True
                logger.info("Redis connection established")
            except Exception as e:
                self._healthy = False
                logger.error("Failed to connect to Redis", error=str(e))
                raise
        return self._redis
    
    async def execute(self, operation: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a Redis operation with circuit breaker protection.
        
        Args:
            operation: Name of operation for logging
            func: Redis operation function
            
        Returns:
            Operation result
            
        Raises:
            RedisUnavailableException: If Redis is unavailable (circuit open)
        """
        try:
            return await self._circuit_breaker.call(self._execute_with_retry, operation, func, *args, **kwargs)
        except RedisUnavailableException:
            # Log security implication
            logger.error(
                "Redis unavailable - security operation blocked",
                operation=operation,
                circuit_state=self._circuit_breaker.state.value
            )
            raise
        except Exception as e:
            logger.error(
                "Redis operation failed",
                operation=operation,
                error=str(e)
            )
            raise
    
    async def _execute_with_retry(
        self,
        operation: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute Redis operation with retry logic."""
        redis_conn = await self._get_connection()
        
        try:
            return await func(redis_conn, *args, **kwargs)
        except redis.ConnectionError as e:
            logger.warning("Redis connection error, attempting reconnect", error=str(e))
            # Reset connection and retry once
            self._redis = None
            redis_conn = await self._get_connection()
            return await func(redis_conn, *args, **kwargs)
    
    async def health_check(self) -> dict:
        """Check Redis health status."""
        try:
            if self._redis:
                await self._redis.ping()
                return {
                    "status": "healthy",
                    "circuit_state": self._circuit_breaker.state.value,
                    "connected": True
                }
            else:
                return {
                    "status": "disconnected",
                    "circuit_state": self._circuit_breaker.state.value,
                    "connected": False
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "circuit_state": self._circuit_breaker.state.value,
                "connected": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._healthy = False


# Global instance
redis_manager = RedisManager()


class SafeTokenCache:
    """
    Token cache with safe-fail behavior.
    
    When Redis is unavailable:
    - Token validation FAILS (token is considered invalid)
    - This prevents security bypass when we can't check blacklists
    """
    
    async def _execute_or_fail_secure(self, operation: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute Redis operation or fail securely.
        
        For security operations, we prefer to deny access when Redis is down
        rather than risk allowing revoked tokens.
        """
        try:
            return await redis_manager.execute(operation, func, *args, **kwargs)
        except RedisUnavailableException:
            # For token validation - fail securely (deny)
            if "token" in operation.lower() and "blacklist" in operation.lower():
                logger.warning(
                    "Redis unavailable - assuming token is blacklisted (fail secure)",
                    operation=operation
                )
                return True  # Consider it blacklisted = deny access
            
            if "refresh" in operation.lower():
                logger.warning(
                    "Redis unavailable - rejecting refresh token (fail secure)",
                    operation=operation
                )
                return False  # Token invalid = deny refresh
            
            # Re-raise for other operations
            raise
    
    async def store_refresh_token(
        self,
        user_id: UUID,
        token_jti: str,
        expires_in: int = 60 * 60 * 24 * 7
    ) -> None:
        """Store refresh token with retry."""
        async def _store(redis_conn):
            key = f"refresh_token:{user_id}:{token_jti}"
            await redis_conn.setex(key, expires_in, "valid")
        
        await self._execute_or_fail_secure("store_refresh_token", _store)
    
    async def validate_refresh_token(self, user_id: UUID, token_jti: str) -> bool:
        """
        Validate refresh token.
        
        If Redis is unavailable, returns False (fail secure).
        """
        async def _validate(redis_conn):
            key = f"refresh_token:{user_id}:{token_jti}"
            return await redis_conn.exists(key) == 1
        
        try:
            return await self._execute_or_fail_secure("validate_refresh_token", _validate)
        except RedisUnavailableException:
            return False  # Fail secure - reject token
    
    async def revoke_refresh_token(self, user_id: UUID, token_jti: str) -> None:
        """Revoke a refresh token."""
        async def _revoke(redis_conn):
            key = f"refresh_token:{user_id}:{token_jti}"
            await redis_conn.delete(key)
        
        await self._execute_or_fail_secure("revoke_refresh_token", _revoke)
    
    async def blacklist_access_token(self, token_jti: str, expires_in: int) -> None:
        """Blacklist an access token."""
        async def _blacklist(redis_conn):
            key = f"blacklist:access_token:{token_jti}"
            await redis_conn.setex(key, expires_in, "revoked")
        
        await self._execute_or_fail_secure("blacklist_access_token", _blacklist)
    
    async def is_access_token_blacklisted(self, token_jti: str) -> bool:
        """
        Check if access token is blacklisted.
        
        If Redis is unavailable, returns True (fail secure - assume blacklisted).
        """
        async def _check(redis_conn):
            key = f"blacklist:access_token:{token_jti}"
            return await redis_conn.exists(key) == 1
        
        try:
            return await self._execute_or_fail_secure("check_blacklist", _check)
        except RedisUnavailableException:
            # Fail secure - assume token is blacklisted (deny access)
            logger.warning(
                "Cannot check token blacklist - assuming blacklisted",
                token_jti=token_jti[:8] + "..."
            )
            return True


# Global safe token cache instance
safe_token_cache = SafeTokenCache()

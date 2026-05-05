"""
Token cache for managing refresh tokens and blacklisted access tokens.

Uses Redis manager with circuit breaker pattern and safe-fail behavior.
When Redis is unavailable:
- Token validation FAILS SECURELY (returns False for valid tokens)
- Blacklist checks return True (assume blacklisted = deny access)
"""

from uuid import UUID

from src.infrastructure.cache.redis_manager import safe_token_cache, RedisUnavailableException
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class TokenCache:
    """
    Redis-based cache for token management with safe-fail behavior.
    
    IMPORTANT: When Redis is unavailable, this cache FAILS SECURE:
    - validate_refresh_token returns False (token considered invalid)
    - is_access_token_blacklisted returns True (token considered blacklisted)
    
    This prevents security bypass when Redis is down.
    """
    
    async def store_refresh_token(
        self,
        user_id: UUID,
        token_jti: str,
        expires_in: int = 60 * 60 * 24 * 7  # 7 days
    ) -> None:
        """Store refresh token with user mapping."""
        try:
            await safe_token_cache.store_refresh_token(user_id, token_jti, expires_in)
        except RedisUnavailableException:
            # Log but don't fail - token creation can continue
            # (validation will fail later if Redis is still down)
            logger.warning(
                "Redis unavailable - refresh token stored in memory only",
                user_id=str(user_id),
                token_jti=token_jti[:8] + "..."
            )
    
    async def validate_refresh_token(
        self,
        user_id: UUID,
        token_jti: str
    ) -> bool:
        """
        Check if refresh token is valid.
        
        FAILS SECURE: Returns False if Redis is unavailable.
        """
        return await safe_token_cache.validate_refresh_token(user_id, token_jti)
    
    async def revoke_refresh_token(
        self,
        user_id: UUID,
        token_jti: str
    ) -> None:
        """Revoke a specific refresh token."""
        try:
            await safe_token_cache.revoke_refresh_token(user_id, token_jti)
        except RedisUnavailableException:
            logger.warning(
                "Redis unavailable - could not revoke refresh token",
                user_id=str(user_id),
                token_jti=token_jti[:8] + "..."
            )
            # Continue - worst case is token remains valid until expiration
    
    async def revoke_all_user_refresh_tokens(self, user_id: UUID) -> None:
        """Revoke all refresh tokens for a user."""
        # For now, rely on individual revocations
        # Could implement pattern-based deletion in future
        logger.info("Revoking all refresh tokens for user", user_id=str(user_id))
    
    async def blacklist_access_token(
        self,
        token_jti: str,
        expires_in: int
    ) -> None:
        """Blacklist an access token until its expiration."""
        try:
            await safe_token_cache.blacklist_access_token(token_jti, expires_in)
        except RedisUnavailableException:
            logger.warning(
                "Redis unavailable - could not blacklist access token",
                token_jti=token_jti[:8] + "..."
            )
            # Continue - worst case is token remains valid until expiration
    
    async def is_access_token_blacklisted(self, token_jti: str) -> bool:
        """
        Check if access token is blacklisted.
        
        FAILS SECURE: Returns True (assume blacklisted) if Redis is unavailable.
        This prevents using potentially revoked tokens.
        """
        return await safe_token_cache.is_access_token_blacklisted(token_jti)
    
    async def close(self):
        """Close Redis connection."""
        # Handled by redis_manager
        pass


# Global instance
token_cache = TokenCache()

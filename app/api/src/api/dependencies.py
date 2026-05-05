from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import UnauthorizedException
from src.domain.schemas import UserResponse
from src.infrastructure.database.connection import get_db
from src.core.security import decode_token, get_token_jti
from src.core.logging_config import get_logger
from src.infrastructure.database.repositories import SQLAlchemyUserRepository
from src.infrastructure.cache.token_cache import token_cache
from src.services.auth_service import AuthService

security = HTTPBearer()
logger = get_logger(__name__)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Extract and validate current user from JWT access token.
    
    Validates:
    - Token signature and expiration
    - Token type is 'access'
    - Token is not blacklisted
    - User exists and is active
    """
    token = credentials.credentials
    
    try:
        # Decode and validate token type
        payload = decode_token(token, token_type="access")
        
        # Check if token is blacklisted (revoked)
        token_jti = payload.get("jti")
        if token_jti:
            is_blacklisted = await token_cache.is_access_token_blacklisted(token_jti)
            if is_blacklisted:
                logger.warning(
                    "Token reuse attempt",
                    token_jti=token_jti,
                    token_preview=token[:20] + "..."
                )
                raise UnauthorizedException("Token has been revoked")
        
        user_id = UUID(payload.get("sub"))
        
        auth_service = AuthService(session)
        user = await auth_service.get_current_user(user_id)
        
        # Verify tenant matches token
        token_tenant_id = payload.get("tenant_id")
        if str(user.tenant_id) != token_tenant_id:
            logger.warning(
                "Tenant mismatch in token",
                user_id=str(user_id),
                user_tenant=str(user.tenant_id),
                token_tenant=token_tenant_id
            )
            raise UnauthorizedException("Invalid tenant context")
        
        return user
        
    except UnauthorizedException as e:
        # Log failed authentication attempt
        logger.warning(
            "Authentication failed",
            error=str(e.message),
            token_preview=token[:20] + "..." if token else "none",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # Log failed authentication attempt with error details
        logger.warning(
            "Authentication failed - invalid credentials",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def validate_refresh_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    """
    Validate a refresh token from Authorization header.
    
    Returns:
        Token payload if valid
        
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    
    try:
        # Decode and validate token type
        payload = decode_token(token, token_type="refresh")
        
        # Validate against Redis stored tokens
        user_id = UUID(payload.get("sub"))
        token_jti = payload.get("jti")
        
        if not await token_cache.validate_refresh_token(user_id, token_jti):
            logger.warning(
                "Invalid or revoked refresh token",
                user_id=str(user_id),
                token_jti=token_jti
            )
            raise UnauthorizedException("Invalid refresh token")
        
        return payload
        
    except UnauthorizedException as e:
        logger.warning("Refresh token validation failed", error=str(e.message))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.warning("Refresh token validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def validate_refresh_token_from_cookie(request: Request) -> dict:
    """
    Validate a refresh token from httpOnly cookie.
    
    This is the secure way to handle refresh tokens - not accessible to JavaScript.
    
    Returns:
        Token payload if valid
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    token = request.cookies.get("refresh_token")
    
    if not token:
        logger.warning("Refresh token cookie not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode and validate token type
        payload = decode_token(token, token_type="refresh")
        
        # Validate against Redis stored tokens
        user_id = UUID(payload.get("sub"))
        token_jti = payload.get("jti")
        
        if not await token_cache.validate_refresh_token(user_id, token_jti):
            logger.warning(
                "Invalid or revoked refresh token from cookie",
                user_id=str(user_id),
                token_jti=token_jti
            )
            raise UnauthorizedException("Invalid refresh token")
        
        return payload
        
    except UnauthorizedException as e:
        logger.warning("Refresh token cookie validation failed", error=str(e.message))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.warning("Refresh token cookie validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_with_context(
    user: Annotated[UserResponse, Depends(get_current_user)],
) -> tuple[UserResponse, UUID, UUID, str]:
    """Get user with tenant and role context for service injection."""
    return (user, user.id, user.tenant_id, user.role.value)


async def require_admin(
    user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    """Require admin role."""
    if user.role.value != "admin":
        # Log unauthorized access attempt
        logger.warning(
            "Unauthorized access attempt - admin required",
            user_id=str(user.id),
            user_role=user.role.value,
            tenant_id=str(user.tenant_id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def require_manager_or_above(
    user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    """Require manager or admin role."""
    if user.role.value not in ["admin", "manager"]:
        # Log unauthorized access attempt
        logger.warning(
            "Unauthorized access attempt - manager or admin required",
            user_id=str(user.id),
            user_role=user.role.value,
            tenant_id=str(user.tenant_id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or admin access required",
        )
    return user

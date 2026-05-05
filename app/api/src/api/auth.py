from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.domain.exceptions import AlreadyExistsException, UnauthorizedException
from src.domain.schemas import (
    AuthResponse,
    TenantCreate,
    TenantResponse,
    TokenPair,
    UserCreate,
    UserLogin,
    UserResponse,
)
from src.infrastructure.database.connection import get_db
from src.infrastructure.database.repositories import SQLAlchemyTenantRepository
from src.api.dependencies import (
    get_current_user,
    validate_refresh_token_from_cookie,
    security,
)
from src.services.auth_service import AuthService

# Cookie settings for refresh token
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days
COOKIE_PATH = "/api/v1/auth"

router = APIRouter(prefix="/auth", tags=["auth"])


def get_client_ip(request: Request) -> str | None:
    """Extract client IP address from request."""
    # Check for forwarded headers (when behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection
    if request.client:
        return request.client.host
    
    return None


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    response: Response,
    data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Register a new user with secure token handling.
    
    Refresh token is set as httpOnly cookie.
    Access token is returned in response body.
    """
    try:
        auth_service = AuthService(session)
        token_pair = await auth_service.register(data)
        
        # Set refresh token as httpOnly cookie
        _set_refresh_token_cookie(response, token_pair.refresh_token)
        
        # Return only access token in body
        return AuthResponse(
            user=token_pair.user,
            access_token=token_pair.access_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
        )
    except AlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    response: Response,
    data: UserLogin,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Login with secure token handling.
    
    Access token is returned in response body (short-lived, 15 minutes).
    Refresh token is set as httpOnly cookie (long-lived, 7 days).
    """
    client_ip = get_client_ip(request)
    
    try:
        auth_service = AuthService(session)
        token_pair = await auth_service.login(
            data.email,
            data.password,
            ip_address=client_ip
        )
        
        # Set refresh token as httpOnly cookie
        _set_refresh_token_cookie(response, token_pair.refresh_token)
        
        # Return only access token in body
        return AuthResponse(
            user=token_pair.user,
            access_token=token_pair.access_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
        )
    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    response: Response,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    refresh_payload: Annotated[dict, Depends(validate_refresh_token_from_cookie)],
):
    """
    Refresh access token using httpOnly cookie refresh token.
    
    Implements token rotation - old refresh token is invalidated
    and new token pair is issued. New refresh token is set as cookie.
    """
    client_ip = get_client_ip(request)
    refresh_token_str = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    
    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        auth_service = AuthService(session)
        token_pair = await auth_service.refresh_access_token(
            refresh_token_str,
            ip_address=client_ip
        )
        
        # Set new refresh token as httpOnly cookie
        _set_refresh_token_cookie(response, token_pair.refresh_token)
        
        # Return only access token in body
        return AuthResponse(
            user=token_pair.user,
            access_token=token_pair.access_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
        )
    except UnauthorizedException as e:
        # Clear cookie on refresh failure
        _clear_refresh_token_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Logout user and revoke tokens.
    
    Access token is blacklisted until expiration.
    Refresh token is revoked and cookie is cleared.
    """
    client_ip = get_client_ip(request)
    
    # Get access token from header
    auth_header = request.headers.get("Authorization", "")
    access_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None
    
    # Get refresh token from cookie
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    
    if access_token:
        auth_service = AuthService(session)
        await auth_service.logout(access_token, refresh_token, ip_address=client_ip)
    
    # Clear refresh token cookie
    _clear_refresh_token_cookie(response)
    
    return None


def _set_refresh_token_cookie(response: Response, token: str) -> None:
    """Set refresh token as secure httpOnly cookie."""
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=token,
        httponly=True,  # Not accessible via JavaScript (prevents XSS)
        secure=settings.is_production,  # HTTPS only in production
        samesite="strict",  # CSRF protection
        max_age=COOKIE_MAX_AGE,
        path=COOKIE_PATH,  # Only sent to auth endpoints
    )


def _clear_refresh_token_cookie(response: Response) -> None:
    """Clear refresh token cookie."""
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path=COOKIE_PATH,
    )


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new tenant (organization)."""
    tenant_repo = SQLAlchemyTenantRepository(session)
    return await tenant_repo.create(data.name)

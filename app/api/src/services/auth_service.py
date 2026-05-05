from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging_config import get_logger
from src.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    get_token_jti,
    get_token_expiration,
    decode_token,
)
from src.domain.enums import UserRole, AuditAction
from src.domain.exceptions import AlreadyExistsException, UnauthorizedException
from src.domain.schemas import UserCreate, UserResponse, TokenPair
from src.infrastructure.cache.token_cache import token_cache
from src.infrastructure.database.models import User
from src.infrastructure.database.repositories import (
    SQLAlchemyUserRepository,
    SQLAlchemyAuditLogRepository,
)

logger = get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._user_repo = SQLAlchemyUserRepository(session)

    async def register(
        self, data: UserCreate, tenant_id: UUID | None = None
    ) -> TokenPair:
        """Register a new user with token pair."""
        # Check if user exists
        existing = await self._user_repo.get_by_email(data.email)
        if existing:
            raise AlreadyExistsException("User", "email", data.email)

        # Hash password
        password_hash = get_password_hash(data.password)

        # Use provided tenant or create default
        effective_tenant_id = tenant_id or data.tenant_id
        if not effective_tenant_id:
            from src.infrastructure.database.repositories import (
                SQLAlchemyTenantRepository,
            )

            tenant_repo = SQLAlchemyTenantRepository(self._session)
            tenant = await tenant_repo.create("Default Tenant")
            effective_tenant_id = tenant.id

        # Create user
        user = await self._user_repo.create(
            email=data.email,
            password_hash=password_hash,
            role=data.role.value,
            tenant_id=effective_tenant_id,
        )

        # Generate token pair
        access_token, access_jti = create_access_token(
            data={
                "sub": str(user.id),
                "tenant_id": str(user.tenant_id),
                "role": user.role.value,
            }
        )
        refresh_token, refresh_jti = create_refresh_token(user.id, user.tenant_id)

        # Store refresh token
        await token_cache.store_refresh_token(
            user.id, refresh_jti, expires_in=60 * 60 * 24 * 7  # 7 days
        )

        # Log security event
        audit_repo = SQLAlchemyAuditLogRepository(self._session)
        await audit_repo.create({
            "tenant_id": user.tenant_id,
            "user_id": user.id,
            "action": AuditAction.CREATE,
            "entity_type": "User",
            "entity_id": user.id,
            "details": {"email": user.email, "event": "user_registered"},
        })

        logger.info(
            "User registered",
            user_id=str(user.id),
            email=user.email,
            tenant_id=str(user.tenant_id)
        )

        return TokenPair(
            user=UserResponse.model_validate(user),
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=15 * 60,  # 15 minutes
        )

    async def login(self, email: str, password: str, ip_address: str | None = None) -> TokenPair:
        """
        Authenticate user and return token pair.
        
        Args:
            email: User email
            password: User password
            ip_address: Optional client IP for audit logging
        """
        logger.info("Login attempt", email=email, ip_address=ip_address)

        # Get user
        user_resp = await self._user_repo.get_by_email(email)
        if not user_resp:
            logger.warning(
                "Login failed - user not found",
                email=email,
                ip_address=ip_address
            )
            raise UnauthorizedException("Invalid credentials")

        # Get full user for password verification
        from sqlalchemy import select
        from sqlalchemy.exc import NoResultFound
        try:
            result = await self._session.execute(
                select(User).where(User.id == user_resp.id)
            )
            user = result.scalar_one()
        except NoResultFound:
            logger.error(
                "User not found in database during login",
                user_id=str(user_resp.id),
                email=email
            )
            raise UnauthorizedException("Invalid credentials")
        except Exception as e:
            logger.error(
                "Database error during login",
                error=str(e),
                error_type=type(e).__name__,
                email=email
            )
            raise UnauthorizedException("Invalid credentials")

        # Validate user data
        if not user.password_hash:
            logger.error("User has no password hash", user_id=str(user.id))
            raise UnauthorizedException("Invalid credentials")

        if not user.role:
            logger.error("User has no role assigned", user_id=str(user.id))
            raise UnauthorizedException("Invalid credentials")

        # Verify password
        try:
            password_valid = verify_password(password, user.password_hash)
        except Exception as e:
            logger.error(
                "Password verification error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise UnauthorizedException("Invalid credentials")

        if not password_valid:
            logger.warning(
                "Login failed - invalid password",
                user_id=str(user.id),
                email=email,
                ip_address=ip_address
            )
            
            # Log failed login attempt
            audit_repo = SQLAlchemyAuditLogRepository(self._session)
            await audit_repo.create({
                "tenant_id": user.tenant_id,
                "user_id": user.id,
                "action": AuditAction.LOGIN_FAILED,
                "entity_type": "User",
                "entity_id": user.id,
                "details": {
                    "email": email,
                    "ip_address": ip_address,
                    "reason": "invalid_password"
                },
            })
            raise UnauthorizedException("Invalid credentials")

        # Generate token pair
        access_token, access_jti = create_access_token(
            data={
                "sub": str(user.id),
                "tenant_id": str(user.tenant_id),
                "role": user.role.value if user.role else "analyst",
            }
        )
        refresh_token, refresh_jti = create_refresh_token(user.id, user.tenant_id)

        # Store refresh token
        await token_cache.store_refresh_token(
            user.id, refresh_jti, expires_in=60 * 60 * 24 * 7  # 7 days
        )

        # Log successful login
        audit_repo = SQLAlchemyAuditLogRepository(self._session)
        await audit_repo.create({
            "tenant_id": user.tenant_id,
            "user_id": user.id,
            "action": AuditAction.LOGIN,
            "entity_type": "User",
            "entity_id": user.id,
            "details": {
                "email": email,
                "ip_address": ip_address,
                "access_jti": access_jti,
                "refresh_jti": refresh_jti,
            },
        })

        logger.info(
            "User logged in successfully",
            user_id=str(user.id),
            email=email,
            tenant_id=str(user.tenant_id),
            ip_address=ip_address
        )

        return TokenPair(
            user=UserResponse.model_validate(user),
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=15 * 60,  # 15 minutes
        )

    async def refresh_access_token(
        self,
        refresh_token: str,
        ip_address: str | None = None
    ) -> TokenPair:
        """
        Refresh access token using refresh token.
        
        Implements token rotation: old refresh token is invalidated,
        new token pair is issued.
        """
        try:
            # Decode refresh token
            payload = decode_token(refresh_token, token_type="refresh")
            user_id = UUID(payload.get("sub"))
            tenant_id = UUID(payload.get("tenant_id"))
            token_jti = payload.get("jti")

            # Validate refresh token against cache
            if not await token_cache.validate_refresh_token(user_id, token_jti):
                logger.warning(
                    "Invalid or revoked refresh token",
                    user_id=str(user_id),
                    token_jti=token_jti,
                    ip_address=ip_address
                )
                raise UnauthorizedException("Invalid refresh token")

            # Get user
            user = await self._user_repo.get_by_id(user_id)
            if not user or not user.is_active:
                logger.warning(
                    "Token refresh failed - user not found or inactive",
                    user_id=str(user_id)
                )
                raise UnauthorizedException("Invalid refresh token")

            # Revoke old refresh token (token rotation)
            await token_cache.revoke_refresh_token(user_id, token_jti)

            # Generate new token pair
            access_token, access_jti = create_access_token(
                data={
                    "sub": str(user.id),
                    "tenant_id": str(user.tenant_id),
                    "role": user.role.value,
                }
            )
            new_refresh_token, new_refresh_jti = create_refresh_token(user.id, user.tenant_id)

            # Store new refresh token
            await token_cache.store_refresh_token(
                user.id, new_refresh_jti, expires_in=60 * 60 * 24 * 7
            )

            # Log token refresh
            audit_repo = SQLAlchemyAuditLogRepository(self._session)
            await audit_repo.create({
                "tenant_id": user.tenant_id,
                "user_id": user.id,
                "action": AuditAction.TOKEN_REFRESH,
                "entity_type": "User",
                "entity_id": user.id,
                "details": {
                    "ip_address": ip_address,
                    "old_refresh_jti": token_jti,
                    "new_refresh_jti": new_refresh_jti,
                    "new_access_jti": access_jti,
                },
            })

            logger.info(
                "Token refreshed",
                user_id=str(user.id),
                ip_address=ip_address
            )

            return TokenPair(
                user=user,
                access_token=access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=15 * 60,
            )

        except Exception as e:
            logger.warning(
                "Token refresh failed",
                error=str(e),
                ip_address=ip_address
            )
            raise UnauthorizedException("Invalid refresh token")

    async def logout(
        self,
        access_token: str,
        refresh_token: str | None = None,
        ip_address: str | None = None
    ) -> None:
        """
        Logout user by revoking tokens.
        
        Blacklists access token and revokes refresh token.
        """
        try:
            # Decode tokens to get JTIs
            access_payload = decode_token(access_token, token_type="access")
            user_id = UUID(access_payload.get("sub"))
            tenant_id = UUID(access_payload.get("tenant_id"))
            access_jti = access_payload.get("jti")

            # Blacklist access token (store until expiration)
            exp = get_token_expiration(access_token)
            ttl = (exp - __import__('datetime').datetime.now(__import__('datetime').timezone.utc)).total_seconds()
            if ttl > 0:
                await token_cache.blacklist_access_token(access_jti, int(ttl))

            # Revoke refresh token if provided
            if refresh_token:
                refresh_payload = decode_token(refresh_token, token_type="refresh")
                refresh_jti = refresh_payload.get("jti")
                await token_cache.revoke_refresh_token(user_id, refresh_jti)

            # Log logout
            audit_repo = SQLAlchemyAuditLogRepository(self._session)
            await audit_repo.create({
                "tenant_id": tenant_id,
                "user_id": user_id,
                "action": AuditAction.LOGOUT,
                "entity_type": "User",
                "entity_id": user_id,
                "details": {
                    "ip_address": ip_address,
                    "access_jti": access_jti,
                },
            })

            logger.info(
                "User logged out",
                user_id=str(user_id),
                ip_address=ip_address
            )

        except Exception as e:
            logger.warning("Logout error", error=str(e), ip_address=ip_address)

    async def get_current_user(self, user_id: UUID) -> UserResponse:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedException("User not found")
        return user

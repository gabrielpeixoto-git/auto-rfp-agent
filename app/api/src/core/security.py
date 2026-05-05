from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings
from src.domain.exceptions import UnauthorizedException

# Use argon2 instead of bcrypt to avoid 72-byte limit issues
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Token expiration settings
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived: 15 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7  # Long-lived: 7 days


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None
) -> tuple[str, str]:
    """
    Create a JWT access token with jti (JWT ID) for revocation support.
    
    Returns:
        tuple: (token_string, jti) where jti is the token ID for blacklisting
    """
    to_encode = data.copy()
    
    # Generate unique token ID for blacklisting
    jti = str(uuid4())
    to_encode["jti"] = jti
    
    # Set token type
    to_encode["type"] = "access"
    
    # Calculate expiration
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt, jti


def create_refresh_token(user_id: UUID, tenant_id: UUID) -> tuple[str, str]:
    """
    Create a JWT refresh token.
    
    Returns:
        tuple: (token_string, jti)
    """
    jti = str(uuid4())
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    data = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "jti": jti,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    encoded_jwt = jwt.encode(
        data, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt, jti


def decode_token(token: str, token_type: str | None = None) -> dict:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token string
        token_type: Optional token type to validate ("access" or "refresh")
    
    Raises:
        UnauthorizedException: If token is invalid or type mismatch
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        
        # Validate token type if specified
        if token_type:
            payload_type = payload.get("type")
            if payload_type != token_type:
                raise UnauthorizedException(
                    f"Invalid token type. Expected {token_type}, got {payload_type}"
                )
        
        return payload
    except JWTError as e:
        raise UnauthorizedException(f"Invalid token: {str(e)}")


def get_user_id_from_token(token: str) -> UUID:
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedException("Token missing user id")
    return UUID(user_id)


def get_tenant_id_from_token(token: str) -> UUID:
    payload = decode_token(token)
    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        raise UnauthorizedException("Token missing tenant id")
    return UUID(tenant_id)


def get_token_jti(token: str) -> str:
    """Extract the jti (JWT ID) from a token."""
    payload = decode_token(token)
    jti = payload.get("jti")
    if jti is None:
        raise UnauthorizedException("Token missing jti")
    return jti


def get_token_expiration(token: str) -> datetime:
    """Get token expiration timestamp."""
    payload = decode_token(token)
    exp = payload.get("exp")
    if exp is None:
        raise UnauthorizedException("Token missing expiration")
    return datetime.fromtimestamp(exp, tz=timezone.utc)

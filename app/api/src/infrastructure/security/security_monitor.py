"""
Real-time security monitoring and alerting system.

Detects and alerts on:
- Multiple failed login attempts (brute force)
- Rate limit abuse
- Cross-tenant access attempts
- Session anomalies (IP changes, device fingerprint changes)
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable
from uuid import UUID

from src.core.logging_config import get_logger
from src.core.config import settings
from src.infrastructure.cache.redis_manager import redis_manager, RedisUnavailableException

logger = get_logger(__name__)


class SecurityAlertLevel(Enum):
    """Security alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """Types of security events."""
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    RATE_LIMIT_ABUSE = "rate_limit_abuse"
    CROSS_TENANT_ACCESS = "cross_tenant_access"
    SUSPICIOUS_SESSION = "suspicious_session"
    TOKEN_REUSE = "token_reuse"
    ANOMALOUS_LOCATION = "anomalous_location"
    ANOMALOUS_DEVICE = "anomalous_device"


@dataclass
class SecurityAlert:
    """Security alert data structure."""
    event_type: SecurityEventType
    level: SecurityAlertLevel
    message: str
    user_id: UUID | None = None
    tenant_id: UUID | None = None
    ip_address: str | None = None
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "level": self.level.value,
            "message": self.message,
            "user_id": str(self.user_id) if self.user_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "ip_address": self.ip_address,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class SecurityMonitor:
    """
    Real-time security monitoring system.
    
    Tracks security events and triggers alerts when thresholds are exceeded.
    Uses Redis for distributed tracking across multiple API instances.
    """
    
    # Thresholds for alerts
    FAILED_LOGIN_THRESHOLD = 5  # Failed logins in window
    FAILED_LOGIN_WINDOW = 300  # 5 minutes
    RATE_LIMIT_THRESHOLD = 10  # Rate limit hits in window
    RATE_LIMIT_WINDOW = 300  # 5 minutes
    SESSION_ANOMALY_THRESHOLD = 3  # Anomalies per hour
    
    _instance = None
    _alert_handlers: list[Callable[[SecurityAlert], None]] = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register_alert_handler(self, handler: Callable[[SecurityAlert], None]) -> None:
        """Register a handler for security alerts."""
        self._alert_handlers.append(handler)
        logger.info("Security alert handler registered", handler=handler.__name__)
    
    async def _store_event(self, key: str, event_data: dict, ttl: int = 3600) -> None:
        """Store security event in Redis."""
        async def _store(redis_conn):
            timestamp = datetime.now(timezone.utc).isoformat()
            await redis_conn.zadd(key, {f"{timestamp}:{event_data}": datetime.now(timezone.utc).timestamp()})
            await redis_conn.expire(key, ttl)
        
        try:
            await redis_manager.execute("store_security_event", _store)
        except RedisUnavailableException:
            # Log locally if Redis is unavailable
            logger.warning("Redis unavailable - security event logged locally", event=event_data)
    
    async def _count_events(self, key: str, window_seconds: int) -> int:
        """Count events in time window."""
        async def _count(redis_conn):
            cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).timestamp()
            await redis_conn.zremrangebyscore(key, 0, cutoff)
            return await redis_conn.zcard(key)
        
        try:
            return await redis_manager.execute("count_security_events", _count)
        except RedisUnavailableException:
            return 0  # Fail safe - assume no events if can't verify
    
    async def _trigger_alert(self, alert: SecurityAlert) -> None:
        """Trigger all registered alert handlers."""
        logger.warning(
            "SECURITY ALERT",
            **alert.to_dict()
        )
        
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error("Alert handler failed", handler=handler.__name__, error=str(e))
    
    # Event tracking methods
    
    async def track_failed_login(
        self,
        email: str,
        ip_address: str,
        user_id: UUID | None = None
    ) -> None:
        """Track failed login attempt and alert if threshold exceeded."""
        key = f"security:failed_logins:{ip_address}"
        
        await self._store_event(key, {
            "email": email,
            "ip": ip_address,
            "user_id": str(user_id) if user_id else None
        })
        
        count = await self._count_events(key, self.FAILED_LOGIN_WINDOW)
        
        if count >= self.FAILED_LOGIN_THRESHOLD:
            await self._trigger_alert(SecurityAlert(
                event_type=SecurityEventType.BRUTE_FORCE_ATTEMPT,
                level=SecurityAlertLevel.HIGH if count >= 10 else SecurityAlertLevel.MEDIUM,
                message=f"Brute force attack detected: {count} failed logins from {ip_address}",
                user_id=user_id,
                ip_address=ip_address,
                details={"failed_count": count, "email": email, "window_seconds": self.FAILED_LOGIN_WINDOW}
            ))
    
    async def track_rate_limit_hit(
        self,
        ip_address: str,
        endpoint: str,
        user_id: UUID | None = None
    ) -> None:
        """Track rate limit violation and alert if threshold exceeded."""
        key = f"security:rate_limits:{ip_address}"
        
        await self._store_event(key, {
            "endpoint": endpoint,
            "ip": ip_address,
            "user_id": str(user_id) if user_id else None
        })
        
        count = await self._count_events(key, self.RATE_LIMIT_WINDOW)
        
        if count >= self.RATE_LIMIT_THRESHOLD:
            await self._trigger_alert(SecurityAlert(
                event_type=SecurityEventType.RATE_LIMIT_ABUSE,
                level=SecurityAlertLevel.MEDIUM,
                message=f"Rate limit abuse detected from {ip_address}",
                user_id=user_id,
                ip_address=ip_address,
                details={"violation_count": count, "endpoint": endpoint}
            ))
    
    async def track_cross_tenant_access(
        self,
        user_id: UUID,
        user_tenant_id: UUID,
        target_tenant_id: UUID,
        resource_type: str,
        ip_address: str
    ) -> None:
        """Track cross-tenant access attempt."""
        await self._trigger_alert(SecurityAlert(
            event_type=SecurityEventType.CROSS_TENANT_ACCESS,
            level=SecurityAlertLevel.CRITICAL,
            message=f"Cross-tenant access attempt: User {user_id} from tenant {user_tenant_id} tried to access {resource_type} in tenant {target_tenant_id}",
            user_id=user_id,
            tenant_id=user_tenant_id,
            ip_address=ip_address,
            details={
                "target_tenant_id": str(target_tenant_id),
                "resource_type": resource_type
            }
        ))
    
    async def track_session_anomaly(
        self,
        user_id: UUID,
        tenant_id: UUID,
        anomaly_type: str,
        details: dict,
        ip_address: str | None = None
    ) -> None:
        """Track session anomaly (IP change, device change, etc.)."""
        key = f"security:anomalies:{user_id}"
        
        await self._store_event(key, {
            "anomaly_type": anomaly_type,
            "details": details,
            "ip": ip_address
        })
        
        count = await self._count_events(key, 3600)  # Per hour
        
        # Determine severity based on anomaly type and count
        if anomaly_type == "ip_change":
            level = SecurityAlertLevel.MEDIUM
        elif anomaly_type == "device_change":
            level = SecurityAlertLevel.MEDIUM
        else:
            level = SecurityAlertLevel.LOW
        
        if count >= self.SESSION_ANOMALY_THRESHOLD:
            level = SecurityAlertLevel.HIGH
        
        await self._trigger_alert(SecurityAlert(
            event_type=SecurityEventType.SUSPICIOUS_SESSION,
            level=level,
            message=f"Session anomaly detected: {anomaly_type}",
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            details={"anomaly_type": anomaly_type, **details, "anomaly_count": count}
        ))
    
    async def track_token_reuse(
        self,
        token_jti: str,
        user_id: UUID,
        ip_address: str
    ) -> None:
        """Track reuse of revoked token."""
        await self._trigger_alert(SecurityAlert(
            event_type=SecurityEventType.TOKEN_REUSE,
            level=SecurityAlertLevel.HIGH,
            message=f"Revoked token reuse attempt",
            user_id=user_id,
            ip_address=ip_address,
            details={"token_jti": token_jti[:8] + "..."}
        ))


# Global security monitor instance
security_monitor = SecurityMonitor()


# Built-in alert handlers

def log_alert_handler(alert: SecurityAlert) -> None:
    """Default handler - logs to structured logging."""
    log_method = {
        SecurityAlertLevel.LOW: logger.info,
        SecurityAlertLevel.MEDIUM: logger.warning,
        SecurityAlertLevel.HIGH: logger.error,
        SecurityAlertLevel.CRITICAL: logger.critical,
    }.get(alert.level, logger.warning)
    
    log_method(
        "SECURITY_ALERT",
        **alert.to_dict()
    )


# Register default handler
security_monitor.register_alert_handler(log_alert_handler)

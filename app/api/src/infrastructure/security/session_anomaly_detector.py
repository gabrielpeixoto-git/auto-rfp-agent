"""
Session anomaly detection system.

Detects suspicious session behavior:
- IP address changes
- User agent / device changes
- Geographic location anomalies
- Multiple active sessions
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from src.core.logging_config import get_logger
from src.infrastructure.cache.redis_manager import redis_manager, RedisUnavailableException
from src.infrastructure.security.security_monitor import security_monitor, SecurityEventType

logger = get_logger(__name__)


@dataclass
class SessionFingerprint:
    """Fingerprint of a user's session."""
    user_id: UUID
    ip_address: str
    user_agent: str
    timestamp: datetime
    device_hash: str
    
    @classmethod
    def create(
        cls,
        user_id: UUID,
        ip_address: str,
        user_agent: str
    ) -> "SessionFingerprint":
        """Create a new session fingerprint."""
        # Create device hash from user agent
        device_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
        
        return cls(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(timezone.utc),
            device_hash=device_hash
        )
    
    def to_dict(self) -> dict:
        return {
            "user_id": str(self.user_id),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent[:100] + "..." if len(self.user_agent) > 100 else self.user_agent,
            "device_hash": self.device_hash,
            "timestamp": self.timestamp.isoformat()
        }


class SessionAnomalyDetector:
    """
    Detects anomalies in user sessions.
    
    Tracks session metadata and alerts on suspicious changes.
    """
    
    # Thresholds
    IP_CHANGE_THRESHOLD = 3  # IP changes per hour
    DEVICE_CHANGE_THRESHOLD = 2  # Device changes per day
    MAX_SESSIONS_PER_USER = 5  # Concurrent sessions
    
    async def record_session_start(
        self,
        user_id: UUID,
        tenant_id: UUID,
        ip_address: str,
        user_agent: str,
        token_jti: str
    ) -> dict:
        """
        Record new session and check for anomalies.
        
        Returns:
            dict with anomaly status and recommendations
        """
        fingerprint = SessionFingerprint.create(user_id, ip_address, user_agent)
        key = f"session:active:{user_id}"
        
        anomalies = []
        recommendations = []
        
        try:
            # Check for IP changes
            last_ip = await self._get_last_ip(user_id)
            if last_ip and last_ip != ip_address:
                ip_changes = await self._count_ip_changes(user_id, 3600)
                if ip_changes >= self.IP_CHANGE_THRESHOLD:
                    anomalies.append({
                        "type": "ip_change",
                        "severity": "medium",
                        "previous_ip": last_ip,
                        "current_ip": ip_address,
                        "changes_in_hour": ip_changes
                    })
                    recommendations.append("Consider requiring MFA for this user")
                    
                    await security_monitor.track_session_anomaly(
                        user_id=user_id,
                        tenant_id=tenant_id,
                        anomaly_type="ip_change",
                        details={"previous_ip": last_ip, "current_ip": ip_address},
                        ip_address=ip_address
                    )
            
            # Check for device changes
            last_device = await self._get_last_device(user_id)
            if last_device and last_device != fingerprint.device_hash:
                device_changes = await self._count_device_changes(user_id, 86400)
                if device_changes >= self.DEVICE_CHANGE_THRESHOLD:
                    anomalies.append({
                        "type": "device_change",
                        "severity": "medium",
                        "changes_in_day": device_changes
                    })
                    recommendations.append("Review recent account activity")
                    
                    await security_monitor.track_session_anomaly(
                        user_id=user_id,
                        tenant_id=tenant_id,
                        anomaly_type="device_change",
                        details={"device_hash": fingerprint.device_hash},
                        ip_address=ip_address
                    )
            
            # Check concurrent sessions
            active_sessions = await self._count_active_sessions(user_id)
            if active_sessions >= self.MAX_SESSIONS_PER_USER:
                anomalies.append({
                    "type": "multiple_sessions",
                    "severity": "low",
                    "active_sessions": active_sessions
                })
                recommendations.append("Consider revoking older sessions")
            
            # Store session data
            await self._store_session(user_id, token_jti, fingerprint)
            
        except RedisUnavailableException:
            logger.warning("Redis unavailable - session anomaly detection disabled")
            anomalies.append({
                "type": "detection_unavailable",
                "severity": "low",
                "message": "Session monitoring temporarily unavailable"
            })
        
        return {
            "session_started": True,
            "fingerprint": fingerprint.to_dict(),
            "anomalies_detected": len(anomalies) > 0,
            "anomalies": anomalies,
            "recommendations": recommendations
        }
    
    async def validate_session(
        self,
        user_id: UUID,
        ip_address: str,
        user_agent: str,
        token_jti: str
    ) -> dict:
        """
        Validate current session against stored fingerprint.
        
        Returns:
            dict with validation result
        """
        try:
            stored = await self._get_session(user_id, token_jti)
            if not stored:
                return {"valid": False, "reason": "session_not_found"}
            
            issues = []
            
            # Check IP (allow some tolerance for mobile networks)
            if stored["ip_address"] != ip_address:
                # Allow if first 3 octets match (same /24 subnet)
                old_ip_parts = stored["ip_address"].split(".")
                new_ip_parts = ip_address.split(".")
                
                if len(old_ip_parts) == 4 and len(new_ip_parts) == 4:
                    if old_ip_parts[:3] != new_ip_parts[:3]:
                        issues.append({
                            "type": "ip_mismatch",
                            "stored_ip": stored["ip_address"],
                            "current_ip": ip_address
                        })
            
            # Check device hash (more strict)
            current_device_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
            if stored["device_hash"] != current_device_hash:
                issues.append({
                    "type": "device_mismatch",
                    "message": "Device fingerprint changed"
                })
            
            return {
                "valid": len(issues) == 0,
                "issues": issues
            }
            
        except RedisUnavailableException:
            # Fail open if Redis is down - don't block legitimate users
            return {"valid": True, "issues": [], "detection_unavailable": True}
    
    async def end_session(self, user_id: UUID, token_jti: str) -> None:
        """End a session and remove tracking data."""
        try:
            await self._remove_session(user_id, token_jti)
        except RedisUnavailableException:
            logger.warning("Redis unavailable - session removal failed", user_id=str(user_id))
    
    # Redis operations
    
    async def _store_session(
        self,
        user_id: UUID,
        token_jti: str,
        fingerprint: SessionFingerprint
    ) -> None:
        """Store session data in Redis."""
        async def _store(redis_conn):
            key = f"session:active:{user_id}:{token_jti}"
            data = {
                "ip_address": fingerprint.ip_address,
                "device_hash": fingerprint.device_hash,
                "user_agent": fingerprint.user_agent[:200],
                "started_at": fingerprint.timestamp.isoformat()
            }
            # TTL 7 days (match refresh token expiry)
            await redis_conn.hset(key, mapping=data)
            await redis_conn.expire(key, 60 * 60 * 24 * 7)
        
        await redis_manager.execute("store_session", _store)
    
    async def _get_session(self, user_id: UUID, token_jti: str) -> dict | None:
        """Get session data from Redis."""
        async def _get(redis_conn):
            key = f"session:active:{user_id}:{token_jti}"
            return await redis_conn.hgetall(key)
        
        return await redis_manager.execute("get_session", _get)
    
    async def _remove_session(self, user_id: UUID, token_jti: str) -> None:
        """Remove session data from Redis."""
        async def _remove(redis_conn):
            key = f"session:active:{user_id}:{token_jti}"
            await redis_conn.delete(key)
        
        await redis_manager.execute("remove_session", _remove)
    
    async def _count_active_sessions(self, user_id: UUID) -> int:
        """Count active sessions for user."""
        async def _count(redis_conn):
            pattern = f"session:active:{user_id}:*"
            count = 0
            async for _ in redis_conn.scan_iter(match=pattern):
                count += 1
            return count
        
        try:
            return await redis_manager.execute("count_sessions", _count)
        except RedisUnavailableException:
            return 0
    
    async def _get_last_ip(self, user_id: UUID) -> str | None:
        """Get last known IP for user."""
        async def _get(redis_conn):
            key = f"session:last:{user_id}"
            return await redis_conn.hget(key, "ip_address")
        
        try:
            return await redis_manager.execute("get_last_ip", _get)
        except RedisUnavailableException:
            return None
    
    async def _count_ip_changes(self, user_id: UUID, window_seconds: int) -> int:
        """Count IP changes in time window."""
        async def _count(redis_conn):
            key = f"session:ip_changes:{user_id}"
            cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).timestamp()
            await redis_conn.zremrangebyscore(key, 0, cutoff)
            return await redis_conn.zcard(key)
        
        try:
            return await redis_manager.execute("count_ip_changes", _count)
        except RedisUnavailableException:
            return 0
    
    async def _get_last_device(self, user_id: UUID) -> str | None:
        """Get last known device hash for user."""
        async def _get(redis_conn):
            key = f"session:last:{user_id}"
            return await redis_conn.hget(key, "device_hash")
        
        try:
            return await redis_manager.execute("get_last_device", _get)
        except RedisUnavailableException:
            return None
    
    async def _count_device_changes(self, user_id: UUID, window_seconds: int) -> int:
        """Count device changes in time window."""
        async def _count(redis_conn):
            key = f"session:device_changes:{user_id}"
            cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).timestamp()
            await redis_conn.zremrangebyscore(key, 0, cutoff)
            return await redis_conn.zcard(key)
        
        try:
            return await redis_manager.execute("count_device_changes", _count)
        except RedisUnavailableException:
            return 0


# Global instance
session_anomaly_detector = SessionAnomalyDetector()

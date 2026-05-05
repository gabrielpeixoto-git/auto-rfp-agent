"""
XSS Protection middleware and input sanitization.

Provides:
- Strong Content Security Policy (CSP) without unsafe-inline
- Request body sanitization
- Output encoding helpers
"""

import html
import json
import re
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.config import settings
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class XSSProtectionMiddleware(BaseHTTPMiddleware):
    """
    XSS Protection middleware with strong CSP.
    
    Removes unsafe-inline and unsafe-eval from CSP.
    Requires nonce-based inline scripts if needed.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Add XSS protection headers."""
        response = await call_next(request)
        
        # Strict CSP without unsafe-inline
        # For API responses, we don't need script-src
        csp = (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "form-action 'self';"
        )
        
        response.headers["Content-Security-Policy"] = csp
        
        # Additional XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        return response


class InputSanitizer:
    """
    Input sanitization utilities.
    
    Prevents XSS by sanitizing user inputs before processing.
    """
    
    # Patterns for common XSS vectors
    XSS_PATTERNS = [
        (re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL), '[REMOVED-SCRIPT]'),
        (re.compile(r'javascript:', re.IGNORECASE), '[REMOVED-JS]'),
        (re.compile(r'on\w+\s*=', re.IGNORECASE), '[REMOVED-EVENT]'),
        (re.compile(r'<iframe[^>]*>.*?</iframe>', re.IGNORECASE | re.DOTALL), '[REMOVED-IFRAME]'),
        (re.compile(r'<object[^>]*>.*?</object>', re.IGNORECASE | re.DOTALL), '[REMOVED-OBJECT]'),
        (re.compile(r'<embed[^>]*>', re.IGNORECASE), '[REMOVED-EMBED]'),
    ]
    
    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """
        Sanitize a string input by removing XSS vectors.
        
        Args:
            value: Input string to sanitize
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return value
        
        # Remove common XSS patterns
        for pattern, replacement in cls.XSS_PATTERNS:
            value = pattern.sub(replacement, value)
        
        # HTML escape the result
        return html.escape(value)
    
    @classmethod
    def sanitize_dict(cls, data: dict) -> dict:
        """Recursively sanitize all string values in a dict."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = cls.sanitize_string(value)
            elif isinstance(value, dict):
                result[key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                result[key] = cls.sanitize_list(value)
            else:
                result[key] = value
        return result
    
    @classmethod
    def sanitize_list(cls, data: list) -> list:
        """Recursively sanitize all string values in a list."""
        result = []
        for item in data:
            if isinstance(item, str):
                result.append(cls.sanitize_string(item))
            elif isinstance(item, dict):
                result.append(cls.sanitize_dict(item))
            elif isinstance(item, list):
                result.append(cls.sanitize_list(item))
            else:
                result.append(item)
        return result
    
    @classmethod
    def sanitize_json_content(cls, content: str) -> str:
        """
        Sanitize JSON string content.
        
        Parses JSON, sanitizes string values, re-serializes.
        
        Args:
            content: JSON string
            
        Returns:
            Sanitized JSON string
        """
        try:
            data = json.loads(content)
            sanitized = cls._sanitize_value(data)
            return json.dumps(sanitized)
        except json.JSONDecodeError:
            # Not valid JSON, sanitize as string
            return cls.sanitize_string(content)
    
    @classmethod
    def _sanitize_value(cls, value: Any) -> Any:
        """Recursively sanitize a value."""
        if isinstance(value, str):
            return cls.sanitize_string(value)
        elif isinstance(value, dict):
            return {k: cls._sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [cls._sanitize_value(v) for v in value]
        return value


class OutputEncoder:
    """
    Output encoding utilities for preventing XSS.
    
    Use these when rendering user-generated content.
    """
    
    @staticmethod
    def html_encode(text: str) -> str:
        """Encode text for HTML output."""
        return html.escape(text)
    
    @staticmethod
    def js_encode(text: str) -> str:
        """Encode text for JavaScript output."""
        # JSON encoding is safe for JS strings
        return json.dumps(text)
    
    @staticmethod
    def url_encode(text: str) -> str:
        """Encode text for URL parameters."""
        from urllib.parse import quote
        return quote(text, safe='')
    
    @staticmethod
    def css_encode(text: str) -> str:
        """Encode text for CSS content."""
        # CSS string encoding
        result = []
        for char in text:
            if char == '\\':
                result.append('\\\\')
            elif char == '"':
                result.append('\\"')
            elif char == "'":
                result.append("\\'")
            elif char < ' ' or ord(char) > 127:
                result.append(f'\\{ord(char):06x} ')
            else:
                result.append(char)
        return ''.join(result)


def sanitize_input(value: Any) -> Any:
    """
    Convenience function to sanitize any input value.
    
    Args:
        value: Value to sanitize
        
    Returns:
        Sanitized value
    """
    if isinstance(value, str):
        return InputSanitizer.sanitize_string(value)
    elif isinstance(value, dict):
        return InputSanitizer.sanitize_dict(value)
    elif isinstance(value, list):
        return InputSanitizer.sanitize_list(value)
    return value

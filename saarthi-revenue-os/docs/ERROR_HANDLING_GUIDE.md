# Comprehensive Error Handling Guide for FastAPI Web Applications

This guide provides a complete implementation strategy for error handling in FastAPI applications, covering all aspects from custom error pages to retry mechanisms.

---

## Table of Contents

1. [Custom Error Pages for HTTP Status Codes](#1-custom-error-pages-for-http-status-codes)
2. [Error Logging Configuration](#2-error-logging-configuration)
3. [User-Friendly Error Messages](#3-user-friendly-error-messages)
4. [Error Notification Systems](#4-error-notification-systems)
5. [Error Handling Middleware and Exception Handlers](#5-error-handling-middleware-and-exception-handlers)
6. [Error Response Formats](#6-error-response-formats)
7. [Development vs Production Configurations](#7-development-vs-production-configurations)
8. [Error Retry Mechanisms](#8-error-retry-mechanisms)

---

## 1. Custom Error Pages for HTTP Status Codes

### 1.1 HTML Error Templates

Create custom error pages for different HTTP status codes.

```python
# app/errors/templates.py
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Dict

ERROR_TEMPLATES: Dict[int, str] = {
    400: "errors/400.html",
    401: "errors/401.html",
    403: "errors/403.html",
    404: "errors/404.html",
    429: "errors/429.html",
    500: "errors/500.html",
    502: "errors/502.html",
    503: "errors/503.html",
}

async def render_error_page(status_code: int, request: Request, detail: str = None) -> HTMLResponse:
    """Render custom HTML error page for the given status code."""
    template_path = Path("app/errors/templates") / ERROR_TEMPLATES.get(status_code, "500.html")
    
    # Default error messages for each status code
    default_messages = {
        400: "Bad Request - The server could not understand your request.",
        401: "Unauthorized - Please log in to access this resource.",
        403: "Forbidden - You don't have permission to access this resource.",
        404: "Page Not Found - The requested resource could not be found.",
        429: "Too Many Requests - Please slow down and try again later.",
        500: "Internal Server Error - Something went wrong on our end.",
        502: "Bad Gateway - The server received an invalid response.",
        503: "Service Unavailable - We're temporarily unavailable.",
    }
    
    error_message = detail or default_messages.get(status_code, "An error occurred.")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Error {status_code}</title>
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex; 
                align-items: center; 
                justify-content: center; 
                min-height: 100vh; 
                margin: 0; 
                background: #f5f5f5;
            }}
            .error-container {{
                text-align: center;
                padding: 2rem;
                max-width: 500px;
            }}
            .error-code {{
                font-size: 6rem;
                font-weight: bold;
                color: #dc2626;
                margin: 0;
            }}
            .error-title {{
                font-size: 1.5rem;
                color: #374151;
                margin: 1rem 0;
            }}
            .error-message {{
                color: #6b7280;
                margin-bottom: 2rem;
            }}
            .home-link {{
                display: inline-block;
                padding: 0.75rem 1.5rem;
                background: #2563eb;
                color: white;
                text-decoration: none;
                border-radius: 0.5rem;
                transition: background 0.2s;
            }}
            .home-link:hover {{
                background: #1d4ed8;
            }}
        </style>
    </head>
    <body>
        <div class="error-container">
            <h1 class="error-code">{status_code}</h1>
            <h2 class="error-title">{default_messages.get(status_code, 'An Error Occurred')}</h2>
            <p class="error-message">{error_message}</p>
            <a href="/" class="home-link">Go to Homepage</a>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content, status_code=status_code)
```

### 1.2 Registering Custom Error Handlers

```python
# app/errors/handlers.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from typing import Union
import traceback
import logging

from app.errors.templates import render_error_page
from app.errors.logging import log_error
from app.errors.notifications import send_error_notification
from app.core.settings import settings

logger = logging.getLogger(__name__)

# Custom exception classes
class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ResourceNotFoundError(AppException):
    """Raised when a requested resource is not found."""
    def __init__(self, resource: str, resource_id: str = None):
        message = f"{resource} not found"
        if resource_id:
            message += f" with ID: {resource_id}"
        super().__init__(message, status_code=404)

class ValidationError(AppException):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: str = None):
        details = {"field": field} if field else {}
        super().__init__(message, status_code=400, details=details)

class AuthenticationError(AppException):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)

class AuthorizationError(AppException):
    """Raised when user lacks permission."""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)

class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        details = {"retry_after": retry_after}
        super().__init__(message, status_code=429, details=details)

class ExternalServiceError(AppException):
    """Raised when external service call fails."""
    def __init__(self, service: str, message: str = None):
        msg = message or f"External service '{service}' is unavailable"
        super().__init__(msg, status_code=503, details={"service": service})

def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    
    # Handle custom AppException
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return await handle_app_exception(request, exc)
    
    # Handle HTTPException
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return await handle_http_exception(request, exc)
    
    # Handle validation errors
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return await handle_validation_error(request, exc)
    
    # Handle uncaught exceptions
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return await handle_general_exception(request, exc)

async def handle_app_exception(request: Request, exc: AppException) -> Union[JSONResponse, HTMLResponse]:
    """Handle custom application exceptions."""
    # Log the error
    log_error(
        error=exc,
        context={"path": request.url.path, "method": request.method},
        details=exc.details
    )
    
    # Send notification for critical errors
    if exc.status_code >= 500:
        await send_error_notification(exc, request)
    
    # Check if client accepts HTML
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return await render_error_page(exc.status_code, request, exc.message)
    
    # Return JSON response for API clients
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.message,
                "details": exc.details if settings.DEBUG else {}  # Hide details in production
            }
        }
    )

async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> Union[JSONResponse, HTMLResponse]:
    """Handle built-in HTTP exceptions."""
    accept = request.headers.get("accept", "")
    
    if "text/html" in accept:
        return await render_error_page(exc.status_code, request, str(exc.detail))
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail
            }
        }
    )

async def handle_validation_error(request: Request, exc: RequestValidationError) -> Union[JSONResponse, HTMLResponse]:
    """Handle request validation errors."""
    errors = exc.errors()
    
    # Format validation errors for better UX
    formatted_errors = []
    for error in errors:
        formatted_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"] if loc != "body"),
            "message": error["msg"],
            "type": error["type"]
        })
    
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return await render_error_page(400, request, "Invalid request data")
    
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": 400,
                "message": "Validation failed",
                "details": {"validation_errors": formatted_errors} if settings.DEBUG else {}
            }
        }
    )

async def handle_general_exception(request: Request, exc: Exception) -> Union[JSONResponse, HTMLResponse]:
    """Handle unexpected exceptions."""
    # Log full traceback
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Log and notify
    log_error(
        error=exc,
        context={"path": request.url.path, "method": request.method},
        details={"traceback": traceback.format_exc()} if settings.DEBUG else {}
    )
    
    # Send notification for unexpected errors
    await send_error_notification(exc, request)
    
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return await render_error_page(500, request)
    
    # Generic message for production
    message = "An unexpected error occurred" if not settings.DEBUG else str(exc)
    
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": message
            }
        }
    )
```

---

## 2. Error Logging Configuration

### 2.1 Structured Logging Setup

```python
# app/errors/logging.py
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
import traceback
from logging.handlers import RotatingFileHandler, SysLogHandler
import logging.config

from app.core.settings import settings

class StructuredLogger:
    """Enhanced logger with structured logging support."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up logging handlers based on environment."""
        if self.logger.handlers:
            return
        
        # Console handler for all environments
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for production
        if not settings.DEBUG:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_dir / "error.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=10
            )
            file_handler.setLevel(logging.WARNING)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log(self, level: str, message: str, **kwargs: Any) -> None:
        """Log with structured data."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            **kwargs
        }
        
        log_func = getattr(self.logger, level.lower())
        log_func(json.dumps(log_data))
    
    def error_with_context(self, message: str, context: Dict = None, **kwargs: Any) -> None:
        """Log error with additional context."""
        self.log("error", message, context=context or {}, **kwargs)
    
    def log_request_error(self, request, error: Exception, extra: Dict = None) -> None:
        """Log request-related error."""
        self.log(
            "error",
            f"Request error: {str(error)}",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            **(extra or {})
        )

# Global logger instance
structured_logger = StructuredLogger("saarthi")

def log_error(
    error: Exception,
    context: Dict = None,
    details: Dict = None,
    level: str = "error"
) -> None:
    """
    Log an error with full context and details.
    
    Args:
        error: The exception that was raised
        context: Request/context information
        details: Additional error details
        level: Logging level (error, warning, critical)
    """
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {},
    }
    
    if details:
        error_data["details"] = details
    
    if settings.DEBUG:
        error_data["traceback"] = traceback.format_exc()
    
    log_func = getattr(structured_logger.logger, level.lower())
    log_func(json.dumps(error_data))

def log_warning(message: str, **kwargs: Any) -> None:
    """Log a warning message."""
    structured_logger.log("warning", message, **kwargs)

def log_info(message: str, **kwargs: Any) -> None:
    """Log an info message."""
    structured_logger.log("info", message, **kwargs)

def log_debug(message: str, **kwargs: Any) -> None:
    """Log a debug message."""
    structured_logger.log("debug", message, **kwargs)
```

### 2.2 Logging Configuration in Settings

```python
# app/core/settings.py
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings."""
    
    # Environment
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost/db"
    
    # Security
    SECRET_KEY: str = "your-secret-key"
    
    # Error Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "logs/error.log"
    ENABLE_ERROR_NOTIFICATIONS: bool = True
    ERROR_NOTIFICATION_WEBHOOK: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # External Services
    EXTERNAL_SERVICE_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

---

## 3. User-Friendly Error Messages

### 3.1 Error Message Templates

```python
# app/errors/messages.py
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass

class ErrorCode(str, Enum):
    """Standardized error codes for the application."""
    # Authentication
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_ACCOUNT_LOCKED = "AUTH_ACCOUNT_LOCKED"
    
    # Authorization
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_FORBIDDEN = "RESOURCE_FORBIDDEN"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"
    
    # Resources
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # External Services
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    
    # General
    INTERNAL_ERROR = "INTERNAL_ERROR"
    BAD_REQUEST = "BAD_REQUEST"

@dataclass
class ErrorMessage:
    """Error message with user-friendly text and technical details."""
    user_message: str
    technical_message: str
    error_code: ErrorCode
    status_code: int
    should_notify: bool = False
    
    def to_dict(self, include_technical: bool = False) -> Dict:
        """Convert to dictionary for API response."""
        result = {
            "error": {
                "code": self.error_code.value,
                "message": self.user_message,
            }
        }
        
        if include_technical:
            result["error"]["technical_details"] = self.technical_message
        
        return result

# Error message templates
ERROR_MESSAGES: Dict[ErrorCode, ErrorMessage] = {
    ErrorCode.AUTH_INVALID_CREDENTIALS: ErrorMessage(
        user_message="Invalid email or password. Please try again.",
        technical_message="Authentication failed: invalid credentials",
        error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
        status_code=401
    ),
    ErrorCode.AUTH_TOKEN_EXPIRED: ErrorMessage(
        user_message="Your session has expired. Please log in again.",
        technical_message="JWT token has expired",
        error_code=ErrorCode.AUTH_TOKEN_EXPIRED,
        status_code=401
    ),
    ErrorCode.AUTH_TOKEN_INVALID: ErrorMessage(
        user_message="Your session is invalid. Please log in again.",
        technical_message="Invalid JWT token",
        error_code=ErrorCode.AUTH_TOKEN_INVALID,
        status_code=401
    ),
    ErrorCode.PERMISSION_DENIED: ErrorMessage(
        user_message="You don't have permission to perform this action.",
        technical_message="User lacks required permissions",
        error_code=ErrorCode.PERMISSION_DENIED,
        status_code=403
    ),
    ErrorCode.RESOURCE_NOT_FOUND: ErrorMessage(
        user_message="The requested resource could not be found.",
        technical_message="Resource not found in database",
        error_code=ErrorCode.RESOURCE_NOT_FOUND,
        status_code=404
    ),
    ErrorCode.VALIDATION_ERROR: ErrorMessage(
        user_message="The provided data is invalid. Please check your input.",
        technical_message="Input validation failed",
        error_code=ErrorCode.VALIDATION_ERROR,
        status_code=400
    ),
    ErrorCode.RATE_LIMIT_EXCEEDED: ErrorMessage(
        user_message="Too many requests. Please wait a moment and try again.",
        technical_message="Rate limit exceeded",
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        status_code=429
    ),
    ErrorCode.EXTERNAL_SERVICE_ERROR: ErrorMessage(
        user_message="We're having trouble connecting to an external service. Please try again later.",
        technical_message="External API call failed",
        error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        status_code=503,
        should_notify=True
    ),
    ErrorCode.INTERNAL_ERROR: ErrorMessage(
        user_message="Something went wrong on our end. Please try again later.",
        technical_message="Unhandled internal error",
        error_code=ErrorCode.INTERNAL_ERROR,
        status_code=500,
        should_notify=True
    ),
}

def get_error_message(error_code: ErrorCode, custom_message: Optional[str] = None) -> ErrorMessage:
    """Get error message by code, optionally with custom user message."""
    base_message = ERROR_MESSAGES.get(error_code)
    
    if base_message and custom_message:
        return ErrorMessage(
            user_message=custom_message,
            technical_message=base_message.technical_message,
            error_code=error_code,
            status_code=base_message.status_code,
            should_notify=base_message.should_notify
        )
    
    return base_message or ERROR_MESSAGES[ErrorCode.INTERNAL_ERROR]
```

### 3.2 Sanitizing Error Responses

```python
# app/errors/sanitizer.py
import re
import os
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

# Patterns that might expose sensitive information
SENSITIVE_PATTERNS = [
    (r'password["\']?\s*[:=]\s*["\']?[^"\']+', 'password":"[REDACTED]'),
    (r'secret["\']?\s*[:=]\s*["\']?[^"\']+', 'secret":"[REDACTED]'),
    (r'token["\']?\s*[:=]\s*["\']?[^"\']+', 'token":"[REDACTED]'),
    (r'api[_-]?key["\']?\s*[:=]\s*["\']?[^"\']+', 'api_key":"[REDACTED]'),
    (r'Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+', 'Bearer [REDACTED]'),
    (r'postgresql://[^:]+:[^@]+@', 'postgresql://[REDACTED]@'),
    (r'mongodb(\+srv)?://[^:]+:[^@]+@', 'mongodb://[REDACTED]@'),
    (r'File "/[^"]+", line \d+', '[FILE PATH REMOVED]'),
    (r'/home/[^/]+/', '[PATH REMOVED]'),
    (r'C:\\Users\\[^\\]+\\', '[PATH REMOVED]'),
]

# Stack trace lines to remove
STACK_TRACE_INDICATORS = [
    'Traceback (most recent call last)',
    'File "',
    '    at ',
    'Stack trace:',
]

def sanitize_error_message(message: str, remove_stack_trace: bool = True) -> str:
    """
    Remove sensitive information from error messages.
    
    Args:
        message: The error message to sanitize
        remove_stack_trace: Whether to remove stack traces
    
    Returns:
        Sanitized error message
    """
    if not message:
        return message
    
    sanitized = message
    
    # Apply pattern-based sanitization
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    # Remove stack traces if requested
    if remove_stack_trace:
        for indicator in STACK_TRACE_INDICATORS:
            if indicator in sanitized:
                # Find the start of the traceback
                lines = sanitized.split('\n')
                filtered_lines = []
                in_traceback = False
                
                for line in lines:
                    if any(ind in line for ind in STACK_TRACE_INDICATORS):
                        in_traceback = True
                        continue
                    if in_traceback and line.strip() == '':
                        continue
                    if in_traceback and not any(line.startswith(' ' * 4 + ind) for ind in ['File ', '    ']):
                        in_traceback = False
                    
                    if not in_traceback:
                        filtered_lines.append(line)
                
                sanitized = '\n'.join(filtered_lines)
    
    return sanitized.strip()

def sanitize_dict(data: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
    """
    Recursively sanitize a dictionary, removing sensitive keys.
    
    Args:
        data: Dictionary to sanitize
        depth: Current recursion depth (to prevent infinite loops)
    
    Returns:
        Sanitized dictionary
    """
    if depth > 10:  # Prevent infinite recursion
        return {"[MAX DEPTH REACHED]": True}
    
    if not isinstance(data, dict):
        return data
    
    sensitive_keys = {
        'password', 'secret', 'token', 'api_key', 'apikey',
        'authorization', 'access_token', 'refresh_token', 'session_id',
        'credit_card', 'cvv', 'ssn', 'private_key', 'public_key'
    }
    
    sanitized = {}
    
    for key, value in data.items():
        # Check if key is sensitive
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, depth + 1)
        elif isinstance(value, str):
            sanitized[key] = sanitize_error_message(value)
        else:
            sanitized[key] = value
    
    return sanitized

def create_safe_error_response(error: Exception, include_details: bool = False) -> Dict:
    """
    Create a safe error response that doesn't expose sensitive information.
    
    Args:
        error: The exception that occurred
        include_details: Whether to include technical details
    
    Returns:
        Safe error response dictionary
    """
    response = {
        "error": {
            "type": type(error).__name__,
            "message": sanitize_error_message(str(error))
        }
    }
    
    if include_details:
        # Sanitize any details that might contain sensitive info
        details = {"original_type": type(error).__module__ + "." + type(error).__name__}
        response["error"]["details"] = details
    
    return response
```

---

## 4. Error Notification Systems

### 4.1 Notification Service

```python
# app/errors/notifications.py
import asyncio
import httpx
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache

from app.core.settings import settings

logger = logging.getLogger(__name__)

class NotificationLevel(Enum):
    """Notification urgency levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ErrorNotification:
    """Structured error notification for alerting."""
    level: NotificationLevel
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    environment: str = "unknown"
    service: str = "saarthi-backend"
    error_type: str = ""
    error_trace: Optional[str] = None
    request_info: Dict[str, Any] = field(default_factory=dict)
    user_info: Dict[str, Any] = field(default_factory=dict)
    additional_data: Dict[str, Any] = field(default_factory=dict)

class ErrorNotifier:
    """Service for sending error notifications to various channels."""
    
    def __init__(self):
        self.enabled = settings.ENABLE_ERROR_NOTIFICATIONS
        self.webhook_url = settings.ERROR_NOTIFICATION_WEBHOOK
        self.environment = settings.ENVIRONMENT
    
    async def notify(self, error: Exception, request = None) -> bool:
        """
        Send error notification.
        
        Args:
            error: The exception that occurred
            request: Optional FastAPI request object
        
        Returns:
            True if notification was sent successfully
        """
        if not self.enabled:
            logger.debug("Error notifications disabled, skipping")
            return False
        
        # Determine notification level based on error type
        level = self._determine_level(error)
        
        # Only notify for warnings and above in production
        if self.environment == "production" and level == NotificationLevel.INFO:
            return False
        
        # Build notification
        notification = self._build_notification(error, request, level)
        
        # Send to configured channels
        success = True
        
        # Send to webhook
        if self.webhook_url:
            webhook_success = await self._send_webhook(notification)
            success = success and webhook_success
        
        # Send to email for critical errors in production
        if level == NotificationLevel.CRITICAL and self.environment == "production":
            await self._send_critical_alert(notification)
        
        return success
    
    def _determine_level(self, error: Exception) -> NotificationLevel:
        """Determine notification level based on error."""
        error_type = type(error).__name__.lower()
        
        if any(word in error_type for word in ['critical', 'fatal', 'security']):
            return NotificationLevel.CRITICAL
        elif any(word in error_type for word in ['error', 'exception', 'failure']):
            return NotificationLevel.ERROR
        elif any(word in error_type for word in ['warning', 'warn']):
            return NotificationLevel.WARNING
        else:
            return NotificationLevel.INFO
    
    def _build_notification(
        self, 
        error: Exception, 
        request, 
        level: NotificationLevel
    ) -> ErrorNotification:
        """Build error notification object."""
        
        # Extract request info if available
        request_info = {}
        if request:
            request_info = {
                "method": getattr(request, "method", "UNKNOWN"),
                "path": str(getattr(request, "url", "UNKNOWN")),
                "client_ip": request.client.host if hasattr(request, "client") and request.client else None,
                "user_agent": request.headers.get("user-agent", "Unknown"),
            }
        
        return ErrorNotification(
            level=level,
            title=f"{level.value.upper()}: {type(error).__name__}",
            message=str(error),
            environment=self.environment,
            error_type=type(error).__name__,
            error_trace=self._format_traceback(error),
            request_info=request_info,
        )
    
    def _format_traceback(self, error: Exception) -> Optional[str]:
        """Format error traceback."""
        import traceback
        return traceback.format_exc()
    
    async def _send_webhook(self, notification: ErrorNotification) -> bool:
        """Send notification to webhook."""
        if not self.webhook_url:
            return False
        
        payload = {
            "level": notification.level.value,
            "title": notification.title,
            "message": notification.message,
            "timestamp": notification.timestamp.isoformat(),
            "environment": notification.environment,
            "service": notification.service,
            "error_type": notification.error_type,
            "error_trace": notification.error_trace,
            "request": notification.request_info,
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"Error notification sent: {notification.title}")
                    return True
                else:
                    logger.warning(f"Webhook notification failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False
    
    async def _send_critical_alert(self, notification: ErrorNotification) -> None:
        """Send critical alerts via email or other urgent channels."""
        # This would integrate with your email service
        # For now, just log critical alerts
        logger.critical(
            f"CRITICAL ERROR ALERT: {notification.title}\n"
            f"Message: {notification.message}\n"
            f"Environment: {notification.environment}\n"
            f"Time: {notification.timestamp}"
        )

@lru_cache()
def get_notifier() -> ErrorNotifier:
    """Get singleton notifier instance."""
    return ErrorNotifier()

async def send_error_notification(error: Exception, request = None) -> bool:
    """Convenience function to send error notification."""
    notifier = get_notifier()
    return await notifier.notify(error, request)
```

---

## 5. Error Handling Middleware

### 5.1 Global Error Middleware

```python
# app/middleware/error_handling.py
import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.errors.logging import log_error, log_warning
from app.errors.sanitizer import sanitize_dict
from app.errors.notifications import get_notifier

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for centralized error handling and request/response logging.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.notifier = get_notifier()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request ID to headers
        request.state.start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Log slow requests
            duration = time.time() - request.state.start_time
            if duration > 5.0:  # Slow request threshold
                log_warning(
                    f"Slow request detected",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    duration=duration
                )
            
            return response
            
        except Exception as exc:
            # Handle uncaught exceptions
            duration = time.time() - request.state.start_time
            
            # Log the error
            log_error(
                error=exc,
                context={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration": duration,
                }
            )
            
            # Send notification
            await self.notifier.notify(exc, request)
            
            # Re-raise to be handled by exception handlers
            raise

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.state.request_id if hasattr(request.state, "request_id") else "none"
        
        # Log incoming request
        logger.info(
            f"Request started: {request.method} {request.url.path} "
            f"[Request ID: {request_id}]"
        )
        
        response = await call_next(request)
        
        # Log response
        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"Status: {response.status_code} [Request ID: {request_id}]"
        )
        
        return response

# Rate limiting middleware
from app.middleware.rate_limit import RateLimitMiddleware
```

### 5.2 Rate Limiting Middleware

```python
# app/middleware/rate_limit.py
import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.core.settings import settings
from app.errors.logging import log_warning

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    For production, use Redis-based rate limiting.
    """
    
    def __init__(self, app: ASGIApp, requests_per_minute: int = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_PER_MINUTE
        self.window_size = 60  # seconds
        self.request_history: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier (IP or user ID if authenticated)
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not self._check_rate_limit(client_id):
            log_warning(
                "Rate limit exceeded",
                client_id=client_id,
                path=request.url.path
            )
            
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": "60"}
            )
        
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique identifier for the client."""
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host if request.client else 'unknown'}"
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limit."""
        current_time = time.time()
        
        # Initialize if first request
        if client_id not in self.request_history:
            self.request_history[client_id] = []
        
        # Remove requests outside the current window
        self.request_history[client_id] = [
            req_time for req_time in self.request_history[client_id]
            if current_time - req_time < self.window_size
        ]
        
        # Check if within limit
        if len(self.request_history[client_id]) >= self.requests_per_minute:
            return False
        
        # Add current request
        self.request_history[client_id].append(current_time)
        return True
```

---

## 6. Error Response Formats

### 6.1 API Error Response Schema

```python
# app/schemas/error.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ErrorCode(str, Enum):
    """Standard error codes."""
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

class ValidationErrorDetail(BaseModel):
    """Detailed validation error information."""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Human-readable error message")
    type: str = Field(..., description="Type of validation error")

class ErrorResponse(BaseModel):
    """Standard API error response."""
    error: Dict[str, Any] = Field(
        ...,
        description: "Error object containing details"
    )
    
    @classmethod
    def create(
        cls,
        code: ErrorCode,
        message: str,
        status_code: int,
        details: Optional[Dict[str, Any]] = None,
        validation_errors: Optional[List[ValidationErrorDetail]] = None,
        request_id: Optional[str] = None,
        include_timestamp: bool = True
    ) -> "ErrorResponse":
        """Factory method to create standardized error responses."""
        error_obj = {
            "code": code.value,
            "message": message,
        }
        
        if details:
            error_obj["details"] = details
        
        if validation_errors:
            error_obj["validation_errors"] = [
                ve.model_dump() for ve in validation_errors
            ]
        
        if request_id:
            error_obj["request_id"] = request_id
        
        if include_timestamp:
            error_obj["timestamp"] = datetime.utcnow().isoformat()
        
        return cls(error=error_obj)
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "The requested resource was not found",
                    "details": {"resource_type": "campaign", "resource_id": "123"},
                    "request_id": "abc-123-def",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }

# For HTML responses, we return rendered templates
# See Section 1 for HTML error page implementation

# Response helpers
from fastapi import Request
from fastapi.responses import JSONResponse

def error_response(
    code: ErrorCode,
    message: str,
    status_code: int,
    **kwargs
) -> JSONResponse:
    """Create a JSON error response."""
    error = ErrorResponse.create(
        code=code,
        message=message,
        status_code=status_code,
        **kwargs
    )
    
    # Add request_id from request state if available
    # (This would be passed from the endpoint)
    
    return JSONResponse(
        status_code=status_code,
        content=error.model_dump()
    )

def validation_error_response(
    message: str,
    validation_errors: List[ValidationErrorDetail],
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create a validation error response."""
    error = ErrorResponse.create(
        code=ErrorCode.VALIDATION_ERROR,
        message=message,
        status_code=400,
        validation_errors=validation_errors,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=400,
        content=error.model_dump()
    )
```

### 6.2 API Response Formatting

```python
# app/routers/utils.py
from typing import TypeVar, Generic, Optional, List
from pydantic import BaseModel, Field
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    data: Optional[T] = None
    error: Optional[dict] = None
    meta: Optional[dict] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "data": {"id": 1, "name": "Example"},
                "error": None,
                "meta": {"request_id": "abc-123"}
            }
        }

class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response."""
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse[T]":
        """Create paginated response."""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

# Decorator for error handling in routes
from functools import wraps
import traceback

def handle_errors(code_prefix: str = "ROUTE"):
    """Decorator to standardize error handling in route handlers."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as exc:
                # Log full error
                logger.error(f"Route error in {func.__name__}: {exc}", exc_info=True)
                
                # Return generic error (actual handling done by exception handlers)
                raise
        
        return wrapper
    return decorator
```

---

## 7. Development vs Production Configurations

### 7.1 Environment-Based Settings

```python
# app/core/settings.py (Extended)
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List
import os

class Settings(BaseSettings):
    """Application settings with environment-specific defaults."""
    
    # Environment
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    API_TITLE: str = "Saarthi API"
    API_VERSION: str = "1.0.0"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost/db"
    DATABASE_POOL_SIZE: int = 5
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Error Handling - Development Settings
    DEBUG: bool = True
    SHOW_DETAILED_ERRORS: bool = True  # Show stack traces
    LOG_LEVEL: str = "DEBUG"
    
    # Error Handling - Production Settings
    ENABLE_ERROR_NOTIFICATIONS: bool = False
    ERROR_NOTIFICATION_WEBHOOK: Optional[str] = None
    ERROR_NOTIFICATION_EMAIL: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    ENABLE_RATE_LIMITING: bool = True
    
    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    RETRY_BACKOFF: float = 2.0
    
    # External Services
    EXTERNAL_SERVICE_TIMEOUT: int = 30
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT == "development"
    
    def get_error_config(self) -> dict:
        """Get error handling configuration based on environment."""
        if self.is_production:
            return {
                "show_details": False,
                "show_traceback": False,
                "log_errors": True,
                "notify_on_error": self.ENABLE_ERROR_NOTIFICATIONS,
                "sanitize_errors": True,
            }
        else:
            return {
                "show_details": self.SHOW_DETAILED_ERRORS,
                "show_traceback": self.SHOW_DETAILED_ERRORS,
                "log_errors": True,
                "notify_on_error": False,
                "sanitize_errors": False,
            }
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Override settings based on ENVIRONMENT
def get_settings() -> Settings:
    """Get application settings with environment-specific overrides."""
    settings = Settings()
    
    if settings.is_production:
        # Production defaults
        settings.SHOW_DETAILED_ERRORS = False
        settings.LOG_LEVEL = "WARNING"
        settings.ENABLE_RATE_LIMITING = True
    elif settings.ENVIRONMENT == "staging":
        # Staging defaults
        settings.SHOW_DETAILED_ERRORS = True
        settings.LOG_LEVEL = "INFO"
        settings.ENABLE_RATE_LIMITING = True
    
    return settings

settings = get_settings()
```

### 7.2 Environment-Specific App Initialization

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import (
    request_validation_exception_handler,
    http_exception_handler,
)
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.settings import settings
from app.errors.handlers import register_exception_handlers
from app.middleware.error_handling import ErrorHandlingMiddleware, RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.API_TITLE,
        version=settings.API_VERSION,
        debug=settings.DEBUG,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add error handling middleware
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Add request logging (development only)
    if settings.is_development:
        app.add_middleware(RequestLoggingMiddleware)
    
    # Add rate limiting (production and staging)
    if settings.is_production or settings.ENVIRONMENT == "staging":
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.RATE_LIMIT_PER_MINUTE
        )
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Include routers
    from app.routers import auth, campaigns, leads, inbox, settings as settings_router
    
    app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["auth"])
    app.include_router(campaigns.router, prefix=settings.API_V1_PREFIX, tags=["campaigns"])
    app.include_router(leads.router, prefix=settings.API_V1_PREFIX, tags=["leads"])
    app.include_router(inbox.router, prefix=settings.API_V1_PREFIX, tags=["inbox"])
    app.include_router(settings_router.router, prefix=settings.API_V1_PREFIX, tags=["settings"])
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "version": settings.API_VERSION
        }
    
    @app.get("/")
    async def root():
        return {
            "message": "Welcome to Saarthi API",
            "docs": "/docs" if not settings.is_production else None
        }
    
    return app

app = create_app()
```

---

## 8. Error Retry Mechanisms

### 8.1 Retry Decorator and Utilities

```python
# app/utils/retry.py
import asyncio
import functools
import logging
from typing import Callable, Type, Tuple, Optional, Any
from datetime import datetime
from enum import Enum

from app.errors.logging import log_warning, log_error
from app.core.settings import settings

logger = logging.getLogger(__name__)

class RetryStrategy(str, Enum):
    """Retry strategy types."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"

class RetryableError(Exception):
    """Base class for errors that should trigger a retry."""
    pass

class NonRetryableError(Exception):
    """Base class for errors that should NOT trigger a retry."""
    pass

def retry_with_backoff(
    max_attempts: int = None,
    initial_delay: float = None,
    backoff_factor: float = None,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    max_delay: float = 60.0,
    on_retry: Optional[Callable] = None,
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (default from settings)
        initial_delay: Initial delay in seconds (default from settings)
        backoff_factor: Multiplier for delay after each retry (default from settings)
        retry_on: Tuple of exception types to retry on
        retry_strategy: Strategy for calculating delay
        max_delay: Maximum delay between retries
        on_retry: Optional callback function called on each retry
    """
    max_attempts = max_attempts or settings.MAX_RETRIES
    initial_delay = initial_delay or settings.RETRY_DELAY
    backoff_factor = backoff_factor or settings.RETRY_BACKOFF
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e
                    
                    # Don't retry on last attempt
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts"
                        )
                        raise
                    
                    # Calculate delay
                    delay = calculate_delay(
                        attempt=attempt,
                        initial_delay=initial_delay,
                        backoff_factor=backoff_factor,
                        strategy=retry_strategy,
                        max_delay=max_delay
                    )
                    
                    # Log retry attempt
                    log_warning(
                        f"Retry attempt {attempt}/{max_attempts} for {func.__name__}",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(e)
                    )
                    
                    # Call on_retry callback if provided
                    if on_retry:
                        on_retry(attempt, e)
                    
                    # Wait before retry
                    await asyncio.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts"
                        )
                        raise
                    
                    delay = calculate_delay(
                        attempt=attempt,
                        initial_delay=initial_delay,
                        backoff_factor=backoff_factor,
                        strategy=retry_strategy,
                        max_delay=max_delay
                    )
                    
                    log_warning(
                        f"Retry attempt {attempt}/{max_attempts} for {func.__name__}",
                        function=func.__name__,
                        attempt=attempt,
                        delay=delay
                    )
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    import time
                    time.sleep(delay)
            
            raise last_exception
        
        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def calculate_delay(
    attempt: int,
    initial_delay: float,
    backoff_factor: float,
    strategy: RetryStrategy,
    max_delay: float
) -> float:
    """Calculate delay based on retry strategy."""
    
    if strategy == RetryStrategy.FIXED:
        delay = initial_delay
    elif strategy == RetryStrategy.LINEAR:
        delay = initial_delay * attempt
    elif strategy == RetryStrategy.EXPONENTIAL:
        delay = initial_delay * (backoff_factor ** (attempt - 1))
    else:
        delay = initial_delay
    
    # Cap at max_delay
    return min(delay, max_delay)

# Circuit breaker for external services
class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent cascading failures.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state: str = "closed"  # closed, open, half-open"
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        
        if self.state == "open":
            # Check if recovery timeout has passed
            if self.last_failure_time:
                time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.recovery_timeout:
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset circuit breaker
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection."""
        
        if self.state == "open":
            if self.last_failure_time:
                import time
                time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.recovery_timeout:
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise
    
    def reset(self):
        """Manually reset the circuit breaker."""
        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = None
```

### 8.2 Using Retry with External Services

```python
# app/providers/llm/openrouter_provider.py (Example with retry)
from app.utils.retry import retry_with_backoff, RetryStrategy, NonRetryableError
from app.errors.handlers import ExternalServiceError
import httpx

class LLMProviderError(NonRetryableError):
    """Error that should not trigger a retry."""
    pass

class OpenRouterProvider:
    """LLM provider with retry logic."""
    
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0
        )
    
    @retry_with_backoff(
        max_attempts=3,
        initial_delay=1.0,
        backoff_factor=2.0,
        retry_on=(httpx.HTTPError, httpx.TimeoutException),
        retry_strategy=RetryStrategy.EXPONENTIAL,
        on_retry=lambda attempt, error: logger.warning(
            f"LLM request retry {attempt}: {error}"
        )
    )
    async def generate_completion(
        self,
        prompt: str,
        model: str = "openai/gpt-4",
        **kwargs
    ) -> str:
        """
        Generate completion with automatic retry on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        **kwargs
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 429:
                    # Rate limited - raise to trigger retry
                    raise httpx.HTTPError("Rate limited")
                
                if response.status_code >= 500:
                    # Server error - raise to trigger retry
                    raise httpx.HTTPError(f"Server error: {response.status_code}")
                
                if response.status_code != 200:
                    # Client error - don't retry
                    raise LLMProviderError(f"API error: {response.status_code}")
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
        except httpx.TimeoutException:
            raise ExternalServiceError("openrouter", "Request timed out")
    
    @retry_with_backoff(max_attempts=3)
    async def generate_with_fallback(
        self,
        prompt: str,
        primary_model: str = "openai/gpt-4",
        fallback_model: str = "anthropic/claude-3-sonnet"
    ) -> str:
        """Try primary model, fall back to secondary on failure."""
        models_to_try = [primary_model, fallback_model]
        last_error = None
        
        for model in models_to_try:
            try:
                return await self.generate_completion(prompt, model=model)
            except NonRetryableError:
                # Don't retry non-retryable errors
                raise
            except Exception as e:
                last_error = e
                log_warning(
                    f"Model {model} failed, trying next",
                    error=str(e)
                )
        
        raise last_error
```

---

## Summary

This guide covered all 8 aspects of error handling in FastAPI applications:

1. **Custom Error Pages**: HTML templates and JSON responses for different HTTP status codes
2. **Error Logging**: Structured logging with file rotation and environment-specific configuration
3. **User-Friendly Messages**: Sanitized error messages that don't expose sensitive system information
4. **Notification Systems**: Webhook and email notifications for critical errors
5. **Middleware**: Global error handling and rate limiting middleware
6. **Response Formats**: Standardized JSON responses for APIs
7. **Dev vs Prod**: Environment-specific configurations for error handling
8. **Retry Mechanisms**: Exponential backoff with circuit breaker pattern

### Key Best Practices

- **Always sanitize error messages** in production to prevent information disclosure
- **Log comprehensively** but store sensitive data securely
- **Use retry mechanisms** for transient failures but implement circuit breakers to prevent cascading failures
- **Notify on critical errors** but avoid alert fatigue with proper severity levels
- **Return consistent error formats** across all endpoints
- **Test error handling** thoroughly including edge cases

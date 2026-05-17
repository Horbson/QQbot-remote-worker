# -*- coding: utf-8 -*-
"""
Unified exception handling for QQ-facing workflows.

Business code should raise SafeError subclasses when a message can be safely
shown to the user. Event boundaries call handle_error to log full details and
return a compact user-facing response.
"""
import traceback
import uuid
from enum import Enum
from functools import wraps
from typing import Any, Dict

from botpy import logging

_log = logging.get_logger(__name__)


class ErrorLevel(Enum):
    """Severity for user-facing safe errors."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SafeError(Exception):
    """Base class for errors whose message can be shown to QQ users."""

    def __init__(self, message: str, level: ErrorLevel = ErrorLevel.ERROR):
        self.message = message
        self.level = level
        super().__init__(message)


class UserFriendlyError(SafeError):
    """The user can understand or resolve this error."""
    pass


class SystemError(SafeError):
    """Internal system failure. Do not expose details to users."""
    pass


class ConfigurationError(SafeError):
    """Missing or invalid runtime configuration."""
    pass


class NetworkError(SafeError):
    """External network or API failure."""
    pass


class PermissionError(SafeError):
    """Authentication, authorization, or permission failure."""
    pass


ERROR_MESSAGES = {
    ErrorLevel.INFO: "提示：{message}",
    ErrorLevel.WARNING: "警告：{message}",
    ErrorLevel.ERROR: "发生错误：{message}",
    ErrorLevel.CRITICAL: "系统错误，请稍后重试或联系管理员。",
}


def _log_exception(error_id: str, error: Exception, context: str) -> None:
    message = f"[{error_id}] {context}: {type(error).__name__}: {error}"
    if hasattr(_log, "exception"):
        _log.exception(message)
    else:
        _log.error(f"{message}\nTraceback:\n{traceback.format_exc()}")


def _safe_message(error: SafeError) -> str:
    if isinstance(error, SystemError):
        return ERROR_MESSAGES[ErrorLevel.CRITICAL]
    if isinstance(error, ConfigurationError):
        return f"配置错误：{error.message}"
    if isinstance(error, NetworkError):
        return f"网络或外部服务错误：{error.message}"
    if isinstance(error, PermissionError):
        return f"权限错误：{error.message}"
    return ERROR_MESSAGES[error.level].format(message=error.message)


def handle_error(
    error: Exception,
    context: str = "",
    default_message: str = "操作失败，请稍后重试。",
) -> Dict[str, Any]:
    """
    Log an exception and convert it into a user-facing result.

    The returned message is safe to send back to QQ. The error_code is included
    both in the log and the user message so reports can be traced quickly.
    """
    error_id = str(uuid.uuid4())[:8]
    _log_exception(error_id, error, context or "unknown")

    if isinstance(error, SafeError):
        message = _safe_message(error)
        level = error.level.value
    else:
        message = default_message
        level = ErrorLevel.ERROR.value

    return {
        "success": False,
        "message": f"{message}\n错误编号：{error_id}",
        "error_code": error_id,
        "level": level,
    }


def error_decorator(context: str = "", default_message: str = "操作失败"):
    """Decorator that converts exceptions into user-facing messages."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                result = handle_error(e, context, default_message)
                return result["message"]

        return wrapper

    return decorator

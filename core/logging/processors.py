import re
from typing import Any, Dict
import structlog

TOKEN_PATTERN = re.compile(r'[NM][A-Za-z0-9._-]{20,}')
SENSITIVE_KEYS = frozenset({'token', 'password', 'secret', 'api_key', 'authorization'})


def redact_sensitive_data(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: Dict[str, Any],
) -> Dict[str, Any]:
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            event_dict[key] = TOKEN_PATTERN.sub('[REDACTED]', value)
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = '[REDACTED]'
    return event_dict


def add_service_context(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: Dict[str, Any],
) -> Dict[str, Any]:
    event_dict.setdefault("service", "bhnbot")
    return event_dict


def drop_color_message_key(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: Dict[str, Any],
) -> Dict[str, Any]:
    event_dict.pop("color_message", None)
    return event_dict

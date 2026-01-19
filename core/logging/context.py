from contextvars import ContextVar
from typing import Any, Dict, Optional
import uuid

_user_id: ContextVar[Optional[int]] = ContextVar("user_id", default=None)
_guild_id: ContextVar[Optional[int]] = ContextVar("guild_id", default=None)
_channel_id: ContextVar[Optional[int]] = ContextVar("channel_id", default=None)
_command: ContextVar[Optional[str]] = ContextVar("command", default=None)
_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_span_id: ContextVar[Optional[str]] = ContextVar("span_id", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def bind_context(
    *,
    user_id: Optional[int] = None,
    guild_id: Optional[int] = None,
    channel_id: Optional[int] = None,
    command: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    if user_id is not None:
        _user_id.set(user_id)
    if guild_id is not None:
        _guild_id.set(guild_id)
    if channel_id is not None:
        _channel_id.set(channel_id)
    if command is not None:
        _command.set(command)
    if trace_id is not None:
        _trace_id.set(trace_id)
    if span_id is not None:
        _span_id.set(span_id)
    if request_id is not None:
        _request_id.set(request_id)
    elif _request_id.get() is None:
        _request_id.set(str(uuid.uuid4())[:8])


def clear_context() -> None:
    _user_id.set(None)
    _guild_id.set(None)
    _channel_id.set(None)
    _command.set(None)
    _trace_id.set(None)
    _span_id.set(None)
    _request_id.set(None)


def get_current_context() -> Dict[str, Any]:
    context = {}
    if (val := _user_id.get()) is not None:
        context["user_id"] = val
    if (val := _guild_id.get()) is not None:
        context["guild_id"] = val
    if (val := _channel_id.get()) is not None:
        context["channel_id"] = val
    if (val := _command.get()) is not None:
        context["command"] = val
    if (val := _trace_id.get()) is not None:
        context["trace_id"] = val
    if (val := _span_id.get()) is not None:
        context["span_id"] = val
    if (val := _request_id.get()) is not None:
        context["request_id"] = val
    return context


def get_user_id() -> Optional[int]:
    return _user_id.get()


def get_guild_id() -> Optional[int]:
    return _guild_id.get()


def get_trace_id() -> Optional[str]:
    return _trace_id.get()


def get_request_id() -> Optional[str]:
    return _request_id.get()

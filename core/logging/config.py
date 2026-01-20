import json
import logging
import os
import re
import sys
import threading
import queue
from logging.handlers import TimedRotatingFileHandler, QueueHandler, QueueListener
from pathlib import Path
from typing import Any, Optional

import structlog

from core.logging.processors import redact_sensitive_data, add_service_context

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_configured = False
_config_lock = threading.Lock()
_listeners: list[QueueListener] = []
_file_handlers: dict[str, TimedRotatingFileHandler] = {}
_file_handler_lock = threading.Lock()
_loki_handler: Optional[logging.Handler] = None


EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U0001F900-\U0001F9FF"
    "\U00002600-\U000026FF"
    "\U00002300-\U000023FF"
    "\U0000200D"
    "\U0000FE0F"
    "\U00002B50"
    "\U00002714"
    "\U00002716"
    "\U0001FA00-\U0001FAFF"
    "]+",
    flags=re.UNICODE,
)


class DualFormatFormatter(logging.Formatter):
    
    def __init__(self, pretty: bool = False):
        super().__init__()
        self.pretty = pretty
    
    def _strip_emoji(self, text: str) -> str:
        return EMOJI_PATTERN.sub("", text).strip()
    
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        
        if self.pretty:
            try:
                data = json.loads(msg)
                level = data.get("level", "INFO").upper()
                logger_name = data.get("logger", "unknown")
                event = self._strip_emoji(data.get("event", msg))
                timestamp = data.get("timestamp", "")[:19].replace("T", " ")
                
                level_colors = {
                    "DEBUG": "\033[36m",
                    "INFO": "\033[32m", 
                    "WARNING": "\033[33m",
                    "ERROR": "\033[31m",
                    "CRITICAL": "\033[35m",
                }
                reset = "\033[0m"
                color = level_colors.get(level, "")
                
                extra_keys = [k for k in data.keys() if k not in ("event", "logger", "level", "timestamp", "service")]
                extra = ""
                if extra_keys:
                    extra = " " + " ".join(f"{k}={data[k]}" for k in extra_keys[:5])
                
                return f"{timestamp} {color}[{level}]{reset} {logger_name}: {event}{extra}"
            except (json.JSONDecodeError, TypeError):
                return self._strip_emoji(msg)
        else:
            return msg


def configure_logging(
    level: int = logging.INFO,
    log_file: str = "logs/app.log",
    enable_console: bool = True,
    enable_loki: bool = True,
) -> None:
    global _configured
    
    with _config_lock:
        if _configured:
            return
        
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                add_service_context,
                redact_sensitive_data,
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        _configured = True
        
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        json_formatter = DualFormatFormatter(pretty=False)
        pretty_formatter = DualFormatFormatter(pretty=True)
        
        file_handler = TimedRotatingFileHandler(
            filename=log_path,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setFormatter(json_formatter)
        file_handler.setLevel(level)
        
        log_queue: queue.Queue[Any] = queue.Queue(-1)
        queue_handler = QueueHandler(log_queue)
        
        handlers_for_listener: list[logging.Handler] = [file_handler]
        
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(pretty_formatter)
            console_handler.setLevel(level)
            handlers_for_listener.append(console_handler)
        
        global _loki_handler
        if enable_loki:
            loki_url = os.getenv("LOKI_URL")
            if loki_url:
                from core.logging.loki import LokiHandler
                _loki_handler = LokiHandler(url=loki_url)
                _loki_handler.setFormatter(json_formatter)
                _loki_handler.setLevel(level)
                handlers_for_listener.append(_loki_handler)
        
        listener = QueueListener(
            log_queue,
            *handlers_for_listener,
            respect_handler_level=True,
        )
        listener.start()
        _listeners.append(listener)
        
        root_logger.addHandler(queue_handler)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    if not _configured:
        configure_logging()
    return structlog.get_logger(name)


def setup_logger(
    logger_name: str,
    file_path: str,
    level: int = logging.INFO,
) -> logging.Logger:
    if not _configured:
        configure_logging(level=level)
    
    logger = get_logger("logging_config")
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    full_log_path = LOG_DIR / file_path
    full_log_path_str = str(full_log_path)
    full_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    formatter = logging.Formatter("%(message)s")
    
    with _file_handler_lock:
        if full_log_path_str in _file_handlers:
            file_handler = _file_handlers[full_log_path_str]
        else:
            file_handler = TimedRotatingFileHandler(
                filename=full_log_path,
                when="midnight",
                interval=1,
                backupCount=30,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            _file_handlers[full_log_path_str] = file_handler
    
    log_queue: queue.Queue[Any] = queue.Queue(-1)
    queue_handler = QueueHandler(log_queue)
    
    listener = QueueListener(log_queue, file_handler, respect_handler_level=True)
    listener.start()
    _listeners.append(listener)
    
    logger.addHandler(queue_handler)
    
    return logger


def shutdown_logging() -> None:
    global _loki_handler
    # Flush Loki handler before stopping
    if _loki_handler is not None:
        try:
            _loki_handler._flush()
        except Exception:
            pass
    for listener in _listeners:
        listener.stop()
    _listeners.clear()


def get_loki_handler() -> Optional[logging.Handler]:
    """Return the Loki handler if configured."""
    return _loki_handler

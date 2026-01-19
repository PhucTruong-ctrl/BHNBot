import logging
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


def configure_logging(
    level: int = logging.INFO,
    log_file: str = "logs/app.log",
    enable_console: bool = True,
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
        
        formatter = logging.Formatter("%(message)s")
        
        file_handler = TimedRotatingFileHandler(
            filename=log_path,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        
        log_queue: queue.Queue[Any] = queue.Queue(-1)
        queue_handler = QueueHandler(log_queue)
        
        handlers_for_listener: list[logging.Handler] = [file_handler]
        
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(level)
            handlers_for_listener.append(console_handler)
        
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
    for listener in _listeners:
        listener.stop()
    _listeners.clear()

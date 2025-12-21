import logging
import os
from logging.handlers import TimedRotatingFileHandler
import sys
from pathlib import Path

# Base logs directory
LOG_DIR = Path("logs")

def setup_logger(logger_name: str, file_path: str, level=logging.INFO) -> logging.Logger:
    """Configures a standardized logger with file and console handlers.

    The logger automatically rotates log files daily and retains them for 30 days.

    Args:
        logger_name (str): Unique identifier for the logger (e.g., 'DBManager').
        file_path (str): Relative path for the log file within the 'logs/' directory.
                         Example: 'core/database.log'.
        level (int, optional): The logging threshold. Defaults to logging.INFO.

    Returns:
        logging.Logger: The configured logger instance.

    Example:
        >>> logger = setup_logger("MyModule", "modules/my_module.log")
        >>> logger.info("Logger initialized.")
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # Check if handler already exists to avoid duplicate logs
    if logger.handlers:
        return logger
        
    # Create full path
    full_log_path = LOG_DIR / file_path
    
    # Create directories if they don't exist
    os.makedirs(os.path.dirname(full_log_path), exist_ok=True)
    
    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 1. File Handler (Timed Rotation - Daily)
    file_handler = TimedRotatingFileHandler(
        filename=full_log_path,
        when="midnight",
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 2. Console Handler (Standard Output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

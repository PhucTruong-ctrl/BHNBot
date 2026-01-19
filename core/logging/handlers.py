"""
Async file handlers with retention policies for BHNBot structured logging.

This module provides async-safe file handlers that integrate with the QueueHandler
pattern to prevent blocking I/O in async contexts, along with retention cleanup
utilities for managing log file lifecycle.
"""

import glob
import json
import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler
from typing import Dict


class AsyncFileHandler(TimedRotatingFileHandler):
    """
    Async-safe file handler extending TimedRotatingFileHandler.
    
    This handler is designed to be used with QueueHandler/QueueListener
    for async safety. It adds retention cleanup on rotation.
    """
    
    def __init__(self, filename: str, retention_days: int = 30, **kwargs):
        super().__init__(filename, **kwargs)
        self.retention_days = retention_days
    
    def doRollover(self):
        """Override to add retention cleanup after rotation."""
        super().doRollover()
        # Cleanup old logs after rotation
        log_dir = os.path.dirname(self.baseFilename)
        cleanup_old_logs(log_dir, {}, self.retention_days)


def cleanup_old_logs(
    log_dir: str, 
    retention_days_by_level: Dict[str, int], 
    default_retention_days: int = 30
) -> None:
    """
    Clean up old log files based on retention policies.
    
    Parses the first line of each .log file as JSON to determine log level,
    then removes files older than the retention period for that level.
    
    Args:
        log_dir: Directory containing log files
        retention_days_by_level: Dict mapping log levels to retention days
                                 e.g., {'ERROR': 90, 'INFO': 30, 'DEBUG': 7}
        default_retention_days: Default retention for unspecified levels
    """
    if not os.path.exists(log_dir):
        logging.warning(f"Log directory does not exist: {log_dir}")
        return
    
    # Default retention mapping if not provided
    default_mapping = {
        'CRITICAL': 90,
        'ERROR': 90, 
        'WARNING': 30,
        'INFO': 30,
        'DEBUG': 7,
        'NOTSET': 7
    }
    retention_mapping = {**default_mapping, **retention_days_by_level}
    
    removed_count = 0
    for log_file in glob.glob(os.path.join(log_dir, "*.log")):
        try:
            # Get file age in days
            file_mtime = os.path.getmtime(log_file)
            file_age_days = (time.time() - file_mtime) / (24 * 3600)
            
            # Parse first line to get log level
            level = 'INFO'  # default
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line:
                        log_entry = json.loads(first_line)
                        level = log_entry.get('level', 'INFO')
            except (json.JSONDecodeError, UnicodeDecodeError):
                # If we can't parse JSON, assume it's INFO level
                pass
            
            # Check retention
            retention_days = retention_mapping.get(level, default_retention_days)
            if file_age_days > retention_days:
                os.remove(log_file)
                removed_count += 1
                logging.info(
                    f"Removed old log file: {os.path.basename(log_file)} "
                    f"(age: {file_age_days:.1f}d, level: {level}, retention: {retention_days}d)"
                )
                
        except OSError as e:
            logging.warning(f"Error processing log file {log_file}: {e}")
    
    if removed_count > 0:
        logging.info(f"Log cleanup completed: removed {removed_count} old files")

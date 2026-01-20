"""Bot Logs API - View and search bot logs (supports JSON format)."""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/logs", tags=["logs"])

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"


def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
    line = line.strip()
    if not line:
        return None
    
    if line.startswith("{"):
        try:
            data = json.loads(line)
            return {
                "timestamp": data.get("timestamp", "")[:19].replace("T", " "),
                "level": data.get("level", "info").upper(),
                "module": data.get("logger", "unknown"),
                "message": data.get("event", line),
                "extra": {k: v for k, v in data.items() if k not in ("timestamp", "level", "logger", "event", "service")},
            }
        except json.JSONDecodeError:
            pass
    
    old_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[(\w+)\] \[([^\]]+)\] (.+)'
    match = re.match(old_pattern, line)
    if match:
        return {
            "timestamp": match.group(1),
            "level": match.group(2),
            "module": match.group(3),
            "message": match.group(4),
            "extra": {},
        }
    
    return None


def get_log_files() -> List[Dict[str, Any]]:
    if not LOGS_DIR.exists():
        return []
    
    files = []
    for f in LOGS_DIR.glob("*.log*"):
        stat = f.stat()
        files.append({
            "name": f.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "path": str(f)
        })
    
    return sorted(files, key=lambda x: x["modified"], reverse=True)


@router.get("/files")
async def list_log_files() -> Dict[str, Any]:
    return {"files": get_log_files()}


@router.get("/")
async def get_logs(
    file: str = "app.log",
    level: Optional[str] = None,
    module: Optional[str] = None,
    search: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 500,
    offset: int = 0
) -> Dict[str, Any]:
    log_path = LOGS_DIR / file
    
    if not log_path.exists() or not str(log_path.resolve()).startswith(str(LOGS_DIR.resolve())):
        return {"logs": [], "total": 0, "error": "File not found"}
    
    logs = []
    levels_count = {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
    modules_set = set()
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line in reversed(lines):
            parsed = parse_log_line(line)
            if not parsed:
                continue
            
            levels_count[parsed["level"]] = levels_count.get(parsed["level"], 0) + 1
            modules_set.add(parsed["module"])
            
            if level and parsed["level"] != level.upper():
                continue
            
            if module and module.lower() not in parsed["module"].lower():
                continue
            
            if search and search.lower() not in parsed["message"].lower():
                continue
            
            if from_date:
                try:
                    log_dt = datetime.strptime(parsed["timestamp"][:10], "%Y-%m-%d")
                    from_dt = datetime.strptime(from_date, "%Y-%m-%d")
                    if log_dt < from_dt:
                        continue
                except ValueError:
                    pass
            
            if to_date:
                try:
                    log_dt = datetime.strptime(parsed["timestamp"][:10], "%Y-%m-%d")
                    to_dt = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
                    if log_dt >= to_dt:
                        continue
                except ValueError:
                    pass
            
            logs.append(parsed)
        
        total = len(logs)
        logs = logs[offset:offset + limit]
        
    except Exception as e:
        return {"logs": [], "total": 0, "error": str(e)}
    
    return {
        "logs": logs,
        "total": total,
        "file": file,
        "levels": levels_count,
        "modules": sorted(list(modules_set)),
        "limit": limit,
        "offset": offset
    }


@router.get("/stats")
async def get_log_stats() -> Dict[str, Any]:
    stats = {
        "files": [],
        "total_size": 0,
        "levels_today": {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0},
        "errors_24h": 0
    }
    
    files = get_log_files()
    stats["files"] = files[:10]
    stats["total_size"] = sum(f["size"] for f in files)
    
    app_log = LOGS_DIR / "app.log"
    if app_log.exists():
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            with open(app_log, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parsed = parse_log_line(line)
                    if not parsed:
                        continue
                    
                    if parsed["timestamp"].startswith(today):
                        stats["levels_today"][parsed["level"]] = stats["levels_today"].get(parsed["level"], 0) + 1
                    
                    if parsed["level"] in ("ERROR", "CRITICAL"):
                        if parsed["timestamp"].startswith(today) or parsed["timestamp"].startswith(yesterday):
                            stats["errors_24h"] += 1
        except Exception:
            pass
    
    return stats


@router.get("/tail")
async def tail_logs(file: str = "app.log", lines: int = 100) -> Dict[str, Any]:
    log_path = LOGS_DIR / file
    
    if not log_path.exists() or not str(log_path.resolve()).startswith(str(LOGS_DIR.resolve())):
        return {"logs": [], "error": "File not found"}
    
    logs = []
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                parsed = parse_log_line(line)
                if parsed:
                    logs.append(parsed)
    except Exception as e:
        return {"logs": [], "error": str(e)}
    
    return {"logs": logs, "file": file}

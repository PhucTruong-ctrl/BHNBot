"""Loki API proxy for dashboard log viewing."""
import json
import os
from datetime import datetime, timedelta
from typing import Optional
import aiohttp
from fastapi import APIRouter, Query, HTTPException, Depends
from ..dependencies import require_admin

router = APIRouter(prefix="/loki", tags=["loki"], dependencies=[Depends(require_admin)])

LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")
if not LOKI_URL.endswith("/loki/api/v1/push"):
    LOKI_BASE = LOKI_URL.rstrip("/")
else:
    LOKI_BASE = LOKI_URL.replace("/loki/api/v1/push", "")


@router.get("/query")
async def query_logs(
    query: str = Query(default='{service="bhnbot"}', description="LogQL query"),
    limit: int = Query(default=100, ge=1, le=1000),
    start: Optional[str] = None,
    end: Optional[str] = None,
    direction: str = Query(default="backward", pattern="^(forward|backward)$"),
):
    if not start:
        start_time = datetime.utcnow() - timedelta(hours=1)
        start = str(int(start_time.timestamp() * 1_000_000_000))
    if not end:
        end = str(int(datetime.utcnow().timestamp() * 1_000_000_000))
    
    params = {
        "query": query,
        "limit": limit,
        "start": start,
        "end": end,
        "direction": direction,
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{LOKI_BASE}/loki/api/v1/query_range",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=text)
                data = await resp.json()
                return _format_loki_response(data)
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=503, detail=f"Loki unavailable: {e}")


@router.get("/labels")
async def get_labels():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{LOKI_BASE}/loki/api/v1/labels",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=resp.status)
                return await resp.json()
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=503, detail=f"Loki unavailable: {e}")


@router.get("/label/{label}/values")
async def get_label_values(label: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{LOKI_BASE}/loki/api/v1/label/{label}/values",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=resp.status)
                return await resp.json()
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=503, detail=f"Loki unavailable: {e}")


@router.get("/ready")
async def check_loki_ready():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{LOKI_BASE}/ready",
                timeout=aiohttp.ClientTimeout(total=3),
            ) as resp:
                return {"status": "ready" if resp.status == 200 else "not_ready"}
    except aiohttp.ClientError:
        return {"status": "unavailable"}


def _format_loki_response(data: dict) -> dict:
    logs = []
    
    result = data.get("data", {}).get("result", [])
    for stream in result:
        labels = stream.get("stream", {})
        for ts, line in stream.get("values", []):
            try:
                parsed = json.loads(line)
                logs.append({
                    "timestamp": parsed.get("timestamp", ""),
                    "level": parsed.get("level", "info").upper(),
                    "logger": parsed.get("logger", "unknown"),
                    "message": parsed.get("event", line),
                    "raw": parsed,
                    "labels": labels,
                })
            except (json.JSONDecodeError, TypeError):
                logs.append({
                    "timestamp": datetime.fromtimestamp(int(ts) / 1_000_000_000).isoformat(),
                    "level": "INFO",
                    "logger": labels.get("logger", "unknown"),
                    "message": line,
                    "raw": line,
                    "labels": labels,
                })
    
    return {
        "logs": logs,
        "total": len(logs),
        "status": data.get("status", "success"),
    }

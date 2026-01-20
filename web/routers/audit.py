from fastapi import APIRouter, Query, Depends
from typing import Optional, List
from datetime import datetime, timedelta
from ..database import fetchall, fetchone, execute

from ..dependencies import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


async def ensure_audit_table():
    await execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT NOW(),
            admin_id BIGINT NOT NULL,
            admin_name VARCHAR(100),
            action VARCHAR(50) NOT NULL,
            target_type VARCHAR(50),
            target_id VARCHAR(100),
            details JSONB DEFAULT '{}',
            ip_address VARCHAR(45)
        )
    ''')
    await execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC)
    ''')
    await execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)
    ''')


async def log_action(
    admin_id: int,
    admin_name: str,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None
):
    await ensure_audit_table()
    import json
    await execute('''
        INSERT INTO audit_logs (admin_id, admin_name, action, target_type, target_id, details, ip_address)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
    ''', admin_id, admin_name, action, target_type, target_id, 
        json.dumps(details) if details else '{}', ip_address)


@router.get("/")
async def get_audit_logs(
    action: Optional[str] = None,
    admin_id: Optional[int] = None,
    target_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    await ensure_audit_table()
    
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    param_idx = 1
    
    if action:
        query += f" AND action = ${param_idx}"
        params.append(action)
        param_idx += 1
    
    if admin_id:
        query += f" AND admin_id = ${param_idx}"
        params.append(admin_id)
        param_idx += 1
    
    if target_type:
        query += f" AND target_type = ${param_idx}"
        params.append(target_type)
        param_idx += 1
    
    if from_date:
        query += f" AND timestamp >= ${param_idx}"
        params.append(from_date)
        param_idx += 1
    
    if to_date:
        query += f" AND timestamp <= ${param_idx}"
        params.append(to_date)
        param_idx += 1
    
    query += f" ORDER BY timestamp DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([min(limit, 200), offset])
    
    rows = await fetchall(query, tuple(params))
    
    logs = []
    for row in rows:
        logs.append({
            "id": row["id"],
            "created_at": row["timestamp"].isoformat() if row["timestamp"] else None,
            "admin_id": row["admin_id"],
            "admin_name": row["admin_name"],
            "action": row["action"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "details": row["details"],
            "ip_address": row["ip_address"]
        })
    
    actions = await fetchall("SELECT DISTINCT action FROM audit_logs ORDER BY action")
    
    return {"logs": logs, "count": len(logs), "actions": [a["action"] for a in actions]}


@router.get("/actions")
async def get_action_types():
    return {
        "actions": [
            {"id": "user_update", "name": "Cập nhật người dùng"},
            {"id": "seeds_adjust", "name": "Điều chỉnh Hạt"},
            {"id": "config_change", "name": "Thay đổi cấu hình"},
            {"id": "module_toggle", "name": "Bật/tắt module"},
            {"id": "user_ban", "name": "Cấm người dùng"},
            {"id": "user_unban", "name": "Bỏ cấm người dùng"},
            {"id": "data_export", "name": "Xuất dữ liệu"},
        ]
    }


@router.get("/stats")
async def get_audit_stats():
    await ensure_audit_table()
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    
    today_count = await fetchone('''
        SELECT COUNT(*) FROM audit_logs WHERE timestamp >= $1
    ''', today)
    
    week_count = await fetchone('''
        SELECT COUNT(*) FROM audit_logs WHERE timestamp >= $1
    ''', week_ago)
    
    by_action = await fetchall('''
        SELECT action, COUNT(*) as count
        FROM audit_logs
        WHERE timestamp >= $1
        GROUP BY action
        ORDER BY count DESC
        LIMIT 10
    ''', week_ago)
    
    return {
        "today": today_count[0] if today_count else 0,
        "this_week": week_count[0] if week_count else 0,
        "by_action": [{"action": r[0], "count": r[1]} for r in by_action]
    }

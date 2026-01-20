"""
BHNBot Admin Panel - Statistics Router

Endpoints for economy and game statistics.
Rewritten for PostgreSQL compatibility.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, List, Optional
import math
from datetime import datetime, timedelta

from ..database import fetchall, fetchone

from ..dependencies import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


def calculate_gini(balances: List[int]) -> float:
    """Calculate Gini coefficient for wealth distribution.
    
    0 = perfect equality, 1 = perfect inequality
    """
    if not balances or len(balances) < 2:
        return 0.0
    
    n = len(balances)
    sorted_balances = sorted(balances)
    
    # Gini formula: G = (2 * Σ(i * x_i)) / (n * Σx_i) - (n+1)/n
    numerator = sum((i + 1) * x for i, x in enumerate(sorted_balances))
    denominator = n * sum(sorted_balances)
    
    if denominator == 0:
        return 0.0
    
    gini = (2 * numerator) / denominator - (n + 1) / n
    return round(max(0, min(1, gini)), 4)


@router.get("/economy")
async def get_economy_stats() -> Dict[str, Any]:
    """Get economy statistics."""
    # Postgres: Use COALESCE to handle NULL sums if table is empty
    total_data = await fetchone("SELECT COALESCE(SUM(seeds), 0)::BIGINT as total, COUNT(*) as count FROM users")
    
    # Get all balances for Gini calculation
    all_balances = await fetchall("SELECT seeds FROM users WHERE seeds > 0")
    balances = [row["seeds"] for row in all_balances]
    
    # Calculate median
    sorted_balances = sorted(balances)
    median = sorted_balances[len(sorted_balances) // 2] if sorted_balances else 0
    
    # Get top 10
    top_10 = await fetchall(
        "SELECT user_id, username, seeds FROM users ORDER BY seeds DESC LIMIT 10"
    )
    
    return {
        "total_seeds": total_data["total"] if total_data else 0,
        "total_users": total_data["count"] if total_data else 0,
        "top_10": top_10,
        "gini_index": calculate_gini(balances),
        "median_balance": median,
        "active_users": len(balances)
    }


@router.get("/modules")
async def get_module_stats() -> Dict[str, Any]:
    """Get statistics for each game module."""
    
    # Fishing stats
    fishing_catches = await fetchone(
        "SELECT COALESCE(SUM(quantity), 0)::BIGINT as total FROM fish_collection"
    )
    fishing_users = await fetchone(
        "SELECT COUNT(DISTINCT user_id) as count FROM fish_collection"
    )
    
    # Bầu Cua stats from user_stats
    baucua_stats = await fetchone(
        """SELECT 
            COALESCE(SUM(CASE WHEN stat_key = 'baucua_played' THEN value END), 0)::BIGINT as games,
            COALESCE(SUM(CASE WHEN stat_key = 'baucua_total_won' THEN value END), 0)::BIGINT as won,
            COALESCE(SUM(CASE WHEN stat_key = 'baucua_total_lost' THEN value END), 0)::BIGINT as lost
        FROM user_stats WHERE game_id = 'baucua'"""
    )
    
    # Nối Từ stats
    noitu_stats = await fetchone(
        """SELECT 
            COALESCE(SUM(CASE WHEN stat_key = 'correct_words' THEN value END), 0)::BIGINT as words,
            COUNT(DISTINCT user_id) as users
        FROM user_stats WHERE game_id = 'noitu'"""
    )
    
    # Inventory stats
    inventory_stats = await fetchone(
        "SELECT COUNT(*) as items, COALESCE(SUM(quantity), 0)::BIGINT as total FROM inventory"
    )
    
    # Helper to check for None/Empty logic results
    def safe_get(data, key, default=0):
        return data[key] if data and data.get(key) is not None else default

    return {
        "fishing": {
            "total_catches": safe_get(fishing_catches, "total"),
            "active_users": safe_get(fishing_users, "count"),
        },
        "baucua": {
            "total_games": safe_get(baucua_stats, "games"),
            "total_won": safe_get(baucua_stats, "won"),
            "total_lost": safe_get(baucua_stats, "lost"),
            "house_profit": (safe_get(baucua_stats, "lost") - safe_get(baucua_stats, "won")),
        },
        "noitu": {
            "total_words": safe_get(noitu_stats, "words"),
            "active_users": safe_get(noitu_stats, "users"),
        },
        "inventory": {
            "unique_items": safe_get(inventory_stats, "items"),
            "total_quantity": safe_get(inventory_stats, "total"),
        }
    }


@router.get("/distribution")
async def get_wealth_distribution() -> Dict[str, Any]:
    """Get wealth distribution for pie chart."""
    # Group users by wealth brackets (Adjusted for 1.5M economy)
    brackets = await fetchall(
        """SELECT 
            CASE 
                WHEN seeds < 1000 THEN 'Nghèo (<1K)'
                WHEN seeds < 10000 THEN 'Bình dân (1K-10K)'
                WHEN seeds < 50000 THEN 'Trung lưu (10K-50K)'
                WHEN seeds < 100000 THEN 'Giàu (50K-100K)'
                ELSE 'Đại gia (>100K)'
            END as bracket,
            COUNT(*) as count,
            COALESCE(SUM(seeds), 0)::BIGINT as total_seeds
        FROM users
        GROUP BY bracket
        ORDER BY MIN(seeds)"""
    )
    
    return {
        "brackets": brackets,
        "chart_data": [
            {
                "name": b["bracket"], 
                "value": b["total_seeds"], 
                "count": b["count"]
            }
            for b in brackets
        ]
    }


@router.get("/advanced")
async def get_advanced_stats() -> Dict[str, Any]:
    """Get advanced economy analytics."""
    
    # 1. Active Circulation Supply (Users active in last 7 days)
    # Using Postgres native logic: NOW() - INTERVAL '7 days'
    active_supply_data = await fetchone(
        """SELECT COALESCE(SUM(seeds), 0)::BIGINT as total FROM users 
           WHERE last_daily >= NOW() - INTERVAL '7 days'
           OR last_chat_reward >= NOW() - INTERVAL '7 days'"""
    )
    active_supply = active_supply_data['total'] if active_supply_data else 0

    # Total Supply
    total_supply_data = await fetchone("SELECT COALESCE(SUM(seeds), 0)::BIGINT as total FROM users")
    total_supply = total_supply_data['total'] if total_supply_data else 1
    if total_supply == 0: total_supply = 1 # Avoid div by zero
    
    # 2. Whale Alert (> 2% of Total Supply) - Adjusted to show more top players
    # FIX: AsyncPG returns Decimal for SUM(), must cast for float math
    whale_threshold = float(total_supply) * 0.02
    whales = await fetchall(
        "SELECT user_id, username, seeds FROM users WHERE seeds > $1 ORDER BY seeds DESC LIMIT 5", 
        (whale_threshold,)
    )
    
    # 3. Sink/Faucet Breakdown
    # Ensure COALESCE for sums to avoid NoneType errors
    stats = await fetchall(
        """SELECT stat_key, COALESCE(SUM(value), 0)::BIGINT as val FROM user_stats 
           WHERE stat_key IN (
             'baucua_total_won', 'baucua_total_lost', 
             'total_money_earned', 
             'worms_used', 'rods_repaired', 'rod_upgrades'
           )
           GROUP BY stat_key"""
    )
    
    s_map = {row['stat_key']: row['val'] for row in stats}
    
    # Constants (estimates)
    WORM_COST = 3
    REPAIR_COST = 500
    UPGRADE_COST = 5000
    
    faucet_breakdown = [
        {"name": "Bầu Cua Won", "value": s_map.get('baucua_total_won', 0)},
        {"name": "Fishing/Other Earned", "value": s_map.get('total_money_earned', 0)},
    ]
    
    sink_breakdown = [
        {"name": "Bầu Cua Lost", "value": s_map.get('baucua_total_lost', 0)},
        {"name": "Worms", "value": s_map.get('worms_used', 0) * WORM_COST},
        {"name": "Repairs", "value": s_map.get('rods_repaired', 0) * REPAIR_COST},
        {"name": "Upgrades", "value": s_map.get('rod_upgrades', 0) * UPGRADE_COST},
    ]
    
    return {
        "active_circulation": active_supply,
        "whales": whales,
        "flow": {
            "in": faucet_breakdown,
            "out": sink_breakdown
        }
    }


@router.get("/cashflow")
async def get_cashflow_stats(days: int = 30) -> Dict[str, Any]:
    """Get cash flow statistics grouped by category and reason."""
    
    query = """
        SELECT 
            category,
            reason,
            COALESCE(SUM(amount), 0)::BIGINT as net_amount,
            COUNT(*) as count,
            COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0)::BIGINT as total_in,
            COALESCE(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0)::BIGINT as total_out
        FROM transaction_logs
        WHERE created_at >= NOW() - make_interval(days := $1)
        GROUP BY category, reason
        ORDER BY category, net_amount DESC
    """
    
    rows = await fetchall(query, (days,))
    
    categories = {}
    summary = {"total_in": 0, "total_out": 0, "net": 0, "transaction_count": 0}
    
    for row in rows:
        cat = row["category"] or "unknown"
        reason = row["reason"] or "unknown"
        
        summary["total_in"] += row["total_in"]
        summary["total_out"] += row["total_out"]
        summary["net"] += row["net_amount"]
        summary["transaction_count"] += row["count"]
        
        if cat not in categories:
            categories[cat] = {
                "net": 0,
                "in": 0,
                "out": 0,
                "count": 0,
                "reasons": []
            }
            
        c = categories[cat]
        c["net"] += row["net_amount"]
        c["in"] += row["total_in"]
        c["out"] += row["total_out"]
        c["count"] += row["count"]
        
        c["reasons"].append({
            "reason": reason,
            "net": row["net_amount"],
            "in": row["total_in"],
            "out": row["total_out"],
            "count": row["count"]
        })
        
    return {
        "period": f"Last {days} days",
        "summary": summary,
        "categories": categories
    }


@router.get("/economy/detailed")
async def get_detailed_economy_stats() -> Dict[str, Any]:
    """Get detailed economy breakdown by source/cog."""
    
    by_category = await fetchall("""
        SELECT 
            category,
            COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0)::BIGINT as earned,
            COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0)::BIGINT as spent,
            COUNT(*) as transactions
        FROM transaction_logs
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY category
        ORDER BY earned DESC
    """)
    
    by_day = await fetchall("""
        SELECT 
            DATE(created_at) as date,
            COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0)::BIGINT as earned,
            COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0)::BIGINT as spent
        FROM transaction_logs
        WHERE created_at >= NOW() - INTERVAL '14 days'
        GROUP BY DATE(created_at)
        ORDER BY date
    """)
    
    top_earners = await fetchall("""
        SELECT user_id, COALESCE(SUM(amount), 0)::BIGINT as total_earned
        FROM transaction_logs
        WHERE amount > 0 AND created_at >= NOW() - INTERVAL '7 days'
        GROUP BY user_id
        ORDER BY total_earned DESC
        LIMIT 10
    """)
    
    top_spenders = await fetchall("""
        SELECT user_id, COALESCE(SUM(ABS(amount)), 0)::BIGINT as total_spent
        FROM transaction_logs
        WHERE amount < 0 AND created_at >= NOW() - INTERVAL '7 days'
        GROUP BY user_id
        ORDER BY total_spent DESC
        LIMIT 10
    """)
    
    return {
        "by_category": by_category,
        "by_day": [{"date": str(r["date"]), "earned": r["earned"], "spent": r["spent"]} for r in by_day],
        "top_earners": top_earners,
        "top_spenders": top_spenders
    }


@router.get("/inventory")
async def get_inventory_stats() -> Dict[str, Any]:
    """Get inventory and item statistics."""
    
    item_counts = await fetchall("""
        SELECT item_id, COALESCE(SUM(quantity), 0)::BIGINT as total_quantity, COUNT(DISTINCT user_id) as owners
        FROM inventory
        GROUP BY item_id
        ORDER BY total_quantity DESC
        LIMIT 20
    """)
    
    total_items = await fetchone("""
        SELECT COALESCE(SUM(quantity), 0)::BIGINT as total, COUNT(DISTINCT item_id) as unique_items
        FROM inventory
    """)
    
    fish_stats = await fetchall("""
        SELECT fish_id, COALESCE(SUM(quantity), 0)::BIGINT as total, COUNT(DISTINCT user_id) as catchers
        FROM fish_collection
        GROUP BY fish_id
        ORDER BY total DESC
        LIMIT 20
    """)
    
    rarest_fish = await fetchall("""
        SELECT fish_id, COALESCE(SUM(quantity), 0)::BIGINT as total
        FROM fish_collection
        GROUP BY fish_id
        ORDER BY total ASC
        LIMIT 10
    """)
    
    return {
        "items": {
            "total_quantity": total_items["total"] if total_items else 0,
            "unique_items": total_items["unique_items"] if total_items else 0,
            "top_items": item_counts
        },
        "fish": {
            "most_caught": fish_stats,
            "rarest": rarest_fish
        }
    }


@router.get("/commands")
async def get_command_stats(
    days: int = Query(default=7, ge=1, le=90),
    cog: Optional[str] = None,
    guild_id: Optional[int] = None
) -> Dict[str, Any]:
    """Get command usage statistics."""
    
    # Base filters
    filters = ["used_at >= NOW() - make_interval(days := $1)"]
    params: List[Any] = [days]
    param_idx = 2
    
    if cog:
        filters.append(f"cog_name = ${param_idx}")
        params.append(cog)
        param_idx += 1
    
    if guild_id:
        filters.append(f"guild_id = ${param_idx}")
        params.append(guild_id)
        param_idx += 1
    
    where_clause = " AND ".join(filters)
    
    # Total commands
    total = await fetchone(
        f"SELECT COUNT(*) as count FROM command_usage WHERE {where_clause}",
        tuple(params)
    )
    
    # Commands by name (top 20)
    by_command = await fetchall(
        f"""SELECT command_name, COUNT(*) as count, 
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count
        FROM command_usage WHERE {where_clause}
        GROUP BY command_name ORDER BY count DESC LIMIT 20""",
        tuple(params)
    )
    
    # Commands by cog
    by_cog = await fetchall(
        f"""SELECT COALESCE(cog_name, 'Unknown') as cog_name, COUNT(*) as count
        FROM command_usage WHERE {where_clause}
        GROUP BY cog_name ORDER BY count DESC""",
        tuple(params)
    )
    
    # Commands by hour (for chart)
    by_hour = await fetchall(
        f"""SELECT EXTRACT(HOUR FROM used_at)::INT as hour, COUNT(*) as count
        FROM command_usage WHERE {where_clause}
        GROUP BY hour ORDER BY hour""",
        tuple(params)
    )
    
    # Commands by day (for chart)
    by_day = await fetchall(
        f"""SELECT DATE(used_at) as date, COUNT(*) as count
        FROM command_usage WHERE {where_clause}
        GROUP BY date ORDER BY date""",
        tuple(params)
    )
    
    # Error breakdown
    errors = await fetchall(
        f"""SELECT error_type, COUNT(*) as count
        FROM command_usage WHERE {where_clause} AND success = FALSE AND error_type IS NOT NULL
        GROUP BY error_type ORDER BY count DESC LIMIT 10""",
        tuple(params)
    )
    
    # Top users
    top_users = await fetchall(
        f"""SELECT user_id, COUNT(*) as count
        FROM command_usage WHERE {where_clause}
        GROUP BY user_id ORDER BY count DESC LIMIT 10""",
        tuple(params)
    )
    
    return {
        "period": f"Last {days} days",
        "total_commands": total["count"] if total else 0,
        "by_command": by_command,
        "by_cog": by_cog,
        "by_hour": by_hour,
        "by_day": [{"date": str(r["date"]), "count": r["count"]} for r in by_day],
        "errors": errors,
        "top_users": top_users,
        "success_rate": round(
            sum(c["success_count"] for c in by_command) / max(1, total["count"] if total else 1) * 100, 2
        )
    }


@router.get("/commands/trending")
async def get_trending_commands() -> Dict[str, Any]:
    """Get trending commands (comparing last 24h vs previous 24h)."""
    
    # Last 24 hours
    recent = await fetchall(
        """SELECT command_name, COUNT(*) as count
        FROM command_usage 
        WHERE used_at >= NOW() - INTERVAL '24 hours'
        GROUP BY command_name"""
    )
    
    # Previous 24 hours
    previous = await fetchall(
        """SELECT command_name, COUNT(*) as count
        FROM command_usage 
        WHERE used_at >= NOW() - INTERVAL '48 hours' 
        AND used_at < NOW() - INTERVAL '24 hours'
        GROUP BY command_name"""
    )
    
    recent_map = {r["command_name"]: r["count"] for r in recent}
    previous_map = {r["command_name"]: r["count"] for r in previous}
    
    all_commands = set(recent_map.keys()) | set(previous_map.keys())
    
    trends = []
    for cmd in all_commands:
        r_count = recent_map.get(cmd, 0)
        p_count = previous_map.get(cmd, 0)
        
        if p_count > 0:
            change = ((r_count - p_count) / p_count) * 100
        elif r_count > 0:
            change = 100.0  # New command
        else:
            change = 0.0
            
        trends.append({
            "command": cmd,
            "recent": r_count,
            "previous": p_count,
            "change_percent": round(change, 1)
        })
    
    # Sort by change (biggest gainers first)
    trends.sort(key=lambda x: x["change_percent"], reverse=True)
    
    return {
        "trending_up": trends[:10],
        "trending_down": sorted(trends, key=lambda x: x["change_percent"])[:10]
    }


@router.get("/activity")
async def get_user_activity_stats(days: int = Query(default=7, ge=1, le=90)) -> Dict[str, Any]:
    """Get user activity statistics (joins, leaves, etc)."""
    
    # Joins and leaves by day
    activity_by_day = await fetchall(
        """SELECT DATE(created_at) as date, event_type, COUNT(*) as count
        FROM user_activity 
        WHERE created_at >= NOW() - make_interval(days := $1)
        GROUP BY date, event_type
        ORDER BY date""",
        (days,)
    )
    
    # Summary
    summary = await fetchone(
        """SELECT 
            SUM(CASE WHEN event_type = 'join' THEN 1 ELSE 0 END) as joins,
            SUM(CASE WHEN event_type = 'leave' THEN 1 ELSE 0 END) as leaves
        FROM user_activity 
        WHERE created_at >= NOW() - make_interval(days := $1)""",
        (days,)
    )
    
    # Format for chart
    dates_data: Dict[str, Dict[str, int]] = {}
    for row in activity_by_day:
        date_str = str(row["date"])
        if date_str not in dates_data:
            dates_data[date_str] = {"join": 0, "leave": 0}
        dates_data[date_str][row["event_type"]] = row["count"]
    
    chart_data = [
        {"date": d, "joins": v["join"], "leaves": v["leave"]}
        for d, v in sorted(dates_data.items())
    ]
    
    return {
        "period": f"Last {days} days",
        "summary": {
            "total_joins": summary["joins"] if summary else 0,
            "total_leaves": summary["leaves"] if summary else 0,
            "net_change": (summary["joins"] or 0) - (summary["leaves"] or 0) if summary else 0
        },
        "by_day": chart_data
    }


@router.get("/cogs")
async def get_cog_list() -> List[str]:
    """Get list of all cogs that have recorded commands."""
    result = await fetchall(
        "SELECT DISTINCT cog_name FROM command_usage WHERE cog_name IS NOT NULL ORDER BY cog_name"
    )
    return [r["cog_name"] for r in result]


@router.get("/export")
async def export_dashboard_data() -> Any:
    """Export all dashboard data to Excel."""
    try:
        import pandas as pd
        from io import BytesIO
        from fastapi.responses import StreamingResponse
    except ImportError:
        raise HTTPException(status_code=500, detail="Libraries pandas/openpyxl not installed.")

    # Fetch Data
    economy = await get_economy_stats()
    modules = await get_module_stats()
    dist = await get_wealth_distribution()
    
    top_100 = await fetchall(
        "SELECT user_id, username, seeds FROM users ORDER BY seeds DESC LIMIT 100"
    )
    
    inventory = await fetchall(
        """SELECT item_id, COALESCE(SUM(quantity), 0) as total_qty, COUNT(DISTINCT user_id) as owners 
           FROM inventory GROUP BY item_id ORDER BY total_qty DESC"""
    )

    # Create Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        
        # Sheet 1: Overview
        overview_data = {
            "Metric": ["Total Hạt", "Total Users", "Active Users", "Gini Index", "Median Balance"],
            "Value": [
                economy['total_seeds'], 
                economy['total_users'], 
                economy['active_users'], 
                economy['gini_index'], 
                economy['median_balance']
            ]
        }
        pd.DataFrame(overview_data).to_excel(writer, sheet_name='Overview', index=False)
        
        # Sheet 2: Top 100 Richest
        if top_100:
            pd.DataFrame(top_100).to_excel(writer, sheet_name='Top 100 Richest', index=False)
            
        # Sheet 3: Game Modules
        module_rows = []
        for mod, stats in modules.items():
            for k, v in stats.items():
                module_rows.append({"Module": mod.upper(), "Metric": k, "Value": v})
        pd.DataFrame(module_rows).to_excel(writer, sheet_name='Game Modules', index=False)
        
        # Sheet 4: Wealth Distribution
        if dist['brackets']:
            pd.DataFrame(dist['brackets']).to_excel(writer, sheet_name='Wealth Distribution', index=False)
            
        # Sheet 5: Inventory
        if inventory:
            pd.DataFrame(inventory).to_excel(writer, sheet_name='Inventory Summary', index=False)

    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="bhn_stats_export.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

"""
BHNBot Admin Panel - Statistics Router

Endpoints for economy and game statistics.
Rewritten for PostgreSQL compatibility.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import math
from datetime import datetime, timedelta

from ..database import fetchall, fetchone

router = APIRouter()


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
    
    # Postgres specific: Use make_interval for clean integer handling
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
        
        # summary updates
        summary["total_in"] += row["total_in"]
        summary["total_out"] += row["total_out"]
        summary["net"] += row["net_amount"]
        summary["transaction_count"] += row["count"]
        
        # category init
        if cat not in categories:
            categories[cat] = {
                "net": 0,
                "in": 0,
                "out": 0,
                "count": 0,
                "reasons": []
            }
            
        # category updates
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

"""
BHNBot Admin Panel - Statistics Router

Endpoints for economy and game statistics.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import math

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
    """Get economy statistics.
    
    Returns:
        - total_seeds: Total seeds in circulation
        - total_users: Number of users
        - top_10: Top 10 richest users
        - gini_index: Wealth inequality measure
        - median_balance: Median user balance
    """
    # Get total seeds and user count
    total = await fetchone("SELECT SUM(seeds) as total, COUNT(*) as count FROM users")
    
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
        "total_seeds": total["total"] or 0,
        "total_users": total["count"] or 0,
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
        "SELECT COALESCE(SUM(quantity), 0) as total FROM fish_collection"
    )
    fishing_users = await fetchone(
        "SELECT COUNT(DISTINCT user_id) as count FROM fish_collection"
    )
    
    # Bầu Cua stats from user_stats
    baucua_stats = await fetchone(
        """SELECT 
            COALESCE(SUM(CASE WHEN stat_key = 'baucua_played' THEN value END), 0) as games,
            COALESCE(SUM(CASE WHEN stat_key = 'baucua_total_won' THEN value END), 0) as won,
            COALESCE(SUM(CASE WHEN stat_key = 'baucua_total_lost' THEN value END), 0) as lost
        FROM user_stats WHERE game_id = 'baucua'"""
    )
    
    # Nối Từ stats
    noitu_stats = await fetchone(
        """SELECT 
            COALESCE(SUM(CASE WHEN stat_key = 'correct_words' THEN value END), 0) as words,
            COUNT(DISTINCT user_id) as users
        FROM user_stats WHERE game_id = 'noitu'"""
    )
    
    # Inventory stats
    inventory_stats = await fetchone(
        "SELECT COUNT(*) as items, SUM(quantity) as total FROM inventory"
    )
    
    return {
        "fishing": {
            "total_catches": fishing_catches["total"] if fishing_catches else 0,
            "active_users": fishing_users["count"] if fishing_users else 0,
        },
        "baucua": {
            "total_games": baucua_stats["games"] if baucua_stats else 0,
            "total_won": baucua_stats["won"] if baucua_stats else 0,
            "total_lost": baucua_stats["lost"] if baucua_stats else 0,
            "house_profit": (baucua_stats["lost"] - baucua_stats["won"]) if baucua_stats else 0,
        },
        "noitu": {
            "total_words": noitu_stats["words"] if noitu_stats else 0,
            "active_users": noitu_stats["users"] if noitu_stats else 0,
        },
        "inventory": {
            "unique_items": inventory_stats["items"] if inventory_stats else 0,
            "total_quantity": inventory_stats["total"] if inventory_stats else 0,
        }
    }


@router.get("/distribution")
async def get_wealth_distribution() -> Dict[str, Any]:
    """Get wealth distribution for pie chart."""
    # Group users by wealth brackets
    brackets = await fetchall(
        """SELECT 
            CASE 
                WHEN seeds < 100 THEN 'Nghèo (<100)'
                WHEN seeds < 500 THEN 'Bình dân (100-500)'
                WHEN seeds < 2000 THEN 'Trung lưu (500-2K)'
                WHEN seeds < 10000 THEN 'Giàu (2K-10K)'
                ELSE 'Đại gia (>10K)'
            END as bracket,
            COUNT(*) as count,
            SUM(seeds) as total_seeds
        FROM users
        GROUP BY bracket
        ORDER BY MIN(seeds)"""
    )
    
    return {
        "brackets": brackets,
        "chart_data": [
            {"name": b["bracket"], "value": b["total_seeds"], "count": b["count"]}
            for b in brackets
        ]
    }

@router.get("/advanced")
async def get_advanced_stats() -> Dict[str, Any]:
    """Get advanced economy analytics."""
    
    # 1. Active Circulation Supply (Users active in last 7 days)
    active_supply_data = await fetchone(
        """SELECT SUM(seeds) as total FROM users 
           WHERE last_daily >= datetime('now', '-7 days') 
           OR last_chat_reward >= datetime('now', '-7 days')"""
    )
    active_supply = active_supply_data['total'] or 0
    
    # Total Supply for Whale calc
    total_supply_data = await fetchone("SELECT SUM(seeds) as total FROM users")
    total_supply = total_supply_data['total'] or 1
    
    # 2. Whale Alert (> 5% of Total Supply)
    whale_threshold = total_supply * 0.05
    whales = await fetchall(
        "SELECT user_id, username, seeds FROM users WHERE seeds > ?", (whale_threshold,)
    )
    
    # 3. Sink/Faucet Breakdown (Heuristic Estimate)
    # We aggregate ALL-TIME stats from user_stats
    stats = await fetchall(
        """SELECT stat_key, SUM(value) as val FROM user_stats 
           WHERE stat_key IN (
             'baucua_total_won', 'baucua_total_lost', 
             'total_money_earned', 
             'worms_used', 'rods_repaired', 'rod_upgrades'
           )
           GROUP BY stat_key"""
    )
    
    s_map = {row['stat_key']: row['val'] for row in stats}
    
    # Config-based estimates (Hardcoded here for estimation, ideally sync with config)
    WORM_COST = 3
    REPAIR_COST = 500 # Avg
    UPGRADE_COST = 5000 # Avg
    
    faucet_breakdown = [
        {"name": "Bầu Cua Won", "value": s_map.get('baucua_total_won', 0)},
        {"name": "Fishing/Other Earned", "value": s_map.get('total_money_earned', 0)},
        # Daily is NOT tracked in user_stats currently, big missing piece.
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


@router.get("/export")
async def export_dashboard_data() -> Any:
    """Export all dashboard data to Excel."""
    try:
        import pandas as pd
        from io import BytesIO
        from fastapi.responses import StreamingResponse
    except ImportError:
        raise HTTPException(status_code=500, detail="Libraries pandas/openpyxl not installed.")

    # 1. Fetch Data
    
    # Overview (Re-using logic, ideally should refactor to shared service helper but calling directly here for speed)
    economy = await get_economy_stats()
    modules = await get_module_stats()
    dist = await get_wealth_distribution()
    
    # Top 100 Richest
    top_100 = await fetchall(
        "SELECT user_id, username, seeds FROM users ORDER BY seeds DESC LIMIT 100"
    )
    
    # Inventory Summary
    inventory = await fetchall(
        """SELECT item_id, SUM(quantity) as total_qty, COUNT(DISTINCT user_id) as owners 
           FROM inventory GROUP BY item_id ORDER BY total_qty DESC"""
    )

    # 2. Create Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        
        # Sheet 1: Overview
        overview_data = {
            "Metric": ["Total Seeds", "Total Users", "Active Users", "Gini Index", "Median Balance"],
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

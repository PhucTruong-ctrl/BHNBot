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
            COALESCE(SUM(CASE WHEN stat_key = 'games_played' THEN value END), 0) as games,
            COALESCE(SUM(CASE WHEN stat_key = 'total_won' THEN value END), 0) as won,
            COALESCE(SUM(CASE WHEN stat_key = 'total_lost' THEN value END), 0) as lost
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

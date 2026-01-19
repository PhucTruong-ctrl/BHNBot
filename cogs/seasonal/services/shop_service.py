"""Shop service for seasonal event item purchases.

Handles buying items from event shop using event currency.
Each event has its own shop defined in data/events/{event_type}.json.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .database import execute_query, execute_write
from .participation_service import get_currency, spend_currency

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ShopItem:
    """Represents an item in the event shop."""

    key: str
    name: str
    description: str
    price: int
    emoji: str
    category: str  # "consumable", "collectible", "title", "cosmetic"
    stock: int | None  # None = unlimited
    limit_per_user: int | None  # None = unlimited
    requires_title: str | None  # Required title key to purchase


@dataclass
class PurchaseResult:
    """Result of a purchase attempt."""

    success: bool
    message: str
    item: ShopItem | None = None
    new_balance: int = 0


def _load_shop_items(event_type: str) -> list[ShopItem]:
    """Load shop items from event JSON file.

    Args:
        event_type: The event type (e.g., "spring", "halloween").

    Returns:
        List of ShopItem objects.
    """
    # Map event IDs to base types
    base_type = event_type.split("_")[0]  # "spring_2026" -> "spring"

    json_path = Path(__file__).parent.parent.parent.parent / "data" / "events" / f"{base_type}.json"

    if not json_path.exists():
        logger.warning(f"Shop file not found: {json_path}")
        return []

    try:
        from core.data_cache import data_cache
        cache_key = f"event_{base_type}"
        data = data_cache.get(cache_key)
        if not data:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)

        shop_data = data.get("shop", [])
        items = []
        for item_data in shop_data:
            items.append(
                ShopItem(
                    key=item_data["key"],
                    name=item_data["name"],
                    description=item_data.get("description", ""),
                    price=item_data["price"],
                    emoji=item_data.get("emoji", "🛒"),
                    category=item_data.get("category", "consumable"),
                    stock=item_data.get("stock"),
                    limit_per_user=item_data.get("limit_per_user"),
                    requires_title=item_data.get("requires_title"),
                )
            )
        return items
    except Exception as e:
        logger.exception(f"Failed to load shop items: {e}")
        return []


async def get_shop_items(event_id: str) -> list[ShopItem]:
    """Get all shop items for an event.

    Args:
        event_id: The event ID (e.g., "spring_2026").

    Returns:
        List of ShopItem objects.
    """
    return _load_shop_items(event_id)


async def get_user_purchase_count(
    guild_id: int, user_id: int, event_id: str, item_key: str
) -> int:
    """Get how many times a user has purchased an item.

    Args:
        guild_id: The guild ID.
        user_id: The user ID.
        event_id: The event ID.
        item_key: The item key.

    Returns:
        Number of times the user has purchased the item.
    """
    rows = await execute_query(
        """
        SELECT COALESCE(SUM(quantity), 0) as total
        FROM event_shop_purchases
        WHERE guild_id = $1 AND user_id = $2 AND event_id = $3 AND item_key = $4
        """,
        (guild_id, user_id, event_id, item_key),
    )
    return rows[0]["total"] if rows else 0


async def get_global_stock_remaining(
    guild_id: int, event_id: str, item_key: str, max_stock: int | None
) -> int | None:
    """Get remaining global stock for an item.

    Args:
        guild_id: The guild ID.
        event_id: The event ID.
        item_key: The item key.
        max_stock: Maximum stock, or None for unlimited.

    Returns:
        Remaining stock, or None for unlimited.
    """
    if max_stock is None:
        return None

    rows = await execute_query(
        """
        SELECT COALESCE(SUM(quantity), 0) as total
        FROM event_shop_purchases
        WHERE guild_id = $1 AND event_id = $2 AND item_key = $3
        """,
        (guild_id, event_id, item_key),
    )
    sold = rows[0]["total"] if rows else 0
    return max(0, max_stock - sold)


async def purchase_item(
    guild_id: int,
    user_id: int,
    event_id: str,
    item_key: str,
    quantity: int = 1,
    user_titles: list[str] | None = None,
) -> PurchaseResult:
    """Purchase an item from the event shop.

    Args:
        guild_id: The guild ID.
        user_id: The user ID.
        event_id: The event ID.
        item_key: The item key to purchase.
        quantity: Number of items to purchase.
        user_titles: List of title keys the user has unlocked.

    Returns:
        PurchaseResult with success status and message.
    """
    item = next((i for i in _load_shop_items(event_id) if i.key == item_key), None)

    if not item:
        return PurchaseResult(
            success=False,
            message="Không tìm thấy vật phẩm này trong cửa hàng.",
        )

    if item.requires_title:
        if not user_titles or item.requires_title not in user_titles:
            return PurchaseResult(
                success=False,
                message=f"Bạn cần có danh hiệu **{item.requires_title}** để mua vật phẩm này.",
            )

    if item.limit_per_user is not None:
        user_count = await get_user_purchase_count(guild_id, user_id, event_id, item_key)
        if user_count + quantity > item.limit_per_user:
            remaining = item.limit_per_user - user_count
            return PurchaseResult(
                success=False,
                message=f"Bạn chỉ có thể mua tối đa **{item.limit_per_user}** vật phẩm này. Còn lại: {remaining}.",
            )

    if item.stock is not None:
        remaining_stock = await get_global_stock_remaining(
            guild_id, event_id, item_key, item.stock
        )
        if remaining_stock is not None and remaining_stock < quantity:
            return PurchaseResult(
                success=False,
                message=f"Không đủ hàng! Chỉ còn **{remaining_stock}** vật phẩm.",
            )

    total_cost = item.price * quantity
    current_balance = await get_currency(guild_id, user_id, event_id)
    if current_balance < total_cost:
        return PurchaseResult(
            success=False,
            message=f"Không đủ tiền! Cần **{total_cost}** nhưng chỉ có **{current_balance}**.",
        )

    success = await spend_currency(guild_id, user_id, event_id, total_cost)
    if not success:
        return PurchaseResult(
            success=False,
            message="Lỗi khi thanh toán. Vui lòng thử lại.",
        )

    await execute_write(
        """
        INSERT INTO event_shop_purchases (guild_id, user_id, event_id, item_key, quantity, price_paid, purchased_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        (guild_id, user_id, event_id, item_key, quantity, total_cost, datetime.utcnow()),
    )

    new_balance = await get_currency(guild_id, user_id, event_id)

    logger.info(
        f"User {user_id} purchased {quantity}x {item_key} in guild {guild_id} "
        f"for event {event_id}. Cost: {total_cost}, New balance: {new_balance}"
    )

    return PurchaseResult(
        success=True,
        message=f"Đã mua thành công **{quantity}x {item.emoji} {item.name}**!",
        item=item,
        new_balance=new_balance,
    )


async def get_user_purchases(
    guild_id: int, user_id: int, event_id: str
) -> list[dict[str, Any]]:
    """Get all purchases made by a user for an event.

    Args:
        guild_id: The guild ID.
        user_id: The user ID.
        event_id: The event ID.

    Returns:
        List of purchase records.
    """
    rows = await execute_query(
        """
        SELECT item_key, SUM(quantity) as total_quantity, SUM(price_paid) as total_spent
        FROM event_shop_purchases
        WHERE guild_id = $1 AND user_id = $2 AND event_id = $3
        GROUP BY item_key
        ORDER BY total_quantity DESC
        """,
        (guild_id, user_id, event_id),
    )
    return [dict(row) for row in rows]


async def get_shop_stats(guild_id: int, event_id: str) -> dict[str, Any]:
    rows = await execute_query(
        """
        SELECT 
            COUNT(DISTINCT user_id) as unique_buyers,
            SUM(quantity) as total_items_sold,
            SUM(price_paid) as total_currency_spent
        FROM event_shop_purchases
        WHERE guild_id = $1 AND event_id = $2
        """,
        (guild_id, event_id),
    )

    if not rows:
        return {
            "unique_buyers": 0,
            "total_items_sold": 0,
            "total_currency_spent": 0,
        }

    return {
        "unique_buyers": rows[0]["unique_buyers"] or 0,
        "total_items_sold": rows[0]["total_items_sold"] or 0,
        "total_currency_spent": rows[0]["total_currency_spent"] or 0,
    }


async def get_purchase_history(
    guild_id: int, user_id: int, event_id: str, limit: int = 20
) -> list[dict[str, Any]]:
    rows = await execute_query(
        """
        SELECT item_key, quantity, price_paid, purchased_at
        FROM event_shop_purchases
        WHERE guild_id = $1 AND user_id = $2 AND event_id = $3
        ORDER BY purchased_at DESC
        LIMIT $4
        """,
        (guild_id, user_id, event_id, limit),
    )
    return [dict(row) for row in rows]

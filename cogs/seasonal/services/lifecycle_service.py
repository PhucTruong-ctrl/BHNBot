"""
Event Lifecycle Service - Handles event end detection, currency expiry, and notifications.

This service:
1. Runs a scheduler to check event end times every 30 minutes
2. Sends 24h and 1h warning notifications before event ends
3. Converts remaining currency to collectible items when event ends
4. Provides manual currency-to-Hạt exchange at 1:3 rate
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from discord.ext import tasks
import discord

from core.logging import get_logger
from core.database import db_manager as main_db
from cogs.seasonal.services.database import execute_query, execute_write

if TYPE_CHECKING:
    from discord.ext.commands import Bot

logger = get_logger("event_lifecycle")

SQLITE_LIFECYCLE_TABLES = """
CREATE TABLE IF NOT EXISTS event_notifications_sent (
    guild_id INTEGER,
    event_id TEXT,
    notification_type TEXT,
    sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, event_id, notification_type)
);
"""

POSTGRES_LEDGER_TABLE = """
CREATE TABLE IF NOT EXISTS event_conversion_ledger (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    user_id BIGINT,
    event_id TEXT,
    original_currency INTEGER,
    conversion_type TEXT,
    result_item_key TEXT,
    result_seeds INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversion_ledger_status 
ON event_conversion_ledger(status);

CREATE INDEX IF NOT EXISTS idx_conversion_ledger_user 
ON event_conversion_ledger(user_id, event_id);
"""

CONVERSION_RATE_TO_SEEDS = 3
COLLECTIBLE_ITEM_TYPE = "commemorative"


class EventLifecycleService:
    _instance: "EventLifecycleService | None" = None
    
    def __init__(self, bot: "Bot"):
        self.bot = bot
        self._initialized = False
    
    @classmethod
    def get_instance(cls, bot: "Bot | None" = None) -> "EventLifecycleService":
        if cls._instance is None:
            if bot is None:
                raise RuntimeError("EventLifecycleService not initialized - bot required")
            cls._instance = cls(bot)
        return cls._instance
    
    async def initialize(self) -> None:
        if self._initialized:
            return
        
        for statement in SQLITE_LIFECYCLE_TABLES.strip().split(";"):
            statement = statement.strip()
            if statement:
                try:
                    await execute_write(statement)
                except Exception as e:
                    logger.warning(f"SQLite lifecycle table creation warning: {e}")
        
        for statement in POSTGRES_LEDGER_TABLE.strip().split(";"):
            statement = statement.strip()
            if statement:
                try:
                    await main_db.execute(statement)
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"PostgreSQL ledger table creation warning: {e}")
        
        self._initialized = True
        logger.info("Event lifecycle service initialized")
    
    async def start_scheduler(self) -> None:
        await self.initialize()
        if not self.lifecycle_check_loop.is_running():
            self.lifecycle_check_loop.start()
            logger.info("Event lifecycle scheduler started")
    
    def stop_scheduler(self) -> None:
        if self.lifecycle_check_loop.is_running():
            self.lifecycle_check_loop.cancel()
            logger.info("Event lifecycle scheduler stopped")
    
    @tasks.loop(minutes=30)
    async def lifecycle_check_loop(self) -> None:
        try:
            await self._check_all_events()
        except Exception as e:
            logger.error(f"Error in lifecycle check loop: {e}")
    
    @lifecycle_check_loop.before_loop
    async def before_lifecycle_check(self) -> None:
        await self.bot.wait_until_ready()
    
    async def _check_all_events(self) -> None:
        active_events = await execute_query(
            "SELECT guild_id, event_id, ends_at, announcement_channel_id FROM active_events WHERE ends_at IS NOT NULL"
        )
        
        now = datetime.utcnow()
        
        for event in active_events:
            guild_id = event["guild_id"]
            event_id = event["event_id"]
            ends_at_str = event["ends_at"]
            channel_id = event.get("announcement_channel_id")
            
            try:
                ends_at = datetime.fromisoformat(ends_at_str.replace("Z", "+00:00").replace("+00:00", ""))
            except (ValueError, AttributeError):
                logger.warning(f"Invalid ends_at format for event {event_id}: {ends_at_str}")
                continue
            
            time_remaining = ends_at - now
            
            if time_remaining <= timedelta(hours=0):
                await self._handle_event_end(guild_id, event_id)
            elif time_remaining <= timedelta(hours=1):
                await self._send_warning_if_not_sent(guild_id, event_id, "1h_warning", channel_id, time_remaining)
            elif time_remaining <= timedelta(hours=24):
                await self._send_warning_if_not_sent(guild_id, event_id, "24h_warning", channel_id, time_remaining)
    
    async def _send_warning_if_not_sent(
        self, 
        guild_id: int, 
        event_id: str, 
        notification_type: str,
        channel_id: int | None,
        time_remaining: timedelta
    ) -> None:
        existing = await execute_query(
            "SELECT 1 FROM event_notifications_sent WHERE guild_id = ? AND event_id = ? AND notification_type = ?",
            (guild_id, event_id, notification_type)
        )
        
        if existing:
            return
        
        await execute_write(
            "INSERT INTO event_notifications_sent (guild_id, event_id, notification_type) VALUES (?, ?, ?)",
            (guild_id, event_id, notification_type)
        )
        
        if channel_id:
            await self._send_warning_notification(guild_id, event_id, channel_id, time_remaining)
    
    async def _send_warning_notification(
        self, 
        guild_id: int, 
        event_id: str, 
        channel_id: int,
        time_remaining: timedelta
    ) -> None:
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return
            
            hours = int(time_remaining.total_seconds() // 3600)
            minutes = int((time_remaining.total_seconds() % 3600) // 60)
            
            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes} phút"
            
            from cogs.seasonal.services.database import get_notification_role
            role_id = await get_notification_role(guild_id)
            role_mention = f"<@&{role_id}>" if role_id else ""
            
            embed = discord.Embed(
                title="⏰ Sự Kiện Sắp Kết Thúc!",
                description=(
                    f"**Sự kiện sẽ kết thúc trong {time_str}!**\n\n"
                    f"🎫 Hãy sử dụng currency sự kiện của bạn trước khi hết hạn!\n"
                    f"💡 Dùng `/event shop` để mua vật phẩm\n"
                    f"💰 Hoặc `/event convert` để đổi ra Hạt (tỷ lệ 1:3)"
                ),
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"Event: {event_id}")
            
            await channel.send(content=role_mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
            logger.info(f"Sent {time_remaining} warning for event {event_id} in guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Failed to send warning notification: {e}")
    
    async def _handle_event_end(self, guild_id: int, event_id: str) -> None:
        already_converted = await execute_query(
            "SELECT 1 FROM event_notifications_sent WHERE guild_id = ? AND event_id = ? AND notification_type = 'event_ended'",
            (guild_id, event_id)
        )
        
        if already_converted:
            return
        
        logger.info(f"Processing event end for {event_id} in guild {guild_id}")
        
        participants = await execute_query(
            "SELECT user_id, currency FROM event_participation WHERE guild_id = ? AND event_id = ? AND currency > 0",
            (guild_id, event_id)
        )
        
        event_info = await self._get_event_info(event_id)
        currency_name = event_info.get("currency", {}).get("name", "Token Sự Kiện")
        currency_emoji = event_info.get("currency", {}).get("emoji", "🎫")
        
        converted_count = 0
        for participant in participants:
            user_id = participant["user_id"]
            currency_amount = participant["currency"]
            
            success = await self._convert_to_collectible(
                guild_id, user_id, event_id, currency_amount, currency_name, currency_emoji
            )
            if success:
                converted_count += 1
        
        await execute_write(
            "INSERT INTO event_notifications_sent (guild_id, event_id, notification_type) VALUES (?, ?, 'event_ended')",
            (guild_id, event_id)
        )
        
        logger.info(f"Event {event_id} ended: converted currency for {converted_count}/{len(participants)} participants")
    
    async def _convert_to_collectible(
        self,
        guild_id: int,
        user_id: int,
        event_id: str,
        currency_amount: int,
        currency_name: str,
        currency_emoji: str
    ) -> bool:
        collectible_key = f"collectible_{event_id}"
        
        try:
            await main_db.execute(
                """
                INSERT INTO event_conversion_ledger 
                (guild_id, user_id, event_id, original_currency, conversion_type, result_item_key, status)
                VALUES ($1, $2, $3, $4, 'collectible', $5, 'pending')
                """,
                guild_id, user_id, event_id, currency_amount, collectible_key
            )
            
            await execute_write(
                "UPDATE event_participation SET currency = 0 WHERE guild_id = ? AND user_id = ? AND event_id = ?",
                (guild_id, user_id, event_id)
            )
            
            collectible_display = f"{currency_emoji} {currency_name} x{currency_amount}"
            await self._add_collectible_to_inventory(user_id, collectible_key, currency_amount, event_id, collectible_display)
            
            await main_db.execute(
                """
                UPDATE event_conversion_ledger 
                SET status = 'completed', completed_at = NOW()
                WHERE user_id = $1 AND event_id = $2 AND status = 'pending'
                """,
                user_id, event_id
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to convert currency for user {user_id}: {e}")
            await main_db.execute(
                """
                UPDATE event_conversion_ledger 
                SET status = 'failed'
                WHERE user_id = $1 AND event_id = $2 AND status = 'pending'
                """,
                user_id, event_id
            )
            return False
    
    async def _add_collectible_to_inventory(
        self,
        user_id: int,
        collectible_key: str,
        amount: int,
        event_id: str,
        display_name: str
    ) -> None:
        await self.bot.inventory.modify(user_id, collectible_key, amount)
        logger.debug(f"Added collectible {collectible_key} x{amount} to user {user_id}")
    
    async def _get_event_info(self, event_id: str) -> dict[str, Any]:
        try:
            from cogs.seasonal.core.event_manager import EventManager
            manager = EventManager.get_instance()
            return manager.get_event_config(event_id) or {}
        except Exception:
            return {}
    
    async def manual_convert_to_seeds(
        self,
        guild_id: int,
        user_id: int,
        event_id: str,
        amount: int | None = None
    ) -> tuple[bool, int, str]:
        participation = await execute_query(
            "SELECT currency FROM event_participation WHERE guild_id = ? AND user_id = ? AND event_id = ?",
            (guild_id, user_id, event_id)
        )
        
        if not participation or participation[0]["currency"] <= 0:
            return False, 0, "Bạn không có currency sự kiện để đổi."
        
        available_currency = participation[0]["currency"]
        convert_amount = min(amount, available_currency) if amount else available_currency
        
        if convert_amount <= 0:
            return False, 0, "Số lượng không hợp lệ."
        
        seeds_reward = convert_amount * CONVERSION_RATE_TO_SEEDS
        
        try:
            await main_db.execute(
                """
                INSERT INTO event_conversion_ledger 
                (guild_id, user_id, event_id, original_currency, conversion_type, result_seeds, status)
                VALUES ($1, $2, $3, $4, 'seeds', $5, 'pending')
                """,
                guild_id, user_id, event_id, convert_amount, seeds_reward
            )
            
            await execute_write(
                "UPDATE event_participation SET currency = currency - ? WHERE guild_id = ? AND user_id = ? AND event_id = ?",
                (convert_amount, guild_id, user_id, event_id)
            )
            
            from core.economy_repository import EconomyRepository
            economy = EconomyRepository()
            await economy.add_seeds(user_id, seeds_reward)
            
            await main_db.execute(
                """
                UPDATE event_conversion_ledger 
                SET status = 'completed', completed_at = NOW()
                WHERE user_id = $1 AND event_id = $2 AND conversion_type = 'seeds' AND status = 'pending'
                """,
                user_id, event_id
            )
            
            return True, seeds_reward, f"Đã đổi {convert_amount} currency → {seeds_reward} Hạt!"
            
        except Exception as e:
            logger.error(f"Failed to convert currency to seeds for user {user_id}: {e}")
            return False, 0, "Có lỗi xảy ra khi đổi currency."


async def setup_lifecycle_service(bot: "Bot") -> EventLifecycleService:
    service = EventLifecycleService.get_instance(bot)
    await service.start_scheduler()
    return service

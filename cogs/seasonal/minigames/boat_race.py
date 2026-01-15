from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord

from ..minigames.base import BaseMinigame, register_minigame
from ..services import add_contribution, add_currency, get_active_event, update_community_progress
from ..services.database import execute_query, execute_write

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager

logger = logging.getLogger("BoatRace")


@dataclass
class Boat:
    emoji: str
    name: str
    description: str
    base_speed: float
    luck: float
    resist: float

    @property
    def id(self) -> str:
        return self.name.lower().replace(" ", "_")


BOATS = [
    Boat("⛵", "Sóng Bạc", "Cân bằng, ổn định", 2.0, 0.50, 0.30),
    Boat("🚤", "Gió Đông", "Nhanh nhưng dễ gặp sự cố", 3.0, 0.30, 0.10),
    Boat("🛥️", "Hải Âu", "Chậm chắc, ít tai nạn", 1.5, 0.40, 0.60),
    Boat("🚢", "Đại Dương", "Khổng lồ, immune sóng nhỏ", 1.0, 0.50, 0.80),
    Boat("⛴️", "Thủy Triều", "Bí ẩn, không ai đoán được", 0, 0.70, 0.20),
    Boat("🛶", "Sóng Thần", "Cực nhanh, cực rủi ro", 4.0, 0.20, 0.00),
    Boat("🚣", "Rái Cá", "Nhỏ gọn, dễ lách sóng", 2.5, 0.60, 0.40),
    Boat("🛳️", "Long Vương", "Huyền thoại, khó lường", 0, 0.80, 0.50),
]

RACE_EVENTS = [
    {"emoji": "💨", "name": "Gió Thuận", "chance": 0.15, "effect": 2, "message": "đón gió thuận, tăng tốc!"},
    {"emoji": "🌊", "name": "Sóng Lớn", "chance": 0.12, "effect": -1, "message": "gặp sóng lớn!"},
    {"emoji": "🐬", "name": "Cá Heo Giúp", "chance": 0.08, "effect": 2, "message": "được cá heo đẩy!"},
    {"emoji": "🦦", "name": "Rái Cá Đẩy", "chance": 0.08, "effect": 3, "message": "được đàn rái cá hỗ trợ!"},
    {"emoji": "🌿", "name": "Mắc Rong", "chance": 0.10, "effect": -2, "message": "bị mắc rong biển!"},
    {"emoji": "⚡", "name": "Turbo", "chance": 0.05, "effect": 4, "message": "kích hoạt TURBO!"},
    {"emoji": "🔧", "name": "Hỏng Động Cơ", "chance": 0.05, "effect": 0, "skip": True, "message": "bị hỏng động cơ!"},
    {"emoji": "🧜‍♀️", "name": "Tiên Cá", "chance": 0.03, "effect": 5, "last_only": True, "message": "được tiên cá giúp đỡ!"},
]

FINISH_LINE = 25


@register_minigame("boat_race")
class BoatRaceMinigame(BaseMinigame):
    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)
        self._active_races: dict[int, dict] = {}

    @property
    def name(self) -> str:
        return "Đua Thuyền"

    @property
    def spawn_config(self) -> dict[str, Any]:
        return {
            "spawn_type": "mixed",
            "scheduled_times": ["20:00"],
            "times_per_day": [2, 3],
            "active_hours": [10, 22],
            "registration_seconds": 60,
            "race_interval_seconds": 3.5,
            "suspense_interval_seconds": 5.0,
        }

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        config = self.spawn_config
        reg_time = config.get("registration_seconds", 60)
        expire_time = datetime.now() + timedelta(seconds=reg_time)

        boat_stats = await self._get_boat_stats(guild_id)

        embed = self._create_registration_embed(event, boat_stats, expire_time, 0)
        view = BoatSelectionView(self, guild_id, active["event_id"], expire_time)
        message = await channel.send(embed=embed, view=view)
        
        logger.info(f"[BOAT_RACE] Spawned in guild {guild_id}, channel {channel.id}, reg_time={reg_time}s")

        self._active_races[message.id] = {
            "guild_id": guild_id,
            "event_id": active["event_id"],
            "participants": {},
            "expire_time": expire_time,
            "message": message,
            "channel": channel,
            "phase": "registration",
            "boat_stats": boat_stats,
        }

        self.bot.loop.create_task(self._start_race_after_registration(message.id, reg_time))

    def _create_registration_embed(
        self, event: Any, boat_stats: dict, expire_time: datetime, participant_count: int
    ) -> discord.Embed:
        embed = discord.Embed(
            title="🚤 ĐUA THUYỀN - CHỌN THUYỀN!",
            description="Chọn thuyền của bạn để tham gia cuộc đua!",
            color=event.color if event else 0x00CED1,
        )

        lines = []
        for boat in BOATS:
            stats = boat_stats.get(boat.id, {"wins": 0, "races": 0})
            win_rate = (stats["wins"] / stats["races"] * 100) if stats["races"] > 0 else 0
            lines.append(f"{boat.emoji} **{boat.name}** │ _{boat.description}_ │ 🏆 {stats['wins']} ({win_rate:.0f}%)")

        embed.add_field(name="🚢 Thuyền Đua", value="\n".join(lines), inline=False)
        embed.add_field(name="👥 Người chơi", value=str(participant_count), inline=True)
        embed.add_field(name="⏰ Bắt đầu", value=f"<t:{int(expire_time.timestamp())}:R>", inline=True)

        return embed

    async def _get_boat_stats(self, guild_id: int) -> dict:
        rows = await execute_query(
            "SELECT boat_id, wins, races FROM boat_race_history WHERE guild_id = ?",
            (guild_id,),
        )
        return {row["boat_id"]: {"wins": row["wins"], "races": row["races"]} for row in rows}

    async def _start_race_after_registration(self, message_id: int, delay: int) -> None:
        await asyncio.sleep(delay)

        data = self._active_races.get(message_id)
        if not data or data["phase"] != "registration":
            return

        if not data["participants"]:
            embed = discord.Embed(
                title="🚤 ĐUA THUYỀN - HỦY",
                description="Không có ai tham gia cuộc đua!",
                color=0xFF0000,
            )
            try:
                await data["message"].edit(embed=embed, view=None)
            except discord.NotFound:
                pass
            del self._active_races[message_id]
            return

        data["phase"] = "racing"
        await self._run_race(message_id)

    async def _run_race(self, message_id: int) -> None:
        data = self._active_races.get(message_id)
        if not data:
            return

        positions = {boat.id: 0 for boat in BOATS}
        skip_next = {boat.id: False for boat in BOATS}
        round_num = 0
        event_log: list[str] = []

        event = self.event_manager.get_event(data["event_id"])
        interval = self.spawn_config.get("race_interval_seconds", 3.5)
        suspense_interval = self.spawn_config.get("suspense_interval_seconds", 5.0)
        
        participant_count = len(data["participants"])
        logger.info(f"[BOAT_RACE] Race started in guild {data['guild_id']} with {participant_count} participants")

        while max(positions.values()) < FINISH_LINE:
            round_num += 1
            round_events = []
            
            is_final_stretch = max(positions.values()) >= FINISH_LINE - 5
            is_photo_finish = self._check_photo_finish(positions)

            for boat in BOATS:
                if skip_next[boat.id]:
                    skip_next[boat.id] = False
                    continue

                if boat.base_speed == 0:
                    speed = random.uniform(0, 5)
                else:
                    speed = boat.base_speed

                for race_event in RACE_EVENTS:
                    if random.random() < race_event["chance"]:
                        if race_event.get("last_only"):
                            last_boat = min(positions, key=positions.get)
                            if boat.id != last_boat:
                                continue

                        if random.random() > boat.resist:
                            if race_event.get("skip"):
                                skip_next[boat.id] = True
                                round_events.append(f"{race_event['emoji']} {boat.name} {race_event['message']}")
                            else:
                                speed += race_event["effect"]
                                round_events.append(f"{race_event['emoji']} {boat.name} {race_event['message']}")
                        break

                positions[boat.id] = max(0, min(FINISH_LINE, positions[boat.id] + int(speed)))

            if round_events:
                event_log = round_events[-3:]

            embed = self._create_race_embed(event, positions, round_num, event_log, is_final_stretch)
            try:
                await data["message"].edit(embed=embed)
            except discord.NotFound:
                logger.warning(f"[BOAT_RACE] Message deleted during race in guild {data['guild_id']}")
                return

            if is_final_stretch and is_photo_finish:
                await asyncio.sleep(suspense_interval)
            else:
                await asyncio.sleep(interval)

        logger.info(f"[BOAT_RACE] Race finished in guild {data['guild_id']} after {round_num} rounds")
        await self._finish_race(message_id, positions)
    
    def _check_photo_finish(self, positions: dict) -> bool:
        top_positions = sorted(positions.values(), reverse=True)[:3]
        if len(top_positions) >= 2:
            return top_positions[0] - top_positions[1] <= 3
        return False

    def _create_race_embed(
        self, event: Any, positions: dict, round_num: int, event_log: list[str], is_final_stretch: bool = False
    ) -> discord.Embed:
        title = f"🏁 ĐUA THUYỀN - VÒNG {round_num}"
        if is_final_stretch:
            title = f"🔥 ĐUA THUYỀN - NƯỚC RÚT! VÒNG {round_num}"
        
        embed = discord.Embed(
            title=title,
            color=event.color if event else 0x00CED1,
        )

        sorted_boats = sorted(BOATS, key=lambda b: positions[b.id], reverse=True)

        lines = ["🏆 **ĐÍCH** " + "═" * 30]
        for boat in sorted_boats:
            pos = positions[boat.id]
            progress = int((pos / FINISH_LINE) * 20)
            bar = "═" * progress + f" {boat.emoji} " + "░" * (20 - progress)
            pct = int((pos / FINISH_LINE) * 100)
            lines.append(f"{boat.emoji} {boat.name} {bar} {pct}%")
        lines.append("🏁 **XUẤT PHÁT** " + "═" * 27)

        embed.add_field(name="🚣 Đường Đua", value="\n".join(lines), inline=False)

        if event_log:
            embed.add_field(name="📢 Diễn Biến", value="\n".join(event_log), inline=False)
        
        if is_final_stretch:
            embed.set_footer(text="⚡ NƯỚC RÚT! Ai sẽ về đích trước?!")

        return embed

    async def _finish_race(self, message_id: int, positions: dict) -> None:
        data = self._active_races.get(message_id)
        if not data:
            return

        sorted_results = sorted(positions.items(), key=lambda x: x[1], reverse=True)
        winner_id = sorted_results[0][0]

        await self._update_boat_history(data["guild_id"], winner_id)

        event = self.event_manager.get_event(data["event_id"])
        emoji = event.currency_emoji if event else "🐚"

        rewards = {0: 100, 1: 50, 2: 25}
        participation_reward = 10

        results_text = []
        medals = ["🥇", "🥈", "🥉"]

        for i, (boat_id, _) in enumerate(sorted_results[:3]):
            boat = next((b for b in BOATS if b.id == boat_id), None)
            if boat:
                results_text.append(f"{medals[i]} **{boat.name}** {boat.emoji}")

        embed = discord.Embed(
            title="🏁 ĐUA THUYỀN - KẾT THÚC!",
            description="\n".join(results_text),
            color=event.color if event else 0x00CED1,
        )

        top_3_users: dict[int, list[int]] = {0: [], 1: [], 2: []}
        other_users: list[tuple[int, int]] = []
        
        for user_id, boat_id in data["participants"].items():
            rank = next((i for i, (bid, _) in enumerate(sorted_results) if bid == boat_id), -1)
            reward = rewards.get(rank, participation_reward)

            await add_currency(data["guild_id"], user_id, data["event_id"], reward)
            await add_contribution(data["guild_id"], user_id, data["event_id"], reward)
            await self._update_user_streak(data["guild_id"], user_id, boat_id == winner_id)

            if rank in top_3_users:
                top_3_users[rank].append(user_id)
            else:
                other_users.append((user_id, reward))

        winner_lines = []
        for rank, users in top_3_users.items():
            if users:
                reward = rewards[rank]
                mentions = " ".join([f"<@{uid}>" for uid in users[:5]])
                if len(users) > 5:
                    mentions += f" (+{len(users) - 5} người khác)"
                winner_lines.append(f"{medals[rank]} {mentions} → **+{reward}** {emoji}")
        
        if winner_lines:
            embed.add_field(
                name="🎉 Người chiến thắng",
                value="\n".join(winner_lines),
                inline=False,
            )
        
        if other_users:
            other_count = len(other_users)
            embed.add_field(
                name="🎖️ Người tham gia",
                value=f"{other_count} người khác nhận **+{participation_reward}** {emoji}",
                inline=False,
            )

        embed.add_field(
            name="💰 Bảng phần thưởng",
            value=f"🥇 +100 {emoji} │ 🥈 +50 {emoji} │ 🥉 +25 {emoji} │ 🎖️ +10 {emoji}",
            inline=False,
        )
        
        total_rewards = sum(rewards.get(next((i for i, (bid, _) in enumerate(sorted_results) if bid == bid_p), -1), participation_reward) for _, bid_p in data["participants"].items())
        logger.info(f"[BOAT_RACE] Race completed in guild {data['guild_id']}, {len(data['participants'])} participants, {total_rewards} total rewards distributed")

        try:
            await data["message"].edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        del self._active_races[message_id]

    async def _update_boat_history(self, guild_id: int, winner_id: str) -> None:
        for boat in BOATS:
            is_winner = 1 if boat.id == winner_id else 0
            await execute_write(
                """
                INSERT INTO boat_race_history (guild_id, boat_id, wins, races)
                VALUES (?, ?, ?, 1)
                ON CONFLICT (guild_id, boat_id) DO UPDATE SET
                    wins = boat_race_history.wins + ?,
                    races = boat_race_history.races + 1
                """,
                (guild_id, boat.id, is_winner, is_winner),
            )

    async def _update_user_streak(self, guild_id: int, user_id: int, won: bool) -> None:
        if won:
            await execute_write(
                """
                INSERT INTO boat_race_streaks (guild_id, user_id, current_streak, best_streak)
                VALUES (?, ?, 1, 1)
                ON CONFLICT (guild_id, user_id) DO UPDATE SET
                    current_streak = boat_race_streaks.current_streak + 1,
                    best_streak = GREATEST(boat_race_streaks.best_streak, boat_race_streaks.current_streak + 1)
                """,
                (guild_id, user_id),
            )
        else:
            await execute_write(
                """
                INSERT INTO boat_race_streaks (guild_id, user_id, current_streak, best_streak)
                VALUES (?, ?, 0, 0)
                ON CONFLICT (guild_id, user_id) DO UPDATE SET
                    current_streak = 0
                """,
                (guild_id, user_id),
            )

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def select_boat(self, interaction: Interaction, message_id: int, boat_id: str) -> None:
        data = self._active_races.get(message_id)
        if not data:
            await interaction.response.send_message("❌ Cuộc đua này đã kết thúc!", ephemeral=True)
            return

        if data["phase"] != "registration":
            await interaction.response.send_message("❌ Đã hết thời gian đăng ký!", ephemeral=True)
            return

        if datetime.now() > data["expire_time"]:
            await interaction.response.send_message("❌ Đã hết thời gian đăng ký!", ephemeral=True)
            return

        boat = next((b for b in BOATS if b.id == boat_id), None)
        if not boat:
            await interaction.response.send_message("❌ Thuyền không hợp lệ!", ephemeral=True)
            return

        old_boat = data["participants"].get(interaction.user.id)
        data["participants"][interaction.user.id] = boat_id

        if old_boat:
            old_boat_obj = next((b for b in BOATS if b.id == old_boat), None)
            await interaction.response.send_message(
                f"🔄 Đã đổi từ {old_boat_obj.emoji if old_boat_obj else ''} sang {boat.emoji} **{boat.name}**!",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"✅ Đã chọn {boat.emoji} **{boat.name}**! Chúc may mắn!",
                ephemeral=True,
            )

        event = self.event_manager.get_event(data["event_id"])
        embed = self._create_registration_embed(
            event, data["boat_stats"], data["expire_time"], len(data["participants"])
        )
        try:
            await data["message"].edit(embed=embed)
        except discord.NotFound:
            pass


class BoatSelectionView(discord.ui.View):
    def __init__(
        self,
        minigame: BoatRaceMinigame,
        guild_id: int,
        event_id: str,
        expire_time: datetime,
    ) -> None:
        timeout = (expire_time - datetime.now()).total_seconds()
        super().__init__(timeout=max(timeout, 1))
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id
        self.message_id: int | None = None

        for i, boat in enumerate(BOATS):
            button = discord.ui.Button(
                emoji=boat.emoji,
                style=discord.ButtonStyle.secondary,
                custom_id=f"boat_{boat.id}",
                row=i // 4,
            )
            button.callback = self._make_callback(boat.id)
            self.add_item(button)

    def _make_callback(self, boat_id: str):
        async def callback(interaction: discord.Interaction) -> None:
            if self.message_id is None:
                self.message_id = interaction.message.id
            await self.minigame.select_boat(interaction, self.message_id, boat_id)

        return callback

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

import json
import random
import time
import asyncio
from datetime import datetime
from discord.ext import tasks
import discord
from core.logger import setup_logger
from database_manager import db_manager, add_item, add_seeds, get_stat, increment_stat
from ..mechanics.event_views import MeteorWishView

logger = setup_logger("GlobalEvents", "cogs/fishing/global_events.log")

class GlobalEventManager:
    """Manages global time-based events for the fishing system.
    
    Handles scheduling, random triggers, active effects, and raid mechanics.
    """
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/fishing_global_events.json"
        self.config = {}
        
        # State
        self.current_event = None  # { "key": str, "end_time": float, "data": dict, "message_id": int }
        self.active_effects = {}
        self.last_event_times = {} # { event_key: timestamp_finished }
        
        # Raid State
        self.raid_state = {
            "active": False,
            "hp_current": 0,
            "hp_max": 0,
            "contributors": {}, # { user_id: total_value }
            "start_time": 0,
            "message": None     # Discord Message object for editing
        }

        # Mini Game state
        self.last_minigame_spawn = 0
        self.next_minigame_spawn_delay = 0
        
        # Load initially
        self.load_config()
        
        # Initialize Loop using Config
        interval = self.config.get("meta_config", {}).get("check_interval_seconds", 60)
        self._loop_task = tasks.loop(seconds=interval)(self._event_check_loop)

    def load_config(self):
        """Reloads configuration from JSON."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            logger.info("Global Event Config loaded successfully.")
            
            # Update Loop Interval if changed
            if hasattr(self, "_loop_task"):
                new_interval = self.config.get("meta_config", {}).get("check_interval_seconds", 60)
                if self._loop_task.seconds != new_interval:
                     self._loop_task.change_interval(seconds=new_interval)
                     logger.info(f"Global Event Loop interval updated to {new_interval}s")
        except Exception as e:
            logger.error(f"Failed to load Global Event Config: {e}")
            self.config = {"events": {}}

    def start(self):
        """Starts the event monitoring loop."""
        logger.info("Starting Global Event Manager Loop...")
        self._loop_task.start()

    def unload(self):
        """Stops the loop."""
        self._loop_task.cancel()

    # ==================== LOOP LOGIC ====================

    async def _event_check_loop(self):
        """Main loop checking for event triggers every minute."""
        try:
            now = datetime.now()
            current_hhmm = now.strftime("%H:%M")
            weekday = now.weekday() # 0=Mon, 6=Sun
            
            # Debug Trace
            logger.info(f"[EVENT_LOOP] Checking events at {current_hhmm} (Weekday: {weekday})")
            
            # 1. Check if an event is currently running
            if self.current_event:
                # Check if event expired
                if time.time() > self.current_event["end_time"]:
                    await self.end_current_event()
                else:
                    # Handle Mini-Game Ticks (Meteor Shower)
                    if self.current_event["data"].get("type") == "mini_game":
                        await self._process_mini_game()
                    # Raid Status Updates
                    elif self.current_event["data"].get("type") == "raid_boss":
                        await self._update_raid_status()
                return # Don't start new event if one is running (System limitation for simplicity)

            # 2. Check for potential events
            events_cfg = self.config.get("events", {})
             # Sort by priority desc
            sorted_events = sorted(
                events_cfg.items(), 
                key=lambda x: x[1].get("priority", 0), 
                reverse=True
            )

            for key, event_data in sorted_events:
                schedule = event_data.get("schedule", {})
                
                # A. Check Cooldown
                last_run = self.last_event_times.get(key, 0)
                cooldown = schedule.get("cooldown_minutes", 0) * 60
                if time.time() < last_run + cooldown:
                    continue # On cooldown
                
                # B. Check Day
                days = schedule.get("days", [])
                if days and weekday not in days:
                    continue
                
                # C. Check Time Range
                valid_time = False
                time_ranges = schedule.get("time_ranges", ["00:00-23:59"])
                for rng in time_ranges:
                    start_str, end_str = rng.split("-")
                    # Simple string comparison works for HH:MM format
                    if start_str <= current_hhmm <= end_str:
                        valid_time = True
                        break
                
                if not valid_time:
                    continue

                # D. Check Probability (Frequency Chance)
                chance = schedule.get("frequency_chance", 0.0)
                
                trigger = False
                if chance >= 1.0:
                    trigger = True
                else:
                    trigger = random.random() < chance
                
                # VERBOSE LOG
                logger.info(f"[DEBUG] Event {key}: ValidTime={valid_time} Trigger={trigger} LastRun={last_run}")
                
                if not trigger:
                    continue
                else:
                    # Random Event
                    if random.random() < chance:
                        trigger = True

                if trigger:
                    logger.info(f"[EVENT_LOOP] Triggering event: {key} (Chance: {chance})")
                    await self.start_event(key, event_data)
                    break # Only start one event at a time
                else:
                    logger.info(f"[EVENT_LOOP] Event {key} condition met but probability failed (Chance: {chance})")

        except Exception as e:
            logger.error(f"Global Event Loop Error: {e}", exc_info=True)

    # ==================== EVENT CONTROL ====================

    async def start_event(self, key, data):
        """Activates an event."""
        duration = data["schedule"].get("duration_minutes", 30) * 60
        self.current_event = {
            "key": key,
            "end_time": time.time() + duration,
            "data": data,
            "start_time": time.time()
        }
        
        # Cache active effects
        self.active_effects = data.get("effects", {})
        
        # Special Setup
        if data["type"] == "raid_boss":
            await self._setup_raid(data)
        
        logger.info(f"[GLOBAL_EVENT] Started: {key} (Duration: {duration}s)")
        
        # Announce
        await self._broadcast_message(data.get("messages", {}).get("start"))

    async def end_current_event(self):
        """Ends the currently active event."""
        if not self.current_event: 
            return

        key = self.current_event["key"]
        data = self.current_event["data"]
        
        # Special Cleanup
        if data["type"] == "raid_boss":
            await self._finalize_raid(data)
        
        # Announce End
        await self._broadcast_message(data.get("messages", {}).get("end"))
        
        # Reset State
        self.last_event_times[key] = time.time()
        self.current_event = None
        self.active_effects = {}
        self.raid_state["active"] = False
        
        logger.info(f"[GLOBAL_EVENT] Ended: {key}")

    async def _broadcast_message(self, content):
        """Sends announcement to all configured fishing channels (Rich Embed)."""
        if not content: return
        
        try:
            # Detect Event Config for Styling
            visuals = self.current_event.get("data", {}).get("visuals", {})
            
            # Default Style
            color = discord.Color.blue()
            title = "📢 THÔNG BÁO SỰ KIỆN"
            image = visuals.get("image_url")

            # Dynamic Options
            if "title" in visuals:
                title = visuals["title"]
            
            if "color" in visuals:
                try:
                    hex_str = visuals["color"]
                    if hex_str.startswith("#"):
                        value = int(hex_str.lstrip("#"), 16)
                        color = discord.Color(value)
                except Exception as e:
                    logger.warning(f"Invalid color {visuals.get('color')}: {e}")

            # Build Embed
            # Content separation logic (if content has title line)
            lines = content.split("\n", 1)
            # If the JSON already provides a specific title (like "MƯA SAO BĂNG"),
            # we might want to prioritize it over the message content's first line if it's generic.
            # But the current logic appends custom_title to base title.
            # Let's keep the content clean - if visuals has title, we use it as Base.
            
            description = content
            # If content starts with a header, it might duplicate the Visual Title.
            # The current content in JSON often repeats the title in the message. 
            # e.g., "🌌 **DẠ TIỆC ÁNH SAO BẮT ĐẦU!**\n..."
            # For now, let's trust the JSON content is formatted for the Description.
                
            embed = discord.Embed(title=title, description=description, color=color)
            if image: embed.set_image(url=image)

            # Get Configured Channels
            rows = await db_manager.execute(
                "SELECT fishing_channel_id FROM server_config WHERE fishing_channel_id IS NOT NULL"
            )
            
            if not rows: return
            
            from ..mechanics.view_registry import get_view_class

            for (channel_id,) in rows:
                try:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        # DYNAMIC VIEW LOADING
                        view = None
                        view_type = self.current_event.get("data", {}).get("mechanics", {}).get("view_type")
                        if view_type:
                            ViewClass = get_view_class(view_type)
                            if ViewClass:
                                # Instantiate View
                                # NOTE: Different views take different args. Ideally standardize this.
                                # Current legacy support:
                                if view_type == "TrashSellView":
                                    view = ViewClass(self)
                                elif view_type == "MeteorWishView":
                                    view = ViewClass(self.bot.get_cog("FishingCog"))
                                else:
                                    # Try default instantiation (if supported in future)
                                    try:
                                        view = ViewClass(self)
                                    except:
                                        logger.warning(f"Could not instantiate view {view_type}")
                        
                        await channel.send(embed=embed, view=view)
                except Exception as e:
                    logger.warning(f"Failed to send event msg to {channel_id}: {e}")
        except Exception as e:
            logger.error(f"Broadcast error: {e}")

    # ==================== RAID MECHANICS ====================

    async def _setup_raid(self, data):
        # RAM-ONLY State
        self.raid_state = {
            "active": True,
            "hp_current": data["mechanics"]["hp_goal"], 
            "hp_max": data["mechanics"]["hp_goal"],
            "contributors": {},
            "start_time": time.time(),
            "message": None
        }
        logger.info(f"Raid Setup: HP {self.raid_state['hp_max']} (RAM Mode)")
        
    async def process_raid_contribution(self, user_id, value):
        """Called when user sells fish during raid."""
        if not self.raid_state["active"]: return 0
        
        # Add contribution
        current = self.raid_state["contributors"].get(user_id, 0)
        self.raid_state["contributors"][user_id] = current + value
        
        # Damage Boss
        self.raid_state["hp_current"] -= value
        if self.raid_state["hp_current"] < 0:
            self.raid_state["hp_current"] = 0
            
        logger.info(f"[RAID] User {user_id} dealt {value} dmg. Boss HP: {self.raid_state['hp_current']}")
        return value

    async def _finalize_raid(self, data):
        """Rewards and Cleanup - RAM Powered (Data Driven)."""
        if not self.raid_state["active"]: return
        
        success = self.raid_state["hp_current"] == 0
        contributors = self.raid_state["contributors"]
        
        if not contributors:
            logger.info("Raid ended with no contributors.")
            return

        # 1. Sort Contributors
        sorted_users = sorted(contributors.items(), key=lambda x: x[1], reverse=True)
        top_users = sorted_users[:3]
        
        summary_text = ""
        
        # 2. Reward Logic
        if success:
             rewards_config = data.get("rewards", {}).get("success", {})
             base_items_cfg = rewards_config.get("items", [])
             mvp_items_cfg = rewards_config.get("mvp_bonus", [])
             
             summary_text = "🎉 **CHIẾN THẮNG!** Cthulhu đã bị đánh bại!\n\n"
             
             # Helper to process item list config
             async def give_reward_items(uid, items_cfg, multiplier=1):
                 added_text = []
                 for item in items_cfg:
                     key = item["key"]
                     qty = random.randint(item["min"], item["max"]) * multiplier
                     if qty > 0:
                         await add_item(uid, key, qty)
                         # Try to get emoji name if possible, else key
                         added_text.append(f"{qty} {key}")
                 return ", ".join(added_text)

             # AWARD MVP (Top 1)
             if len(top_users) >= 1:
                 user_id, dmg = top_users[0]
                 # Achievement
                 try:
                     await self.bot.achievement_manager.check_unlock(user_id, "fishing", "god_slayer", 1, None)
                 except: pass
                 
                 # Base + MVP Bonus
                 base_txt = await give_reward_items(user_id, base_items_cfg)
                 mvp_txt = await give_reward_items(user_id, mvp_items_cfg)
                 
                 summary_text += f"🥇 <@{user_id}>: **{dmg:,} Điểm**\n"
                 if mvp_txt: summary_text += f"   🎁 MVP Bonus: {mvp_txt}\n"
                 if base_txt: summary_text += f"   📦 Quà tham gia: {base_txt}\n"
             
             # AWARD OTHERS (Top 2-3 get just Base? Or logic for tiers? User said 'participant get items')
             # So EVERYONE gets base items.
             # Loop through ALL contributors excluding MVP (already gave base)
             mvp_id = top_users[0][0] if top_users else None
             
             count_others = 0
             for user_id, dmg in sorted_users:
                 if user_id == mvp_id: continue
                 
                 await give_reward_items(user_id, base_items_cfg)
                 count_others += 1
                 # Mention Top 2/3 specifically?
                 if any(u[0] == user_id for u in top_users[1:]):
                     rank = "🥈" if user_id == top_users[1][0] else "🥉"
                     summary_text += f"{rank} <@{user_id}>: **{dmg:,} Điểm** - Nhận quà tham gia!\n"
            
             if count_others > len(top_users) - 1:
                 summary_text += f"\n✨ **Và {count_others - (len(top_users)-1)} chiến binh khác** đã nhận được quà tham gia!"

        else:
             summary_text = "💀 **THẤT BẠI!** Cthulhu đã tàn phá server...\n\n"
             summary_text += f"Boss còn: **{self.raid_state['hp_current']:,} HP**\n"
             
             # Apply Debuff from JSON
             fail_config = data.get("rewards", {}).get("fail", {})
             debuff = fail_config.get("global_debuff")
             
             if debuff == "market_crash_50":
                  summary_text += "📉 **THỊ TRƯỜNG SỤP ĐỔ!** Giá cá giảm 50% trong 12h tới."
                  # Logic to apply global debuff state? 
                  # Currently system relies on active events. 
                  # Ideally we set a "lingering_effect" flag in DB or Manager.
                  # For now just text.
                  
             # Consolation (not in JSON but kept for UX)
             for user_id, _ in sorted_users:
                 await add_seeds(user_id, 100)
             summary_text += "\n🩹 **Quà an ủi:** 100 Hạt cho mỗi người tham gia."

        # 3. Broadcast Result
        embed = discord.Embed(
            title="🏁 KẾT THÚC RAID CTHULHU",
            description=summary_text,
            color=discord.Color.green() if success else discord.Color.red()
        )
        if success:
             embed.set_image(url="https://media.discordapp.net/attachments/1253945310690934835/1266023778536009778/cthulhu.png")
             
        await self._broadcast_raid_update(embed) # Reuse broadcast helper for simplicity, or _broadcast_message

    async def _update_raid_status(self):
        """Updates the raid status embed in channels (throttled)."""
        if not self.raid_state["active"]: return
        
        # 1. Throttle Updates (Max once every 60s)
        now = time.time()
        last_update = self.raid_state.get("last_update", 0)
        if now - last_update < 60:
            return
        self.raid_state["last_update"] = now
        
        # 2. Build Embed (VIETNAMESE UI)
        percent = (self.raid_state["hp_current"] / self.raid_state["hp_max"]) * 100
        hp_bar_len = 20
        filled = int((self.raid_state["hp_current"] / self.raid_state["hp_max"]) * hp_bar_len)
        bar = "█" * filled + "░" * (hp_bar_len - filled)
        
        embed = discord.Embed(title="🐙 TÌNH HÌNH CHIẾN SỰ CTHULHU", color=discord.Color.dark_red())
        embed.description = f"**Máu:** `{self.raid_state['hp_current']:,} / {self.raid_state['hp_max']:,}`\n`[{bar}]` **{percent:.1f}%**"
        
        # Top Contributors
        sorted_contrib = sorted(self.raid_state["contributors"].items(), key=lambda x: x[1], reverse=True)[:3]
        top_text = ""
        for i, (uid, val) in enumerate(sorted_contrib, 1):
             top_text += f"{'🥇' if i==1 else '🥈' if i==2 else '🥉'} <@{uid}>: **{val:,}** Điểm\n"
        
        if top_text:
            embed.add_field(name="🏆 Chiến Thần", value=top_text, inline=False)
        else:
            embed.add_field(name="🏆 Chiến Thần", value="*Chưa có ai tham chiến...*", inline=False)
            
        embed.set_footer(text=f"Cập nhật lúc {datetime.now().strftime('%H:%M:%S')}")
            
        # 3. Broadcast with Delete-Old-And-Send-New pattern
        await self._broadcast_raid_update(embed)

    async def _broadcast_raid_update(self, embed):
        """Sends new status message and deletes the old one to prevent spam."""
        try:
            rows = await db_manager.execute("SELECT fishing_channel_id FROM server_config WHERE fishing_channel_id IS NOT NULL")
            
            # Initialize storage for message IDs if not exists
            if not hasattr(self, "raid_message_ids"):
                self.raid_message_ids = {} # {channel_id: message_id}
                
            for (cid,) in rows:
                try:
                    ch = self.bot.get_channel(cid)
                    if not ch: continue
                    
                    # A. Delete old message
                    old_msg_id = self.raid_message_ids.get(cid)
                    if old_msg_id:
                        try:
                            old_msg = await ch.fetch_message(old_msg_id)
                            await old_msg.delete()
                        except (discord.NotFound, discord.Forbidden):
                            pass # Message already gone or no perm
                        except Exception as e:
                            logger.warning(f"Error deleting old raid msg in {cid}: {e}")
                    
                    # B. Send new message
                    new_msg = await ch.send(embed=embed)
                    self.raid_message_ids[cid] = new_msg.id
                    
                except Exception as e:
                    logger.warning(f"Failed to update raid status in {cid}: {e}")
        except Exception as e:
            logger.error(f"Broadcast update error: {e}")

    async def _process_mini_game(self):
        """Handles periodic spawning of mini-games (e.g. Meteor Shower)."""
        now = time.time()
        
        # Initialize delay if first run
        if self.next_minigame_spawn_delay == 0:
            spawn_range = self.current_event.get("data", {}).get("mechanics", {}).get("spawn_interval", [60, 180])
            self.next_minigame_spawn_delay = random.randint(spawn_range[0], spawn_range[1])
            self.last_minigame_spawn = now
            return

        if now >= self.last_minigame_spawn + self.next_minigame_spawn_delay:
            # SPAWN IT
            view_class_name = self.current_event["data"].get("mechanics", {}).get("view_class")
            logger.info(f"[MINI_GAME] Spawning {view_class_name} now...")
            
            if view_class_name == "MeteorWishView":
                embed = discord.Embed(
                    title="🌟 MỘT NGÔI SAO VỪA VỤT QUA!",
                    description="Hãy nhanh tay **Ước Nguyện** trước khi nó biến mất!",
                    color=discord.Color.purple()
                )
                
                view = MeteorWishView(self)
                
                # Broadcast to configured channels
                rows = await db_manager.execute(
                    "SELECT fishing_channel_id FROM server_config WHERE fishing_channel_id IS NOT NULL"
                )
                if not rows:
                    logger.warning("[MINI_GAME] No fishing_channel configured in DB! Cannot send Meteor.")
                
                if rows:
                    count_sent = 0
                    for row in rows:
                        channel_id = int(row[0])
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            try:
                                await channel.send(embed=embed, view=view)
                                count_sent += 1
                            except Exception as e:
                                logger.error(f"Failed to send meteor to {channel_id}: {e}")
                        else:
                            logger.warning(f"[MINI_GAME] Channel {channel_id} not found/accessible.")
                    logger.info(f"[MINI_GAME] Meteor sent to {count_sent} channels.")
            
            # Reset Timer
            spawn_range = self.current_event["data"].get("mechanics", {}).get("spawn_interval", [60, 180])
            self.next_minigame_spawn_delay = random.randint(spawn_range[0], spawn_range[1])
            self.last_minigame_spawn = now
            logger.info(f"[MINI_GAME] Next spawn in {self.next_minigame_spawn_delay}s")
        else:
            # Verbose debug for user assurance (can remove later)
            remaining = (self.last_minigame_spawn + self.next_minigame_spawn_delay) - now
            logger.info(f"[MINI_GAME] Waiting... {remaining:.1f}s left")

    # ==================== HELPERS FOR COGS ====================

    def get_public_effect(self, effect_name, default=1.0):
        """Get active multiplier/effect value."""
        # 1. Check Event Effects
        if self.current_event:
            val = self.active_effects.get(effect_name)
            if val is not None: return val
            
        # 2. Check Lingering Effects
        if hasattr(self, "lingering_effects"):
             if effect_name == "money_multiplier" and "market_crash" in self.lingering_effects:
                 if time.time() < self.lingering_effects["market_crash"]:
                     return 0.5
        
        return default

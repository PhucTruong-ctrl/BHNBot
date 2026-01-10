import json
import random
import time
import asyncio
from datetime import datetime
from discord.ext import tasks
import discord
from core.logger import setup_logger
from database_manager import db_manager, add_seeds, get_stat, increment_stat, set_global_state, get_global_state
from ..ui import MeteorWishView

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

        # Dragon Quest State
        self.dragon_state = {
            "active": False,
            "requested_fish_key": "",
            "requested_fish_name": "",
            "quantity_goal": 0,
            "quantity_current": 0,
            "contributors": {},  # { user_id: quantity }
            "start_time": 0,
            "message_ids": {}  # { channel_id: message_id }
        }

        # Mini Game state
        self.last_minigame_spawn = 0
        self.next_minigame_spawn_delay = 0

        # Message Bump State
        self.last_bump_time = 0
        self.bump_message_ids = {} # {channel_id: message_id}
        
        # Initialization State
        self.ready = False
        
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
                     
            # Load Persistent Cooldowns
            # Use asyncio.create_task but ensure we set ready=True when done
            asyncio.create_task(self._load_cooldowns())
                     
        except Exception as e:
            logger.error(f"Failed to load Global Event Config: {e}")
            self.config = {"events": {}}
            # If config fails, we should still allow ready=True eventually or it blocks forever?
            # Likely minimal config loaded.

    async def _load_cooldowns(self):
        """Load last run times and ACTIVE STATE from DB to prevent spam."""
        try:
            # 1. Load Last Run Times
            data = await get_global_state("system_cooldowns", {})
            if data:
                self.last_event_times = data
                logger.info(f"Restored event cooldowns: {len(data)} events")
            
            # 2. Load Active Event State
            active_state = await get_global_state("active_global_event", None)
            
            if active_state:
                if time.time() < active_state.get("end_time", 0):
                    self.current_event = active_state
                    key = active_state.get("key")
                    logger.info(f"[RESTORE] Restored ACTIVE event: {key}")
                    
                    # Restore Raid/Dragon State logic into memory
                    event_data = active_state.get("data", {})
                    event_type = event_data.get("type", "passive")
                    
                    if event_type == "raid_boss":
                         await self._setup_raid(event_data)
                    elif event_type == "fish_quest_raid":
                         await self._setup_dragon_quest(event_data)
                    
                    # 3. Restore bump_message_ids from DB
                    stored_msg_ids = await get_global_state("event_bump_message_ids", {})
                    if stored_msg_ids:
                        # Convert string keys back to int (JSON serialization issue)
                        self.bump_message_ids = {int(k): v for k, v in stored_msg_ids.items()}
                        logger.info(f"[RESTORE] Restored {len(self.bump_message_ids)} message IDs")
                    
                    # 4. Re-register Views for existing messages
                    await self._reregister_event_views()
                    
                else:
                    logger.info("[RESTORE] Found stale active event in DB, clearing...")
                    await set_global_state("active_global_event", None)
                    await set_global_state("event_bump_message_ids", {})
                    
        except Exception as e:
            logger.warning(f"Failed to load global state: {e}")
        finally:
            self.ready = True
            logger.info("Global Event Manager is READY.")

    async def _reregister_event_views(self):
        """Re-register Views for existing event messages after bot restart."""
        if not self.current_event or not self.bump_message_ids:
            return
            
        event_data = self.current_event.get("data", {})
        view_type = event_data.get("data", {}).get("mechanics", {}).get("view_type")
        
        if not view_type:
            logger.info("[REREGISTER] No view_type for current event, skipping")
            return
            
        from ..mechanics.view_registry import get_view_class
        ViewClass = get_view_class(view_type)
        
        if not ViewClass:
            logger.warning(f"[REREGISTER] ViewClass not found for {view_type}")
            return
            
        success_count = 0
        for channel_id, message_id in list(self.bump_message_ids.items()):
            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    channel = await self.bot.fetch_channel(channel_id)
                    
                if not channel:
                    logger.warning(f"[REREGISTER] Channel {channel_id} not found")
                    continue
                    
                message = await channel.fetch_message(message_id)
                
                # Create fresh View instance
                if view_type == "MeteorWishView":
                    view = ViewClass(self.bot.get_cog("FishingCog"))
                else:
                    view = ViewClass(self)
                
                # Edit message to re-register View
                await message.edit(view=view)
                success_count += 1
                logger.info(f"[REREGISTER] Re-registered View for message {message_id} in channel {channel_id}")
                
            except discord.NotFound:
                logger.warning(f"[REREGISTER] Message {message_id} not found in channel {channel_id}")
                # Remove stale entry
                del self.bump_message_ids[channel_id]
            except Exception as e:
                logger.error(f"[REREGISTER] Error for channel {channel_id}: {e}")
        
        if success_count > 0:
            logger.info(f"[REREGISTER] Successfully re-registered {success_count} Views")

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
            if not self.ready:
                logger.info("[EVENT_LOOP] Manager not ready (DB loading), skipping tick.")
                return

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
                    # Dragon Quest Status Updates
                    elif self.current_event["data"].get("type") == "fish_quest_raid":
                        await self._update_dragon_status()
                    
                    # Generic Event Bump (Check BOTH locations for mechanics)
                    else:
                        event_data = self.current_event["data"]
                        mechanics = event_data.get("mechanics", {})
                        # Fallback for nested data (GenericActionView style)
                        if not mechanics:
                            mechanics = event_data.get("data", {}).get("mechanics", {})
                            
                        if mechanics.get("view_type") == "GenericActionView" or mechanics.get("bump_interval_seconds", 0) > 0:
                            await self._process_bump()

                return # Don't start new event if one is running

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
        
        # Reset bump
        self.last_bump_time = time.time()
        self.bump_message_ids = {}
        
        # Cache active effects
        self.active_effects = data.get("effects", {})
        
        # Special Setup
        # Special Setup
        event_type = data.get("type", "passive")
        
        if event_type == "raid_boss":
            await self._setup_raid(data)
        elif event_type == "fish_quest_raid":
            await self._setup_dragon_quest(data)
        
        logger.info(f"[GLOBAL_EVENT] Started: {key} (Duration: {duration}s)")
        
        # Announce (customize message for dragon quest)
        start_message = data.get("messages", {}).get("start")
        if event_type == "fish_quest_raid" and self.dragon_state.get("active"):
            # Replace placeholders with actual fish details
            start_message = f"🐲 **THẦN TÍCH: LONG THẦN ĐÃ XUẤT HIỆN!**\nNgài đang tìm kiếm sản vật tinh túy của đại dương và yêu cầu:\n🎯 **{self.dragon_state['quantity_goal']} con {self.dragon_state['requested_fish_name']}**\n💡 **Cách Đóng Góp:** Bán cá bằng `!banca` như bình thường. Nếu có cá yêu cầu trong hóa đơn → Tự động đóng góp cho Long Thần!\n⚠️ **Lưu ý:** Cá đóng góp sẽ KHÔNG được tính tiền."
        
        # Broadcast and Save Message ID
        message = await self._broadcast_message(start_message)
        if message:
            self.current_event["message_id"] = message.id
            
        # PERSIST STATE
        await set_global_state("active_global_event", self.current_event)

    async def end_current_event(self):
        """Ends the currently active event."""
        if not self.current_event: 
            return

        key = self.current_event["key"]
        data = self.current_event["data"]
        
        # Special Cleanup
        event_type = data.get("type", "passive")
        
        if event_type == "raid_boss":
            await self._finalize_raid(data)
        elif event_type == "fish_quest_raid":
            await self._finalize_dragon_quest(data)
        
        # Announce End (No Buttons)
        await self._broadcast_message(data.get("messages", {}).get("end"), attach_view=False)
        
        # Reset State
        self.last_event_times[key] = time.time()
        
        # Save Cooldowns to DB & CLEAR Active State
        await set_global_state("system_cooldowns", self.last_event_times)
        await set_global_state("active_global_event", None)
        await set_global_state("event_bump_message_ids", {})  # Clear message IDs
        
        self.current_event = None
        self.active_effects = {}
        self.raid_state["active"] = False
        self.dragon_state["active"] = False
        self.bump_message_ids = {}  # Clear RAM
        
        logger.info(f"[GLOBAL_EVENT] Ended: {key}")

    async def _broadcast_message(self, content, is_bump=False, attach_view=True):
        """Sends announcement to all configured fishing channels (Rich Embed)."""
        if not content: return
        
        try:
            # Detect Event Config for Styling
            visuals = {}
            if self.current_event:
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
            lines = content.split("\n", 1)
            description = content
                
            embed = discord.Embed(title=title, description=description, color=color)
            if image: embed.set_image(url=image)

            # Get Configured Channels
            rows = await db_manager.fetch(
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
                        
                        # Only attach view if explicitly requested AND event is active
                        if attach_view and self.current_event:
                            # Fix: Don't attach view to Start Message for Mini-Games (they spawn separate views)
                            # event_data contains the full event config (including type field)
                            event_data = self.current_event.get("data", {})
                            event_type = event_data.get("type")  # type is at root of event config
                            logger.info(f"[DEBUG] Event type for {self.current_event.get('key')}: '{event_type}'")
                            
                            
                            if event_type != "mini_game":
                                # event_data = full event config
                                # mechanics is in: event_config["data"]["mechanics"]
                                view_type = event_data.get("data", {}).get("mechanics", {}).get("view_type")
                                logger.info(f"[DEBUG] view_type extracted: '{view_type}'")
                                
                                if view_type:
                                    logger.info(f"[DEBUG] Attaching view {view_type} to start message")
                                    ViewClass = get_view_class(view_type)
                                    logger.info(f"[DEBUG] ViewClass resolved: {ViewClass}")
                                    
                                    if ViewClass:
                                        # Instantiate View
                                        if view_type == "TrashSellView":
                                            view = ViewClass(self)
                                        elif view_type == "MeteorWishView":
                                            view = ViewClass(self.bot.get_cog("FishingCog"))
                                        else:
                                            try:
                                                view = ViewClass(self)
                                                logger.info(f"[DEBUG] View instantiated successfully: {view}")
                                            except Exception as e:
                                                logger.error(f"[DEBUG] Failed to instantiate view {view_type}: {e}", exc_info=True)
                                else:
                                    logger.warning(f"[DEBUG] ViewClass is None for {view_type}")
                            else:
                                logger.warning(f"[DEBUG] No view_type found in mechanics for {self.current_event.get('key')}")
                        else:
                            logger.info(f"[DEBUG] Skipping view attachment for mini_game event")
                        
                        # Handle Deletion for Bump
                        if is_bump and channel_id in self.bump_message_ids:
                             old_id = self.bump_message_ids[channel_id]
                             try:
                                 old_msg = await channel.fetch_message(old_id)
                                 await old_msg.delete()
                             except Exception: pass

                        new_msg = await channel.send(embed=embed, view=view)
                        
                        # Always store message ID for View re-registration on restart
                        self.bump_message_ids[channel_id] = new_msg.id
                            
                except Exception as e:
                    logger.warning(f"Failed to send event msg to {channel_id}: {e}")
                    
            # Persist message IDs to DB for restart recovery
            if self.bump_message_ids:
                await set_global_state("event_bump_message_ids", self.bump_message_ids)
                logger.info(f"[BROADCAST] Saved {len(self.bump_message_ids)} message IDs to DB")
                
        except Exception as e:
            logger.error(f"Broadcast error: {e}")

    async def _process_bump(self):
        """Bumps the event message if configured."""
        event_data = self.current_event["data"]
        mechanics = event_data.get("mechanics", {})
        if not mechanics:
            mechanics = event_data.get("data", {}).get("mechanics", {})
            
        bump_interval = mechanics.get("bump_interval_seconds", 0)
        if bump_interval <= 0: return

        if time.time() - self.last_bump_time > bump_interval:
            self.last_bump_time = time.time()
            content = self.current_event["data"].get("messages", {}).get("start")
            await self._broadcast_message(content, is_bump=True)
            logger.info(f"[EVENT_BUMP] Bumped event {self.current_event['key']}")

    # ==================== RAID MECHANICS ====================

    async def _setup_raid(self, data):
        # 1. Try Load from DB
        saved_state = await get_global_state("cthulhu_raid")
        
        if saved_state and saved_state.get("active"):
             self.raid_state = saved_state
             # Fix: Convert String keys to Int for contributors (JSON Load artifact)
             if "contributors" in self.raid_state:
                 self.raid_state["contributors"] = {
                     int(k): v for k, v in self.raid_state["contributors"].items()
                 }
             logger.info(f"Raid Resumed from DB: HP {self.raid_state['hp_current']}/{self.raid_state['hp_max']}")
        else:
            # 2. Init New Raid
            self.raid_state = {
                "active": True,
                "hp_current": data["mechanics"]["hp_goal"], 
                "hp_max": data["mechanics"]["hp_goal"],
                "contributors": {},
                "start_time": time.time(),
                "message": None
            }
            # Save Initial State
            await set_global_state("cthulhu_raid", self.raid_state)
            logger.info(f"Raid Initialized: HP {self.raid_state['hp_max']}")
        
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
            
        # SAVE STATE TO DB (Atomic Persistence)
        await set_global_state("cthulhu_raid", self.raid_state)
            
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
                 from ..constants import RARE_FISH_KEYS, COMMON_FISH_KEYS
                 
                 for item in items_cfg:
                     key = item.get("key")
                     min_qty = item.get("min", 1)
                     max_qty = item.get("max", 1)
                     
                     # Check for random category type
                     if item.get("type") == "random_category":
                         category = item.get("category")
                         pool = []
                         if category == "rare":
                             pool = RARE_FISH_KEYS
                         elif category == "common":
                             pool = COMMON_FISH_KEYS
                             
                         if pool:
                             key = random.choice(pool)
                     
                     if not key: continue

                     qty = random.randint(min_qty, max_qty) * multiplier
                     if qty > 0:
                         # [CACHE] Use bot.inventory.modify
                         await self.bot.inventory.modify(uid, key, qty)
                         # Try to resolve name from ALL_FISH/items if possible
                         name = key
                         from ..constants import ALL_FISH
                         if key in ALL_FISH:
                              name = ALL_FISH[key].get("name", key)
                              
                         added_text.append(f"{qty} {name}")
                 return ", ".join(added_text)

             # AWARD MVP (Top 1)
             if len(top_users) >= 1:
                 user_id, dmg = top_users[0]
                 # Achievement
                 try:
                     await self.bot.achievement_manager.check_unlock(user_id, "fishing", "god_slayer", 1, None)
                 except Exception: pass
                 
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
                  summary_text += "📉 **THỊ TRƯỜNG SỤP ĐỔ!** Giá cá giảm 50% trong 1h tới."
                  # Logic to apply global debuff state? 
                  # Currently system relies on active events. 
                  # Ideally we set a "lingering_effect" flag in DB or Manager.
                  # For now just text.
                  
             # Consolation (not in JSON but kept for UX)
             for user_id, _ in sorted_users:
                 await add_seeds(user_id, 100, reason="raid_consolation", category="raid")
             summary_text += "\n🩹 **Quà an ủi:** 100 Hạt cho mỗi người tham gia."

        # Clear DB Persistence regardless of outcome
        await set_global_state("cthulhu_raid", {"active": False})

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
        
        damage_info = (
            "🐟 **Cá Thường:** 5-9 Sát Thương\n"
            "⭐ **Cá Hiếm:** 35-500 Sát Thương\n"
            "💎 **Cá Huyền Thoại:** Nhiều hơn nữa!"
        )
        embed.add_field(name="📊 Đóng Góp Theo Cá", value=damage_info, inline=True)
        
        rewards_info = (
            "🥇 **MVP:** 5,000 Hạt + Huy Hiệu\n"
            "🥈 **Top 2:** 3,000 Hạt\n"
            "🥉 **Top 3:** 1,500 Hạt\n"
            "👥 **Tham gia:** 500 Hạt"
        )
        embed.add_field(name="🎁 Phần Thưởng", value=rewards_info, inline=True)
            
        if self.current_event and self.current_event.get("end_time"):
            end_ts = int(self.current_event["end_time"])
            embed.description += f"\n⏳ **Kết thúc:** <t:{end_ts}:R>"

        # Use native Discord timestamp for footer
        embed.timestamp = datetime.now()
        embed.set_footer(text="Cập nhật trạng thái")
            
        # 3. Broadcast with Delete-Old-And-Send-New pattern
        await self._broadcast_raid_update(embed)

    async def _broadcast_raid_update(self, embed):
        """Sends new status message and deletes the old one to prevent spam."""
        try:
            rows = await db_manager.fetch("SELECT fishing_channel_id FROM server_config WHERE fishing_channel_id IS NOT NULL")
            
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

    async def _update_dragon_status(self):
        """Updates the dragon quest status embed in channels (throttled)."""
        if not self.dragon_state.get("active"):
            return
        
        # Throttle Updates (Max once every 60s)
        now = time.time()
        last_update = self.dragon_state.get("last_update", 0)
        if now - last_update < 60:
            return
        self.dragon_state["last_update"] = now
        
        # Call broadcast method
        await self._broadcast_dragon_status()


    # ==================== DRAGON FISH QUEST MECHANICS ====================

    async def _setup_dragon_quest(self, data):
        """Initialize dragon fish collection quest with random fish selection."""
        # 1. Try Load from DB
        saved_state = await get_global_state("dragon_quest")
        
        # Validate saved state is not stale (older than 2 hours = likely from previous event)
        is_stale = False
        if saved_state and saved_state.get("active"):
            saved_start_time = saved_state.get("start_time", 0)
            time_diff = time.time() - saved_start_time
            if time_diff > 7200:  # 2 hours
                is_stale = True
                logger.info(f"Dragon Quest saved state is stale (age: {time_diff/60:.1f} minutes). Creating new quest.")
        
        if saved_state and saved_state.get("active") and not is_stale:
            self.dragon_state = saved_state
            logger.info(f"Dragon Quest Resumed: {self.dragon_state['quantity_current']}/{self.dragon_state['quantity_goal']} {self.dragon_state['requested_fish_name']}")
        else:
            # 2. Init New Quest - Random Fish Selection
            mechanics = data["mechanics"]
            fish_pools = mechanics["fish_pools"]
            quantity_ranges = mechanics["quantity_ranges"]
            
            # Randomly select fish category
            category = random.choice(["rare", "common"])
            pool = fish_pools[category]
            selected_fish_key = random.choice(pool)
            
            # Determine quantity based on category
            qty_range = quantity_ranges[category]
            quantity_goal = random.randint(qty_range["min"], qty_range["max"])
            
            # Get fish display name
            from ..constants import ALL_FISH
            fish_name = ALL_FISH.get(selected_fish_key, {}).get("name", selected_fish_key)
            
            self.dragon_state = {
                "active": True,
                "requested_fish_key": selected_fish_key,
                "requested_fish_name": fish_name,
                "quantity_goal": quantity_goal,
                "quantity_current": quantity_goal,  # Count down to 0
                "contributors": {},
                "start_time": time.time(),
                "message_ids": {}
            }
            
            await set_global_state("dragon_quest", self.dragon_state)
            logger.info(f"Dragon Quest Initialized: Need {quantity_goal} x {fish_name} ({selected_fish_key})")
    
    async def process_dragon_contribution(self, user_id, fish_dict):
        """Process fish contribution when user sells fish.
        
        Args:
            user_id: Discord user ID
            fish_dict: Dict of fish being sold {fish_key: quantity}
            
        Returns:
            tuple: (contributed_quantity, fish_value_to_deduct)
        """
        if not self.dragon_state.get("active"):
            return 0, 0
        
        requested_key = self.dragon_state["requested_fish_key"]
        
        # Check if user has the requested fish
        if requested_key not in fish_dict:
            return 0, 0
        
        available = fish_dict[requested_key]
        needed = self.dragon_state["quantity_current"]
        
        # Calculate contribution (take min of available and needed)
        contribution = min(available, needed)
        
        if contribution <= 0:
            return 0, 0
        
        # Update state
        current = self.dragon_state["contributors"].get(user_id, 0)
        self.dragon_state["contributors"][user_id] = current + contribution
        self.dragon_state["quantity_current"] -= contribution
        
        if self.dragon_state["quantity_current"] < 0:
            self.dragon_state["quantity_current"] = 0
        
        # Save to DB
        await set_global_state("dragon_quest", self.dragon_state)
        
        # Calculate money value to deduct (user doesn't get paid for contributed fish)
        # Need fish sell prices from constants
        from ..constants import ALL_FISH
        fish_data = ALL_FISH.get(requested_key, {})
        fish_price = fish_data.get("sell_price", 0)
        value_to_deduct = contribution * fish_price
        
        logger.info(f"[DRAGON_QUEST] User {user_id} contributed {contribution} {requested_key}. Remaining: {self.dragon_state['quantity_current']}")
        
        return contribution, value_to_deduct
    
    async def _broadcast_dragon_status(self):
        """Update dragon quest status in all channels."""
        if not self.dragon_state.get("active"):
            return
        
        # Calculate progress
        goal = self.dragon_state["quantity_goal"]
        current = self.dragon_state["quantity_current"]
        collected = goal - current
        percent = (collected / goal) * 100
        
        # Progress bar
        bar_len = 20
        filled = int((collected / goal) * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        
        embed = discord.Embed(
            title="🐲 NHIỆM VỤ LONG THẦN",
            description=f"**Yêu Cầu:** {self.dragon_state['quantity_goal']} x {self.dragon_state['requested_fish_name']}",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Tiến Độ",
            value=f"`[{bar}]` {percent:.1f}%\n**{collected}/{goal}** đã thu thập",
            inline=False
        )
        
        # Top contributors
        if self.dragon_state["contributors"]:
            sorted_contrib = sorted(
                self.dragon_state["contributors"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            leaderboard = ""
            medals = ["🥇", "🥈", "🥉"]
            for i, (uid, qty) in enumerate(sorted_contrib):
                leaderboard += f"{medals[i]} <@{uid}>: **{qty}** cá\\n"
            
            embed.add_field(name="🏆 Top Đóng Góp", value=leaderboard, inline=False)
        
        embed.set_footer(text="💡 Bán cá bằng /banca để tự động đóng góp!")
        
        # Broadcast
        try:
            rows = await db_manager.fetch(
                "SELECT fishing_channel_id FROM server_config WHERE fishing_channel_id IS NOT NULL"
            )
            if not rows:
                return
            
            for (cid,) in rows:
                try:
                    ch = self.bot.get_channel(cid)
                    if not ch:
                        continue
                    
                    # Delete old message
                    old_msg_id = self.dragon_state["message_ids"].get(cid)
                    if old_msg_id:
                        try:
                            old_msg = await ch.fetch_message(old_msg_id)
                            await old_msg.delete()
                        except Exception:
                            pass
                    
                    # Send new message
                    new_msg = await ch.send(embed=embed)
                    self.dragon_state["message_ids"][cid] = new_msg.id
                    
                except Exception as e:
                    logger.warning(f"Failed to update dragon status in {cid}: {e}")
        except Exception as e:
            logger.error(f"Dragon broadcast error: {e}")
    
    async def _finalize_dragon_quest(self, data):
        """Reward contributors and announce results."""
        if not self.dragon_state.get("active"):
            return
        
        success = self.dragon_state["quantity_current"] == 0
        contributors = self.dragon_state["contributors"]
        
        if not contributors:
            logger.info("Dragon Quest ended with no contributors")
            await set_global_state("dragon_quest", {"active": False})
            return
        
        # Sort contributors
        sorted_users = sorted(contributors.items(), key=lambda x: x[1], reverse=True)
        top_users = sorted_users[:3]
        
        summary_text = ""
        
        if success:
            # Success rewards
            rewards_config = data.get("rewards", {}).get("success", {})
            base_items = rewards_config.get("items", [])
            mvp_items = rewards_config.get("mvp_bonus", [])
            
            summary_text = f"🎉 **THÀNH CÔNG!** Long Thần đã nhận đủ {self.dragon_state['quantity_goal']} {self.dragon_state['requested_fish_name']}!\\n\\n"
            
            # Helper to give rewards
            async def give_quest_rewards(uid, items_cfg, multiplier=1):
                added_text = []
                for item in items_cfg:
                    key = item.get("key")
                    if not key:
                        continue
                    
                    # Check if it's seeds or item
                    if key == "seeds":
                        amount = item.get("amount", 0)
                        await add_seeds(uid, amount, reason="dragon_quest_reward", category="event")
                        added_text.append(f"{amount} Hạt")
                    else:
                        min_qty = item.get("min", 1)
                        max_qty = item.get("max", 1)
                        qty = random.randint(min_qty, max_qty) * multiplier
                        # [CACHE] Use bot.inventory.modify
                        await self.bot.inventory.modify(uid, key, qty)
                        added_text.append(f"{qty} {key}")
                
                return ", ".join(added_text)
            
            # MVP (Top 1)
            if len(top_users) >= 1:
                user_id, qty = top_users[0]
                base_txt = await give_quest_rewards(user_id, base_items)
                mvp_txt = await give_quest_rewards(user_id, mvp_items)
                summary_text += f"🥇 <@{user_id}>: **{qty} cá**\\n🎁 Nhận: {base_txt}, {mvp_txt}\\n"
            
            # Others get base rewards
            count_others = 0
            for user_id, qty in sorted_users:
                if user_id not in [u[0] for u in top_users]:
                    await give_quest_rewards(user_id, base_items)
                    count_others += 1
                elif any(u[0] == user_id for u in top_users[1:]):
                    rank = "🥈" if user_id == top_users[1][0] else "🥉"
                    base_txt = await give_quest_rewards(user_id, base_items)
                    summary_text += f"{rank} <@{user_id}>: **{qty} cá** - Nhận: {base_txt}\\n"
            
            if count_others > 0:
                summary_text += f"\\n✨ **Và {count_others} người khác** đã nhận quà tham gia!"
        
        else:
            # No penalty for failure (user's choice: Option A)
            collected = self.dragon_state["quantity_goal"] - self.dragon_state["quantity_current"]
            summary_text = f"⏰ **Hết Giờ!** Long Thần đã bay đi...\\n\\n"
            summary_text += f"📊 Đã thu thập: **{collected}/{self.dragon_state['quantity_goal']}** {self.dragon_state['requested_fish_name']}\\n"
            summary_text += f"\\n💭 *Lần sau sẽ cố gắng hơn!*"
        
        # Clear DB
        await set_global_state("dragon_quest", {"active": False})
        
        # Send summary
        embed = discord.Embed(
            title="🐲 KẾT QUẢ NHIỆM VỤ LONG THẦN",
            description=summary_text,
            color=discord.Color.gold() if success else discord.Color.light_grey()
        )
        
        if success:
            embed.set_footer(text="🎊 Cảm ơn tất cả mọi người đã đóng góp!")
        
        try:
            rows = await db_manager.fetch(
                "SELECT fishing_channel_id FROM server_config WHERE fishing_channel_id IS NOT NULL"
            )
            for (cid,) in rows:
                ch = self.bot.get_channel(cid)
                if ch:
                    await ch.send(embed=embed)
        except Exception as e:
            logger.error(f"Dragon finalize broadcast error: {e}")


    async def _process_mini_game(self):
        """Handles periodic spawning of mini-games (e.g. Meteor Shower)."""
        now = time.time()
        
        # Initialize delay if first run
        if self.next_minigame_spawn_delay == 0:
            spawn_config = self.current_event.get("data", {}).get("mechanics", {}).get("spawn_interval", [60, 180])
            
            if isinstance(spawn_config, int):
                self.next_minigame_spawn_delay = spawn_config
            else:
                self.next_minigame_spawn_delay = random.randint(spawn_config[0], spawn_config[1])
            self.last_minigame_spawn = now
            return

        if now >= self.last_minigame_spawn + self.next_minigame_spawn_delay:
            # SPAWN IT
            view_class_name = self.current_event["data"].get("mechanics", {}).get("view_type")
            if not view_class_name:
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
                rows = await db_manager.fetch(
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


from typing import Optional, List, Dict
from core.database import db_manager
from core.logger import setup_logger

logger = setup_logger("AquariumHousing", "logs/aquarium.log")

class HousingManager:
    """Business logic for Housing System (Project Aquarium)."""

    @staticmethod
    async def has_house(user_id: int) -> bool:
        """Check if user already has a house (thread)."""
        rows = await db_manager.execute(
            "SELECT home_thread_id FROM users WHERE user_id = ?", 
            (user_id,)
        )
        return bool(rows and rows[0][0])

    @staticmethod
    async def get_home_thread_id(user_id: int) -> Optional[int]:
        """Get the Discord Thread ID of the user's home."""
        rows = await db_manager.execute(
            "SELECT home_thread_id FROM users WHERE user_id = ?",
            (user_id,)
        )
        return rows[0][0] if rows and rows[0][0] else None

    @staticmethod
    async def get_house_owner(thread_id: int) -> Optional[int]:
        """Get the User ID who owns the house (thread)."""
        rows = await db_manager.execute(
            "SELECT user_id FROM user_house WHERE thread_id = ?",
            (thread_id,)
        )
        return rows[0][0] if rows else None

    @staticmethod
    async def register_house(user_id: int, thread_id: int) -> bool:
        """
        Register a new house in the database.
        1. Update users.home_thread_id
        2. Initialize 5 empty slots in home_slots
        3. Create user_house record
        """
        try:
            operations = []
            
            # 1. Update User
            operations.append((
                "UPDATE users SET home_thread_id = ? WHERE user_id = ?",
                (thread_id, user_id)
            ))
            
            # 2. Update User House Table
            operations.append((
                "INSERT OR IGNORE INTO user_house (user_id, thread_id, house_level, slots_unlocked) VALUES (?, ?, 1, 5)",
                (user_id, thread_id)
            ))

            # 3. Init Default Slots (0-4)
            for i in range(5):
                operations.append((
                    "INSERT OR IGNORE INTO home_slots (user_id, slot_index, item_id) VALUES (?, ?, NULL)",
                    (user_id, i)
                ))
            
            await db_manager.batch_modify(operations)
            
            logger.info(f"[HOUSE_CREATE] Registed house for User {user_id}, Thread {thread_id}")
            return True
        except Exception as e:
            logger.error(f"[HOUSE_REGISTER_ERROR] User {user_id}: {e}", exc_info=True)
            return False

    @staticmethod
    async def get_slots(user_id: int) -> List[Optional[str]]:
        """Get list of item_ids in slots 0-4."""
        rows = await db_manager.execute(
            "SELECT slot_index, item_id FROM home_slots WHERE user_id = ? ORDER BY slot_index ASC",
            (user_id,)
        )
            
        # Default 5 None
        slots = [None] * 5
        for idx, item in rows:
            if idx < 5: # Limit just in case
                slots[idx] = item
        return slots

    @staticmethod
    async def get_inventory(user_id: int) -> Dict[str, int]:
        """Get user's available decor inventory."""
        rows = await db_manager.execute(
            "SELECT item_id, quantity FROM user_decor WHERE user_id = ? AND quantity > 0",
            (user_id,)
        )
        return {row[0]: row[1] for row in rows}

    @staticmethod
    async def update_slot(user_id: int, slot_index: int, new_item_id: Optional[str]) -> tuple[bool, str]:
        """
        Update a decor slot. Handles Inventory management correctly.
        Returns: (Success, Message)
        """
        try:
            # 1. Get current item in this slot
            current_rows = await db_manager.execute(
                "SELECT item_id FROM home_slots WHERE user_id = ? AND slot_index = ?",
                (user_id, slot_index)
            )
            old_item_id = current_rows[0][0] if current_rows and current_rows[0][0] else None

            # Nothing changed?
            if old_item_id == new_item_id:
                return True, "Không có thay đổi."

            operations = []

            # 2. Logic: Return OLD item to inventory (if any)
            if old_item_id:
                operations.append((
                    """
                    INSERT INTO user_decor (user_id, item_id, quantity) 
                    VALUES (?, ?, 1)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + 1
                    """,
                    (user_id, old_item_id)
                ))

            # 3. Logic: Take NEW item from inventory (if any)
            if new_item_id:
                operations.append((
                    "UPDATE user_decor SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?",
                    (user_id, new_item_id)
                ))
            
            # 4. Update Slot
            operations.append((
                "UPDATE home_slots SET item_id = ? WHERE user_id = ? AND slot_index = ?",
                (new_item_id, user_id, slot_index)
            ))
            
            # 5. Cleanup: Remove 0 quantity rows to keep DB clean
            operations.append((
                "DELETE FROM user_decor WHERE user_id = ? AND quantity <= 0",
                (user_id,)
            ))

            await db_manager.batch_modify(operations)
            logger.info(f"[HOUSE_UPDATE] User {user_id} Slot {slot_index}: {old_item_id} -> {new_item_id}")
            return True, "Cập nhật thành công."

        except Exception as e:
            import traceback
            traceback.print_exc() # Print to console for debugging
            logger.error(f"[HOUSE_UPDATE_ERROR] User {user_id}: {e}", exc_info=True)
            return False, f"Lỗi hệ thống: {e}"

    @staticmethod
    async def get_dashboard_message_id(user_id: int) -> Optional[int]:
        """Get the ID of the floating dashboard message."""
        try:
            rows = await db_manager.execute(
                "SELECT dashboard_message_id FROM user_house WHERE user_id = ?",
                (user_id,)
            )
            return rows[0][0] if rows and rows[0][0] else None
        except Exception:
            return None

    @staticmethod
    async def set_dashboard_message_id(user_id: int, message_id: int):
        """Update the ID of the floating dashboard message."""
        await db_manager.execute(
            "UPDATE user_house SET dashboard_message_id = ? WHERE user_id = ?",
            (message_id, user_id)
        )

    @staticmethod
    async def get_active_sets(user_id: int) -> List[Dict]:
        """Check which Feng Shui sets are active for the user."""
        from ..constants import FENG_SHUI_SETS
        
        slots = await HousingManager.get_slots(user_id)
        # Convert slots to set of item_ids for O(1) lookup
        placed_items = set(item for item in slots if item)
        
        active_sets = []
        for set_key, set_data in FENG_SHUI_SETS.items():
            required = set(set_data.get("required", []))
            if required.issubset(placed_items):
                active_sets.append(set_data)
                
        return active_sets

    @staticmethod
    async def calculate_home_stats(user_id: int) -> Dict:
        """Calculate total value and charm of the house based on placed items."""
        from ..constants import DECOR_ITEMS
        
        slots = await HousingManager.get_slots(user_id)
        active_sets = await HousingManager.get_active_sets(user_id)
        
        total_charm = 0
        total_value = 0 # Sum of leaf_price or seed_price? "Giá trị hồ" -> Maybe Sell Value? Or Display Value. Let's use Leaf Value for now as "Asset".
        
        for item_id in slots:
            if item_id and item_id in DECOR_ITEMS:
                item = DECOR_ITEMS[item_id]
                # Parse Charm from description? Or should we add charm field to constants?
                # Description format: "... (+50 Charm)"
                # Regex or simple string split.
                desc = item.get('desc', '')
                if "(+" in desc and "Charm)" in desc:
                    try:
                        charm_part = desc.split("(+")[1].split(" Charm)")[0]
                        total_charm += int(charm_part)
                    except:
                        pass
                
                total_value += item.get('price_leaf', 0)
        
        return {
            "charm": total_charm,
            "value": total_value,
            "sets": active_sets
        }

    @staticmethod
    async def refresh_dashboard(user_id: int, bot) -> bool:
        """
        Smart Bump Logic:
        - If last message in thread IS dashboard -> Edit it.
        - If dashboard is old/buried -> Delete and Resend.
        """
        try:
            from ..ui.render import render_engine # Lazy import to avoid circular dep if any
            from ..ui.embeds import create_aquarium_dashboard
            import discord

            thread_id = await HousingManager.get_home_thread_id(user_id)
            if not thread_id: return False

            # Get Thread Object
            # We need a way to get the thread. If we have 'bot', we can fetch channel.
            # But fetching by ID globally is hard without guild.
            # We can find guild from user_house? No guild_id in user_house?
            # Actually we assume bot can fetch channel directly by ID or cache.
            thread = bot.get_channel(thread_id)
            if not thread:
                try:
                    thread = await bot.fetch_channel(thread_id)
                except:
                    return False

            # Generate Content
            slots = await HousingManager.get_slots(user_id)
            inventory = await HousingManager.get_inventory(user_id)
            
            # Use unified stats & embed
            stats = await HousingManager.calculate_home_stats(user_id)
            visuals = render_engine.generate_view(slots)
            
            # Fetch User for fancy embed (Name/Avatar)
            try:
                user = bot.get_user(user_id) or await bot.fetch_user(user_id)
                user_name = user.display_name
                user_avatar = user.display_avatar.url
            except:
                user_name = thread.name.replace('Nhà của ', '')
                user_avatar = None

            embed = create_aquarium_dashboard(
                user_name=user_name,
                user_avatar=user_avatar,
                view_visuals=visuals,
                stats=stats,
                inventory_count=len(inventory)
            )

            # Check Last Message (Smart Adoption Logic)
            last_message = None
            try:
                # History is an async iterator
                async for msg in thread.history(limit=1):
                    last_message = msg
            except:
                pass

            old_dashboard_id = await HousingManager.get_dashboard_message_id(user_id)
            
            # Scenario 0: ADOPTION - DB is empty but last message IS dashboard (from restart/manual send)
            if not old_dashboard_id and last_message and last_message.author.id == bot.user.id:
                 # Check if it looks like a dashboard
                 if last_message.embeds and "Nhà của" in (last_message.embeds[0].title or ""):
                     old_dashboard_id = last_message.id
                     await HousingManager.set_dashboard_message_id(user_id, old_dashboard_id)
                     logger.info(f"[DASHBOARD] Adopted orphan message {old_dashboard_id} for user {user_id}")

            # Scenario 1: Dashboard is already the latest message
            if old_dashboard_id and last_message and last_message.id == old_dashboard_id:
                try:
                    msg = last_message # Optimization: use already fetched msg
                    await msg.edit(embed=embed)
                    return True
                except discord.NotFound:
                    pass # Message deleted, send new

            # Scenario 2: Dashboard is old or missing -> Scroll Bump
            # Delete old one if exists to keep chat clean? 
            # User wants "Dashboard at bottom". If we leave old ones, it spams.
            # So yes, delete old one.
            if old_dashboard_id:
                try:
                    old_msg = await thread.fetch_message(old_dashboard_id)
                    await old_msg.delete()
                except:
                    pass

            # Send New
            new_msg = await thread.send(embed=embed)
            await HousingManager.set_dashboard_message_id(user_id, new_msg.id)
            return True

        except Exception as e:
            logger.error(f"[DASHBOARD_REFRESH] Error: {e}")
            return False

    @staticmethod
    async def visit_home(visitor_id: int, host_id: int) -> Dict:
        """
        Process a home visit.
        Returns Dict with: success, message, rewards (list of str), stats (visitors_count)
        """
        import datetime
        import random
        from ..constants import TRASH_ITEM_IDS
        
        try:
            today_str = datetime.date.today().isoformat()
            
            # 1. Check Self Visit
            if visitor_id == host_id:
                return {"success": False, "message": "Bạn không thể tự thăm nhà mình để nhận quà (Nhưng có thể ngắm thoải mái)."}

            # 2. Check Daily Limit (5 visits/day)
            # Count distinct hosts visited today
            rows_count = await db_manager.execute(
                "SELECT COUNT(DISTINCT host_id) FROM home_visits WHERE visitor_id = ? AND date(visited_at) = ?",
                (visitor_id, today_str)
            )
            daily_visits = rows_count[0][0]
            if daily_visits >= 5:
                # Check if this specific host was already visited (allow re-visit but no reward?)
                # User said "5 nhà KHÁC NHÂU".
                # Design spec says limit 5 rewards.
                # If over limit, just allow visiting without reward.
                pass 
            
            # 3. Check if already visited THIS host today
            rows_exist = await db_manager.execute(
                "SELECT 1 FROM home_visits WHERE visitor_id = ? AND host_id = ? AND date(visited_at) = ?",
                (visitor_id, host_id, today_str)
            )
            already_visited = bool(rows_exist and rows_exist[0])
            
            reward_items = []
            
            # 4. Processing
            if not already_visited and daily_visits < 5:
                # Valid for reward!
                
                # A. Host Reward: +1 Charm
                await db_manager.execute(
                    "UPDATE users SET charm_point = charm_point + 1 WHERE user_id = ?",
                    (host_id,)
                )
                
                # B. Visitor Reward: 20% Chance
                if random.random() < 0.20:
                    # Roll Table
                    roll = random.random()
                    if roll < 0.05: # 5% of 20% = 1% total -> Leaf Coin
                         await db_manager.execute(
                            "UPDATE users SET leaf_coin = leaf_coin + 1 WHERE user_id = ?",
                            (visitor_id,)
                         )
                         reward_items.append("1 Xu Lá 🍀 (Hiếm!)")
                    else:
                        # Trash or Bait
                        # Simple: Give 1 random trash
                        trash_id = random.choice(TRASH_ITEM_IDS)
                        
                        # Trash/Bait are in 'inventory' table (misc items).
                        await db_manager.execute(
                            """
                            INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, 1)
                            ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + 1
                            """,
                            (visitor_id, trash_id)
                        )
                        reward_items.append(f"1 {trash_id} 🗑️")

                # C. Log Visit
                await db_manager.execute(
                    "INSERT INTO home_visits (visitor_id, host_id) VALUES (?, ?)",
                    (visitor_id, host_id)
                )
                
                msg = "Ghé thăm thành công! Chủ nhà nhận được +1 Charm."
                if reward_items:
                    msg += f"\n🎁 Bạn nhặt được: {', '.join(reward_items)}"
            else:
                msg = "Ghé thăm lại (Không nhận quà hôm nay nữa)."
                if daily_visits >= 5:
                    msg = "Bạn đã hết lượt nhận quà thăm nhà hôm nay (5/5)."

            return {"success": True, "message": msg, "rewards": reward_items}

        except Exception as e:
            logger.error(f"[VISIT_ERROR] {e}", exc_info=True)
            return {"success": False, "message": "Lỗi khi ghé thăm."}

housing_manager = HousingManager()

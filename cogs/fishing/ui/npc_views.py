"""Interactive View classes for NPC encounters."""

import discord
import random
import asyncio
from typing import Dict, Any, List

from database_manager import db_manager, increment_stat, get_stat
from core.logger import setup_logger

logger = setup_logger("NPCViews", "cogs/fishing/fishing.log")


RARE_FISH_POOL = [
    "ca_koi", "ca_he", "ca_hoi", "ca_thien_than", "ca_dia_canh", 
    "ca_ngua", "ca_tam", "betta_rong", "ca_la_han", "ca_hong_ket", 
    "tom_hum_bong", "tom_alaska", "cua_hoang_de"
]


class InteractiveNPCView(discord.ui.View):
    
    def __init__(
        self, 
        cog, 
        user_id: int, 
        npc_key: str,
        npc_data: Dict[str, Any],
        caught_fish: Dict[str, Any],
        ctx_or_interaction
    ):
        super().__init__(timeout=30)
        
        self.cog = cog
        self.user_id = user_id
        self.npc_key = npc_key
        self.npc_data = npc_data
        self.caught_fish = caught_fish
        self.ctx = ctx_or_interaction
        self.completed = False
        self.value = None
        
        self._setup_buttons()
    
    def _setup_buttons(self):
        agree_btn = discord.ui.Button(
            label="Đồng Ý",
            style=discord.ButtonStyle.green,
            emoji="✅",
            custom_id="agree"
        )
        agree_btn.callback = self.agree_callback
        self.add_item(agree_btn)
        
        decline_btn = discord.ui.Button(
            label="Từ Chối",
            style=discord.ButtonStyle.red,
            emoji="❌",
            custom_id="decline"
        )
        decline_btn.callback = self.decline_callback
        self.add_item(decline_btn)

    async def agree_callback(self, interaction: discord.Interaction):
        await self._handle_choice(interaction, "agree")

    async def decline_callback(self, interaction: discord.Interaction):
        await self._handle_choice(interaction, "decline")

    async def _handle_choice(self, interaction: discord.Interaction, choice: str):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Không phải chuyện của bạn!", ephemeral=True)
            
        if self.completed:
            return await interaction.response.send_message("❌ Đã chọn rồi!", ephemeral=True)
            
        self.completed = True
        self.value = choice
        
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        
        if choice == "agree":
            await self._process_agreement(interaction)
        else:
            await self._process_decline(interaction)

    async def _process_agreement(self, interaction: discord.Interaction):
        cost_type = self.npc_data.get("cost")
        
        try:
            try:
                async with asyncio.timeout(10.0):
                    async with db_manager.transaction() as conn:
                        if cost_type == "fish":
                            fish_key = list(self.caught_fish.keys())[0]
                            row = await conn.fetchrow(
                                "SELECT quantity FROM inventory WHERE user_id = $1 AND item_id = $2",
                                self.user_id, fish_key
                            )
                            
                            if not row or row['quantity'] < 1:
                                raise ValueError("Cá đã bốc hơi đâu mất rồi!")
                                
                            await conn.execute(
                                "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = $1 AND item_id = $2",
                                self.user_id, fish_key
                            )
                            
                        elif isinstance(cost_type, int):
                            row = await conn.fetchrow(
                                "SELECT seeds FROM users WHERE user_id = $1", self.user_id
                            )

                            if not row or row['seeds'] < cost_type:
                                raise ValueError(f"Không đủ tiền! Cần {cost_type} Hạt.")
                                
                            await conn.execute(
                                "UPDATE users SET seeds = seeds - $1 WHERE user_id = $2",
                                cost_type, self.user_id
                            )
                            await conn.execute(
                                "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                                self.user_id, -cost_type, f"npc_cost_{self.npc_key}", "fishing"
                            )

                        reward_pool = self.npc_data.get("rewards", {}).get("accept", [])
                        result = self._roll_outcome(reward_pool)
                        
                        msg_extra = await self._apply_outcome(result, conn)
                        
            except asyncio.TimeoutError:
                await interaction.followup.send("⚠️ Hệ thống đang bận. Mèo không thể xử lý yêu cầu!", ephemeral=True)
                return
                
            embed = discord.Embed(
                title=f"{self.npc_data['name']} - Kết Quả",
                description=result.get("message", "Giao dịch thành công!").replace("{amount}", msg_extra if 'msg_extra' in locals() else ""),
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            
            if result.get("type") in ["nothing", "cursed", "rock"]:
                await increment_stat(self.user_id, "fishing", "scam_events", 1)
                
            if self.npc_key == "gemstone_gambler" and result.get("type") in ["nothing", "worm"]:
                await increment_stat(self.user_id, "fishing", "gemstone_gambler_fails", 1)

            await increment_stat(self.user_id, "npc_affinity", self.npc_key, 1)
            logger.info(f"[NPC_AFFINITY] User {self.user_id} increased affinity with {self.npc_key} (+1)")

        except ValueError as ve:
            await interaction.followup.send(f"❌ {ve}", ephemeral=True)
        except Exception as e:
            logger.error(f"[NPC_ERROR] {e}", exc_info=True)
            await interaction.followup.send("❌ Lỗi hệ thống! Mèo đã ăn mất code.", ephemeral=True)

    async def _apply_outcome(self, result: dict, conn) -> str:
        msg_extra = ""
        reward_type = result.get("type")
        
        if reward_type == "money":
            amt = result.get("amount", 0)
            msg_extra = f"\n💰 **Tiền Nhận:** {amt} Hạt"
            await conn.execute(
                "UPDATE users SET seeds = seeds + $1 WHERE user_id = $2",
                amt, self.user_id
            )
            await conn.execute(
                "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                self.user_id, amt, f"npc_reward_{self.npc_key}_money", "fishing"
            )
        
        elif reward_type == "triple_money":
            if not self.caught_fish:
                base_price = 100
            else:
                f_info = list(self.caught_fish.values())[0]
                base_price = f_info.get("sell_price", 0)
            
            multiplier = result.get("multiplier", 3)
            total_val = base_price * multiplier
            msg_extra = f"\n💰 **Tiền Nhận:** {total_val} Hạt (x{multiplier})"
            
            await conn.execute(
                "UPDATE users SET seeds = seeds + $1 WHERE user_id = $2",
                total_val, self.user_id
            )
            await conn.execute(
                "INSERT INTO transaction_logs (user_id, amount, reason, category) VALUES ($1, $2, $3, $4)",
                self.user_id, total_val, f"npc_reward_{self.npc_key}_triple", "fishing"
            )
        
        elif reward_type == "ngoc_trai":
            amt = result.get("amount", 1)
            msg_extra = f"\n⚪ **Nhận:** {amt} Ngọc Trai"
            await conn.execute("""
                INSERT INTO inventory (user_id, item_id, quantity) 
                VALUES ($1, 'ngoc_trai', $2)
                ON CONFLICT(user_id, item_id) 
                DO UPDATE SET quantity = inventory.quantity + excluded.quantity
            """, self.user_id, amt)
        
        elif reward_type == "worm":
            amt = result.get("amount", 0)
            msg_extra = f"\n🪱 **Nhận:** {amt} Mồi Câu"
            await conn.execute("""
                INSERT INTO inventory (user_id, item_id, quantity) 
                VALUES ($1, 'moicau', $2)
                ON CONFLICT(user_id, item_id) 
                DO UPDATE SET quantity = inventory.quantity + excluded.quantity
            """, self.user_id, amt)
            
        elif reward_type == "vat_lieu_nang_cap":
            amt = result.get("amount", 1)
            msg_extra = f"\n⚙️ **Nhận:** {amt} Vật Liệu"
            await conn.execute("""
                INSERT INTO inventory (user_id, item_id, quantity) 
                VALUES ($1, 'vat_lieu_nang_cap', $2)
                ON CONFLICT(user_id, item_id) 
                DO UPDATE SET quantity = inventory.quantity + excluded.quantity
            """, self.user_id, amt)
            
        elif reward_type == "chest":
            amt = result.get("amount", 1)
            msg_extra = f"\n🎁 **Nhận:** {amt} Rương Kho Báu"
            await conn.execute("""
                INSERT INTO inventory (user_id, item_id, quantity) 
                VALUES ($1, 'ruong_kho_bau', $2)
                ON CONFLICT(user_id, item_id) 
                DO UPDATE SET quantity = inventory.quantity + excluded.quantity
            """, self.user_id, amt)

        if reward_type == "rod_durability":
            change = result.get("amount", 0)
            from ..mechanics.rod_system import get_rod_data, update_rod_data
            _, cur_dur = await get_rod_data(self.user_id)
            await update_rod_data(self.user_id, cur_dur + change)
            sign = "+" if change > 0 else ""
            msg_extra = f"\n🎣 **Độ Bền:** {sign}{change} điểm"
            
        elif reward_type == "cursed":
            change = result.get("amount", 0)
            from ..mechanics.rod_system import get_rod_data, update_rod_data
            _, cur_dur = await get_rod_data(self.user_id)
            await update_rod_data(self.user_id, max(0, cur_dur - change))
            msg_extra = f"\n📉 **Độ Bền:** -{change} điểm"
                
        elif reward_type == "lucky_buff":
            duration = result.get("duration", 10)
            await self.cog.emotional_state_manager.apply_emotional_state(
                self.user_id, "lucky", duration
            )
            msg_extra = f"\n🍀 **May Mắn:** +{duration} lượt"
            
        elif reward_type == "legendary_buff":
            duration = result.get("duration", 10)
            await self.cog.emotional_state_manager.apply_emotional_state(
                self.user_id, "legendary", duration
            )
            msg_extra = f"\n✨ **Buff Huyền Thoại:** +{duration} lượt"
            
        elif reward_type == "random_rare_fish":
            fish_key = random.choice(RARE_FISH_POOL)
            await conn.execute("""
                INSERT INTO fish_collection (user_id, fish_id, quantity, biggest_size)
                VALUES ($1, $2, 1, 0)
                ON CONFLICT(user_id, fish_id)
                DO UPDATE SET quantity = fish_collection.quantity + 1
            """, self.user_id, fish_key)
            fish_name = fish_key.replace('_', ' ').title()
            msg_extra = f"\n🐟 **Nhận Cá:** {fish_name}"
        
        elif reward_type == "nothing":
            msg_extra = "\n💨 **Kết quả:** Không có gì..."
        
        elif reward_type == "rock":
            msg_extra = "\n🪨 **Kết quả:** Cục đá vô dụng"
            
        return msg_extra

    async def _process_decline(self, interaction: discord.Interaction):
        decline_data = self.npc_data.get("rewards", {}).get("decline", "Bạn bỏ đi.")
        
        final_description = ""
        
        if isinstance(decline_data, list):
            result = self._roll_outcome(decline_data)
            async with db_manager.transaction() as conn:
                msg_extra = await self._apply_outcome(result, conn)
            final_description = result.get("message", "Kết quả không xác định.").replace("{amount}", msg_extra)
        else:
            final_description = str(decline_data)

        embed = discord.Embed(
            title=f"{self.npc_data['name']} - Từ Chối",
            description=final_description,
            color=discord.Color.light_grey()
        )
        await interaction.followup.send(embed=embed)
        
        try:
            await increment_stat(self.user_id, "npc_affinity", self.npc_key, -1)
            logger.info(f"[NPC_AFFINITY] User {self.user_id} decreased affinity with {self.npc_key} (-1)")
        except Exception:
            pass

    def _roll_outcome(self, pool: List[Dict]) -> Dict:
        if not pool: 
            return {}
        weights = [item.get("chance", 0.1) for item in pool]
        return random.choices(pool, weights=weights)[0]

    async def on_timeout(self):
        if self.completed:
            return
        self.completed = True
        
        for item in self.children:
            item.disabled = True
        
        try:
            timeout_embed = discord.Embed(
                title=f"⏰ {self.npc_data.get('name', 'NPC')} - Hết Thời Gian",
                description=(
                    f"Bạn đã không phản hồi trong **30 giây**.\n"
                    f"{self.npc_data.get('name', 'NPC')} đã bỏ đi..."
                ),
                color=discord.Color.dark_grey()
            )
            timeout_embed.set_footer(text="Sự kiện đã hết hạn")
            
            if hasattr(self, 'message') and self.message:
                await self.message.edit(embed=timeout_embed, view=self)
                logger.info(f"[NPC_TIMEOUT] User {self.user_id} timed out on {self.npc_key}")
        except discord.NotFound:
            logger.warning(f"[NPC_TIMEOUT] Message deleted for user {self.user_id}")
        except discord.HTTPException as e:
            logger.error(f"[NPC_TIMEOUT] Failed to edit message: {e}")
        except Exception as e:
            logger.error(f"[NPC_TIMEOUT] Unexpected error: {e}")

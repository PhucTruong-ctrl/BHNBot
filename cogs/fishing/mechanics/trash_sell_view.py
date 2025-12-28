import discord
import random
from discord.ui import View, Button
from database_manager import get_inventory, add_seeds, remove_item
from ..constants import TRASH_ITEMS
import logging

logger = logging.getLogger("fishing")

class TrashSellView(View):
    """View for Black Market trash selling."""
    def __init__(self, manager):
        super().__init__(timeout=None) # Persistent view? Or attached to message?
        # If attached to event message, timeout should match event duration or handle "Event Ended" interaction.
        # Ideally, we verify event is active on interaction.
        self.manager = manager

    async def _process_sell(self, interaction: discord.Interaction, amount_mode: str):
        """
        amount_mode: "1", "10", "all"
        """
        await interaction.response.defer(ephemeral=False)
        
        # 1. Verify Event is Active
        if not self.manager.current_event or self.manager.current_event["key"] != "scrap_yard":
            await interaction.followup.send("⚠️ Chú Ba đã lái xe đi mất rồi!", ephemeral=True)
            return

        user_id = interaction.user.id
        inventory = await get_inventory(user_id)
        
        # 2. Identify Trash Items
        # TRASH_ITEMS is a list of dicts or objects? properties: key, name, etc.
        # constants.py: TRASH_ITEMS = [v for v in ALL_ITEMS_DATA.values() if v.get("type") == "trash"]
        trash_keys = [t["key"] for t in TRASH_ITEMS]
        
        user_trash = {k: v for k, v in inventory.items() if k in trash_keys and v > 0}
        
        if not user_trash:
            await interaction.followup.send("🗑️ Túi của bạn sạch bong! Không có rác để bán.", ephemeral=True)
            return

        # 3. Determine Items to Sell
        to_sell = {} # {key: qty}
        
        if amount_mode == "all":
            to_sell = user_trash.copy()
        else:
            limit = int(amount_mode)
            collected = 0
            # Prioritize... random? or order? 
            # Let's just iterate
            for key, qty in user_trash.items():
                take = min(qty, limit - collected)
                to_sell[key] = take
                collected += take
                if collected >= limit:
                    break
        
        if not to_sell:
             await interaction.followup.send("❌ Không tìm thấy rác để bán.", ephemeral=True)
             return

        # 4. Sell Logic
        total_seeds = 0
        lines = []
        
        for key, qty in to_sell.items():
            # Random price per UNIT? Or per BATCH?
            # User said "random 1 mon bao nhieu tien".
            # For performance with "Sell All" (could be 1000 items), calculating per unit loop is slow.
            # We will calculate average price per item type? 
            # Let's do: price = random(50, 500) per TYPE for this transaction.
            # It varies per transaction, so repeated clicks give different rates.
            
            # Random price (use config if available, else default)
            evt_mech = self.manager.current_event.get("data", {}).get("mechanics", {})
            min_price = evt_mech.get("trash_price_min", 100)
            max_price = evt_mech.get("trash_price_max", 800)
            
            unit_price = random.randint(min_price, max_price)
            line_total = unit_price * qty
            total_seeds += line_total
            
            # Remove from DB
            await remove_item(user_id, key, qty)
            
            # Find name
            item_name = next((t["name"] for t in TRASH_ITEMS if t["key"] == key), key)
            lines.append(f"🗑️ **{item_name}** x{qty}: `{line_total:,} Hạt` ({unit_price}/c)")

        # 5. Add Money
        await add_seeds(user_id, total_seeds, reason='sell_trash', category='fishing')
        
        # 6. Response
        desc = "\n".join(lines)
        if len(desc) > 1000: desc = desc[:1000] + "\n...(còn nữa)"
        
        username = interaction.user.name.upper()
        embed = discord.Embed(
            title=f"🧾 HÓA ĐƠN BÁN VE CHAI - {username}",
            description=f"{desc}\n\n💰 **TỔNG NHẬN:** `{total_seeds:,} Hạt`",
            color=discord.Color.green()
        )
        embed.set_footer(text="Chú Ba: 'Chai bao nhôm nhựa bán hông con??'")
        
        await interaction.followup.send(embed=embed, ephemeral=False)

    @discord.ui.button(label="Bán 1 Rác", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def sell_one(self, interaction: discord.Interaction, button: Button):
        await self._process_sell(interaction, "1")

    @discord.ui.button(label="Bán 10 Rác", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def sell_ten(self, interaction: discord.Interaction, button: Button):
        await self._process_sell(interaction, "10")

    @discord.ui.button(label="♻️ BÁN HẾT RÁC", style=discord.ButtonStyle.danger, emoji="💰")
    async def sell_all(self, interaction: discord.Interaction, button: Button):
        await self._process_sell(interaction, "all")

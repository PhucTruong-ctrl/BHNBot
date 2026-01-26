import discord
from discord.ui import View
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BHNView(View):
    """Base View class with consistent timeout handling for all BHNBot UI components."""

    def __init__(
        self, 
        timeout: float = 180.0,
        original_interaction: Optional[discord.Interaction] = None,
        timeout_message: str = "⏱️ Menu đã hết thời gian. Vui lòng sử dụng lệnh lại."
    ):
        super().__init__(timeout=timeout)
        self.original_interaction = original_interaction
        self.timeout_message = timeout_message
        self._message: Optional[discord.Message] = None

    async def on_timeout(self) -> None:
        try:
            await self._disable_all_items()
        except Exception as e:
            logger.warning(f"[VIEW_TIMEOUT] Failed to disable items: {e}")

    async def _disable_all_items(self) -> None:
        for item in self.children:
            if hasattr(item, 'disabled'):
                item.disabled = True

        if self._message:
            try:
                await self._message.edit(view=self)
            except discord.NotFound:
                pass
            except discord.HTTPException as e:
                logger.warning(f"[VIEW_TIMEOUT] Failed to edit message: {e}")
        elif self.original_interaction:
            try:
                await self.original_interaction.edit_original_response(view=self)
            except discord.NotFound:
                pass
            except discord.HTTPException as e:
                logger.warning(f"[VIEW_TIMEOUT] Failed to edit interaction: {e}")

    def set_message(self, message: discord.Message) -> None:
        self._message = message


class ConfirmView(BHNView):
    """Confirmation dialog with Yes/No buttons."""

    def __init__(
        self,
        timeout: float = 60.0,
        confirm_label: str = "Xác nhận",
        cancel_label: str = "Hủy",
        **kwargs
    ):
        super().__init__(timeout=timeout, **kwargs)
        self.value: Optional[bool] = None

        confirm_btn = discord.ui.Button(
            label=confirm_label, style=discord.ButtonStyle.success, emoji="✅"
        )
        confirm_btn.callback = self._confirm_callback
        self.add_item(confirm_btn)

        cancel_btn = discord.ui.Button(
            label=cancel_label, style=discord.ButtonStyle.secondary, emoji="❌"
        )
        cancel_btn.callback = self._cancel_callback
        self.add_item(cancel_btn)

    async def _confirm_callback(self, interaction: discord.Interaction):
        self.value = True
        await interaction.response.defer()
        self.stop()

    async def _cancel_callback(self, interaction: discord.Interaction):
        self.value = False
        await interaction.response.defer()
        self.stop()


async def safe_dm(user: discord.User, content: str = None, embed: discord.Embed = None) -> bool:
    """Safely send DM to user, handling Forbidden errors."""
    try:
        await user.send(content=content, embed=embed)
        return True
    except discord.Forbidden:
        logger.info(f"[SAFE_DM] Cannot DM user {user.id} - DMs disabled")
        return False
    except discord.HTTPException as e:
        logger.warning(f"[SAFE_DM] Failed to DM user {user.id}: {e}")
        return False

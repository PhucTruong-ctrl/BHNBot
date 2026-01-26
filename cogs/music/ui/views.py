from __future__ import annotations

import discord
from discord import Interaction
from discord.ui import View, Button, Select, button, select
from typing import TYPE_CHECKING, Optional
import wavelink

if TYPE_CHECKING:
    from discord.ext.commands import Bot


class VolumeSelect(Select):

    def __init__(self, current_volume: int) -> None:
        options = [
            discord.SelectOption(
                label="🔇 Tắt tiếng",
                value="0",
                description="Âm lượng 0%",
                default=(current_volume == 0)
            ),
            discord.SelectOption(
                label="🔈 10%",
                value="10",
                description="Âm lượng rất nhỏ",
                default=(current_volume == 10)
            ),
            discord.SelectOption(
                label="🔈 25%",
                value="25",
                description="Âm lượng nhỏ",
                default=(current_volume == 25)
            ),
            discord.SelectOption(
                label="🔉 50%",
                value="50",
                description="Âm lượng vừa",
                default=(current_volume == 50)
            ),
            discord.SelectOption(
                label="🔉 75%",
                value="75",
                description="Âm lượng lớn",
                default=(current_volume == 75)
            ),
            discord.SelectOption(
                label="🔊 100%",
                value="100",
                description="Âm lượng tối đa",
                default=(current_volume == 100)
            ),
        ]
        super().__init__(
            placeholder="🎚️ Chọn âm lượng...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="music:volume_select"
        )

    async def callback(self, interaction: Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Lỗi: Không tìm thấy server.", ephemeral=True
            )
            return

        player: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if not player:
            await interaction.response.send_message(
                "❌ Bot không đang phát nhạc.", ephemeral=True
            )
            return

        new_volume = int(self.values[0])
        await player.set_volume(new_volume)

        volume_emoji = "🔇" if new_volume == 0 else "🔈" if new_volume <= 25 else "🔉" if new_volume <= 75 else "🔊"
        await interaction.response.send_message(
            f"{volume_emoji} Đã đặt âm lượng: **{new_volume}%**",
            ephemeral=True
        )


class VolumeSelectView(View):

    def __init__(self, current_volume: int, timeout: float = 60.0) -> None:
        super().__init__(timeout=timeout)
        self.add_item(VolumeSelect(current_volume))

    async def on_timeout(self) -> None:
        for child in self.children:
            if hasattr(child, 'disabled'):
                child.disabled = True
        self.stop()


class MusicControlView(View):

    def __init__(self, timeout: float | None = None) -> None:
        super().__init__(timeout=timeout)

    async def _get_player(self, interaction: Interaction) -> Optional[wavelink.Player]:
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Lỗi: Không tìm thấy server.", ephemeral=True
            )
            return None

        player: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if not player:
            await interaction.response.send_message(
                "❌ Bot không đang phát nhạc.", ephemeral=True
            )
            return None

        return player

    @button(label="Tạm dừng", emoji="⏸️", style=discord.ButtonStyle.secondary, custom_id="music:pause", row=0)
    async def pause_button(self, interaction: Interaction, btn: Button) -> None:
        player = await self._get_player(interaction)
        if not player:
            return

        if player.paused:
            await player.pause(False)
            btn.label = "Tạm dừng"
            btn.emoji = "⏸️"
            btn.style = discord.ButtonStyle.secondary
        else:
            await player.pause(True)
            btn.label = "Tiếp tục"
            btn.emoji = "▶️"
            btn.style = discord.ButtonStyle.success

        await interaction.response.edit_message(view=self)

    @button(label="Tiếp theo", emoji="⏭️", style=discord.ButtonStyle.primary, custom_id="music:next", row=0)
    async def next_button(self, interaction: Interaction, btn: Button) -> None:
        player = await self._get_player(interaction)
        if not player:
            return

        if not player.queue and not player.current:
            await interaction.response.send_message(
                "❌ Không có bài hát nào trong hàng đợi.", ephemeral=True
            )
            return

        await player.skip()
        await interaction.response.send_message(
            "⏭️ Đã chuyển sang bài tiếp theo.", ephemeral=True
        )

    @button(label="Dừng", emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="music:stop", row=0)
    async def stop_button(self, interaction: Interaction, btn: Button) -> None:
        player = await self._get_player(interaction)
        if not player:
            return

        player.queue.clear()
        await player.stop()
        await player.disconnect()

        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True

        await interaction.response.edit_message(view=self)
        await interaction.followup.send("⏹️ Đã dừng phát nhạc và ngắt kết nối.", ephemeral=True)

    @button(label="Âm lượng", emoji="🔊", style=discord.ButtonStyle.secondary, custom_id="music:volume", row=0)
    async def volume_button(self, interaction: Interaction, btn: Button) -> None:
        player = await self._get_player(interaction)
        if not player:
            return

        current_volume = player.volume
        volume_view = VolumeSelectView(current_volume)

        embed = discord.Embed(
            title="🎚️ Điều chỉnh âm lượng",
            description=f"Âm lượng hiện tại: **{current_volume}%**\n\nChọn mức âm lượng mới:",
            color=discord.Color.blue()
        )

        await interaction.response.send_message(
            embed=embed,
            view=volume_view,
            ephemeral=True
        )

    @button(label="Xáo trộn", emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="music:shuffle", row=1)
    async def shuffle_button(self, interaction: Interaction, btn: Button) -> None:
        player = await self._get_player(interaction)
        if not player:
            return

        if len(player.queue) < 2:
            await interaction.response.send_message(
                "❌ Cần ít nhất 2 bài trong hàng đợi để xáo trộn.", ephemeral=True
            )
            return

        player.queue.shuffle()
        await interaction.response.send_message(
            f"🔀 Đã xáo trộn **{len(player.queue)}** bài hát.", ephemeral=True
        )

    @button(label="Lặp lại", emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="music:loop", row=1)
    async def loop_button(self, interaction: Interaction, btn: Button) -> None:
        player = await self._get_player(interaction)
        if not player:
            return

        if player.queue.mode == wavelink.QueueMode.normal:
            player.queue.mode = wavelink.QueueMode.loop
            btn.style = discord.ButtonStyle.success
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("🔁 Đã bật chế độ lặp lại bài hát.", ephemeral=True)
        elif player.queue.mode == wavelink.QueueMode.loop:
            player.queue.mode = wavelink.QueueMode.loop_all
            btn.emoji = "🔂"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("🔂 Đã bật chế độ lặp lại toàn bộ hàng đợi.", ephemeral=True)
        else:
            player.queue.mode = wavelink.QueueMode.normal
            btn.style = discord.ButtonStyle.secondary
            btn.emoji = "🔁"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("➡️ Đã tắt chế độ lặp lại.", ephemeral=True)


def _format_duration(ms: int) -> str:
    seconds = ms // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _get_source_label(uri: Optional[str]) -> str:
    if not uri:
        return "🎵"
    uri_lower = uri.lower()
    if "soundcloud" in uri_lower:
        return "☁️ SoundCloud"
    elif "youtube" in uri_lower or "youtu.be" in uri_lower:
        return "▶️ YouTube"
    elif "spotify" in uri_lower:
        return "🟢 Spotify"
    return "🎵"


def create_now_playing_embed(
    track: wavelink.Playable,
    requester: Optional[discord.Member] = None,
    position_ms: int = 0,
    is_paused: bool = False
) -> discord.Embed:
    duration = track.length or 0
    position_str = _format_duration(position_ms)
    duration_str = _format_duration(duration)

    progress = position_ms / duration if duration > 0 else 0
    bar_length = 15
    filled = int(bar_length * progress)
    bar = "━" * filled + "●" + "─" * (bar_length - filled - 1)

    status = "⏸️" if is_paused else "▶️"
    source = _get_source_label(track.uri)

    embed = discord.Embed(
        title="🎵 Đang phát",
        color=discord.Color.green() if not is_paused else discord.Color.orange()
    )

    embed.add_field(
        name="Bài hát",
        value=f"**[{track.title}]({track.uri})**" if track.uri else f"**{track.title}**",
        inline=False
    )

    embed.add_field(
        name="Nghệ sĩ",
        value=track.author or "Không rõ",
        inline=True
    )

    embed.add_field(
        name="Nguồn",
        value=source,
        inline=True
    )

    embed.add_field(
        name="Thời lượng",
        value=f"{status} `{position_str}` {bar} `{duration_str}`",
        inline=False
    )

    if requester:
        embed.set_footer(
            text=f"Yêu cầu bởi {requester.display_name}",
            icon_url=requester.display_avatar.url
        )

    if hasattr(track, 'artwork') and track.artwork:
        embed.set_thumbnail(url=track.artwork)

    return embed


NowPlayingEmbed = create_now_playing_embed

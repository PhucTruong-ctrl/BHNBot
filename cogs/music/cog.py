import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import asyncio
from core.logging import get_logger
import re
import aiohttp
from typing import Optional, cast

from .ui.views import MusicControlView, create_now_playing_embed
from .services import PlaylistService

logger = get_logger("music_cog")

LAVALINK_URI = "http://localhost:2333"
LAVALINK_PASSWORD = "bhnbot_lavalink_2026"

YOUTUBE_URL_PATTERN = re.compile(r'(youtube\.com|youtu\.be)')
SPOTIFY_TRACK_PATTERN = re.compile(r'spotify\.com/track/([a-zA-Z0-9]+)')
SPOTIFY_PLAYLIST_PATTERN = re.compile(r'spotify\.com/playlist/([a-zA-Z0-9]+)')
SPOTIFY_ALBUM_PATTERN = re.compile(r'spotify\.com/album/([a-zA-Z0-9]+)')


def require_lavalink():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not hasattr(interaction.client, 'get_cog'):
            return False
        cog = interaction.client.get_cog("Music")  # type: ignore
        if not cog or not getattr(cog, 'lavalink_connected', False):
            await interaction.response.send_message(
                "❌ **Lavalink server chưa sẵn sàng!**\n"
                "Music bot cần Lavalink server để hoạt động.",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.music_247_guilds: set[int] = set()
        self.lavalink_connected = False
        self._connection_attempted = False
        self._now_playing_messages: dict[int, discord.Message] = {}
        self._music_channels: dict[int, discord.TextChannel] = {}

    async def cog_load(self):
        asyncio.create_task(self._connect_lavalink_background())
        asyncio.create_task(PlaylistService.ensure_tables())
        self.bot.add_view(MusicControlView())

    async def _connect_lavalink_background(self):
        await asyncio.sleep(3)
        await self._try_connect_lavalink()

    async def _try_connect_lavalink(self) -> bool:
        if self._connection_attempted and self.lavalink_connected:
            return True

        self._connection_attempted = True
        try:
            node = wavelink.Node(uri=LAVALINK_URI, password=LAVALINK_PASSWORD)
            await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)
            self.lavalink_connected = True
            logger.info("[MUSIC] Connected to Lavalink successfully")
            return True
        except Exception as e:
            self.lavalink_connected = False
            logger.warning(f"[MUSIC] Lavalink unavailable: {e}")
            return False

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        self.lavalink_connected = True
        logger.info(f"[MUSIC] Node {payload.node.identifier} ready")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        track = payload.track

        if not player or not player.guild:
            return

        guild_id = player.guild.id
        text_channel = self._music_channels.get(guild_id)
        if not text_channel:
            return

        embed = create_now_playing_embed(track, position_ms=0, is_paused=False)
        view = MusicControlView()

        old_message = self._now_playing_messages.get(guild_id)

        try:
            if old_message:
                try:
                    async for msg in text_channel.history(limit=1):
                        if msg.id == old_message.id:
                            await old_message.edit(embed=embed, view=view)
                            return
                    await old_message.delete()
                except discord.NotFound:
                    pass
                except Exception:
                    pass

            new_message = await text_channel.send(embed=embed, view=view)
            self._now_playing_messages[guild_id] = new_message
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player:
            return

        if player.queue.is_empty:
            if player.guild and player.guild.id in self.music_247_guilds:
                return
            await asyncio.sleep(300)
            if player.queue.is_empty and not player.playing:
                await player.disconnect()

    async def _get_spotify_track_info(self, track_id: str) -> Optional[str]:
        try:
            embed_url = f"https://open.spotify.com/embed/track/{track_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(embed_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        title_match = re.search(r'<title>([^<]+)</title>', html)
                        if title_match:
                            title = title_match.group(1).replace(' | Spotify', '').strip()
                            return title
        except Exception:
            pass
        return None

    async def _get_spotify_playlist_tracks(self, playlist_id: str) -> list[str]:
        tracks = []
        try:
            embed_url = f"https://open.spotify.com/embed/playlist/{playlist_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(embed_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        track_matches = re.findall(r'"name":"([^"]+)".*?"artists":\[{"name":"([^"]+)"', html)
                        for name, artist in track_matches[:50]:
                            tracks.append(f"{name} {artist}")
        except Exception:
            pass
        return tracks

    @app_commands.command(name="play", description="Phát nhạc từ YouTube/Spotify/SoundCloud")
    @app_commands.describe(query="Tên bài hát, YouTube URL, hoặc Spotify URL")
    @require_lavalink()
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not interaction.guild:
            return await interaction.followup.send("❌ Chỉ dùng được trong server", ephemeral=True)

        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.voice or not member.voice.channel:
            return await interaction.followup.send("❌ Bạn cần vào voice channel trước!", ephemeral=True)

        voice_channel = member.voice.channel

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            try:
                player = await voice_channel.connect(cls=wavelink.Player)
            except Exception as e:
                return await interaction.followup.send(f"❌ Không thể kết nối: {e}", ephemeral=True)

        self._music_channels[interaction.guild.id] = interaction.channel  # type: ignore

        try:
            is_youtube = bool(YOUTUBE_URL_PATTERN.search(query))
            spotify_track = SPOTIFY_TRACK_PATTERN.search(query)
            spotify_playlist = SPOTIFY_PLAYLIST_PATTERN.search(query)
            spotify_album = SPOTIFY_ALBUM_PATTERN.search(query)

            if is_youtube:
                tracks = await wavelink.Playable.search(query, source=None)
                if not tracks:
                    return await interaction.followup.send("❌ Không tìm thấy video YouTube", ephemeral=True)

                if isinstance(tracks, wavelink.Playlist):
                    for track in tracks.tracks:
                        await player.queue.put_wait(track)
                    embed = discord.Embed(
                        title="📋 Đã thêm YouTube Playlist",
                        description=f"**{tracks.name}** - {len(tracks.tracks)} bài",
                        color=discord.Color.red()
                    )
                else:
                    track = tracks[0]
                    await player.queue.put_wait(track)
                    embed = discord.Embed(
                        title="🎵 Đã thêm từ YouTube",
                        description=f"**[{track.title}]({track.uri})**",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="Kênh", value=track.author, inline=True)
                    if track.artwork:
                        embed.set_thumbnail(url=track.artwork)

            elif spotify_track:
                track_id = spotify_track.group(1)
                track_info = await self._get_spotify_track_info(track_id)

                if not track_info:
                    return await interaction.followup.send("❌ Không thể lấy thông tin từ Spotify", ephemeral=True)

                search_query = f"scsearch:{track_info}"
                tracks = await wavelink.Playable.search(search_query, source=None)

                if not tracks:
                    search_query = f"ytsearch:{track_info}"
                    tracks = await wavelink.Playable.search(search_query, source=None)

                if not tracks:
                    return await interaction.followup.send(f"❌ Không tìm thấy: {track_info}", ephemeral=True)

                track = tracks[0]
                await player.queue.put_wait(track)
                embed = discord.Embed(
                    title="🎵 Đã thêm từ Spotify",
                    description=f"**[{track.title}]({track.uri})**",
                    color=discord.Color.green()
                )
                embed.add_field(name="Nghệ sĩ", value=track.author, inline=True)
                embed.set_footer(text=f"Tìm từ: {track_info}")
                if track.artwork:
                    embed.set_thumbnail(url=track.artwork)

            elif spotify_playlist or spotify_album:
                playlist_match = spotify_playlist or spotify_album
                playlist_id = playlist_match.group(1) if playlist_match else ""
                playlist_type = "playlist" if spotify_playlist else "album"

                await interaction.followup.send(f"🔄 Đang tải Spotify {playlist_type}...")

                track_names = await self._get_spotify_playlist_tracks(playlist_id)
                if not track_names:
                    return await interaction.followup.send("❌ Không thể tải playlist từ Spotify", ephemeral=True)

                added = 0
                for track_name in track_names:
                    try:
                        search_query = f"scsearch:{track_name}"
                        tracks = await wavelink.Playable.search(search_query, source=None)
                        if tracks:
                            await player.queue.put_wait(tracks[0])
                            added += 1
                    except Exception:
                        continue

                embed = discord.Embed(
                    title=f"📋 Đã thêm Spotify {playlist_type.title()}",
                    description=f"Thêm **{added}/{len(track_names)}** bài vào hàng đợi",
                    color=discord.Color.green()
                )

            else:
                search_query = f"scsearch:{query}"
                tracks = await wavelink.Playable.search(search_query, source=None)

                if not tracks:
                    search_query = f"ytsearch:{query}"
                    tracks = await wavelink.Playable.search(search_query, source=None)

                if not tracks:
                    return await interaction.followup.send("❌ Không tìm thấy bài hát", ephemeral=True)

                track = tracks[0]
                await player.queue.put_wait(track)
                embed = discord.Embed(
                    title="🎵 Đã thêm vào hàng đợi",
                    description=f"**[{track.title}]({track.uri})**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Nghệ sĩ", value=track.author, inline=True)
                if track.artwork:
                    embed.set_thumbnail(url=track.artwork)

            if not player.playing:
                await player.play(player.queue.get())

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"[MUSIC] Play error: {e}")
            await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)

    @app_commands.command(name="skip", description="Bỏ qua bài hát hiện tại")
    @require_lavalink()
    async def skip(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("❌ Bot chưa phát nhạc", ephemeral=True)

        await player.skip()
        await interaction.response.send_message("⏭️ Đã bỏ qua bài hát")

    @app_commands.command(name="stop", description="Dừng phát nhạc và rời kênh")
    @require_lavalink()
    async def stop(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("❌ Bot chưa trong voice", ephemeral=True)

        if interaction.guild.id in self.music_247_guilds:
            self.music_247_guilds.discard(interaction.guild.id)

        await player.disconnect()
        await interaction.response.send_message("⏹️ Đã dừng và rời kênh")

    @app_commands.command(name="pause", description="Tạm dừng/tiếp tục phát nhạc")
    @require_lavalink()
    async def pause(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("❌ Bot chưa phát nhạc", ephemeral=True)

        if player.paused:
            await player.pause(False)
            await interaction.response.send_message("▶️ Đã tiếp tục phát")
        else:
            await player.pause(True)
            await interaction.response.send_message("⏸️ Đã tạm dừng")

    @app_commands.command(name="queue", description="Xem hàng đợi nhạc")
    @require_lavalink()
    async def queue(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("❌ Bot chưa phát nhạc", ephemeral=True)

        if player.queue.is_empty and not player.current:
            return await interaction.response.send_message("📭 Hàng đợi trống", ephemeral=True)

        embed = discord.Embed(title="🎶 Hàng đợi nhạc", color=discord.Color.purple())

        if player.current:
            embed.add_field(
                name="▶️ Đang phát",
                value=f"**{player.current.title}** - {player.current.author}",
                inline=False
            )

        if not player.queue.is_empty:
            queue_list = []
            for i, track in enumerate(list(player.queue)[:10], 1):
                queue_list.append(f"`{i}.` **{track.title}** - {track.author}")

            embed.add_field(
                name=f"📋 Tiếp theo ({len(player.queue)} bài)",
                value="\n".join(queue_list) if queue_list else "Trống",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Xem bài đang phát")
    @require_lavalink()
    async def nowplaying(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player or not player.current:
            return await interaction.response.send_message("❌ Không có bài đang phát", ephemeral=True)

        member = interaction.guild.get_member(interaction.user.id)
        embed = create_now_playing_embed(
            player.current,
            requester=member,
            position_ms=player.position,
            is_paused=player.paused
        )
        view = MusicControlView()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="volume", description="Điều chỉnh âm lượng (0-100)")
    @app_commands.describe(level="Mức âm lượng (0-100)")
    @require_lavalink()
    async def volume(self, interaction: discord.Interaction, level: int):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("❌ Bot chưa phát nhạc", ephemeral=True)

        level = max(0, min(100, level))
        await player.set_volume(level)
        await interaction.response.send_message(f"🔊 Âm lượng: **{level}%**")

    @app_commands.command(name="shuffle", description="Xáo trộn hàng đợi")
    @require_lavalink()
    async def shuffle(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("❌ Bot chưa phát nhạc", ephemeral=True)

        player.queue.shuffle()
        await interaction.response.send_message("🔀 Đã xáo trộn hàng đợi")

    @app_commands.command(name="loop", description="Bật/tắt lặp lại")
    @app_commands.describe(mode="Chế độ lặp")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Tắt", value="off"),
        app_commands.Choice(name="Lặp bài", value="track"),
        app_commands.Choice(name="Lặp hàng đợi", value="queue"),
    ])
    @require_lavalink()
    async def loop(self, interaction: discord.Interaction, mode: str):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("❌ Bot chưa phát nhạc", ephemeral=True)

        if mode == "off":
            player.queue.mode = wavelink.QueueMode.normal
            await interaction.response.send_message("➡️ Đã tắt lặp lại")
        elif mode == "track":
            player.queue.mode = wavelink.QueueMode.loop
            await interaction.response.send_message("🔂 Đang lặp bài hiện tại")
        elif mode == "queue":
            player.queue.mode = wavelink.QueueMode.loop_all
            await interaction.response.send_message("🔁 Đang lặp toàn bộ hàng đợi")

    @app_commands.command(name="247", description="Bật/tắt chế độ 24/7")
    @require_lavalink()
    async def mode_247(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        guild_id = interaction.guild.id
        if guild_id in self.music_247_guilds:
            self.music_247_guilds.discard(guild_id)
            await interaction.response.send_message("📴 Đã tắt chế độ 24/7")
        else:
            self.music_247_guilds.add(guild_id)
            await interaction.response.send_message("📻 Đã bật chế độ 24/7")

    @app_commands.command(name="filter", description="Áp dụng hiệu ứng âm thanh")
    @app_commands.describe(effect="Hiệu ứng")
    @app_commands.choices(effect=[
        app_commands.Choice(name="Lofi", value="lofi"),
        app_commands.Choice(name="Vaporwave", value="vaporwave"),
        app_commands.Choice(name="Nightcore", value="nightcore"),
        app_commands.Choice(name="Bass Boost", value="bass"),
        app_commands.Choice(name="Reset", value="reset"),
    ])
    @require_lavalink()
    async def audio_filter(self, interaction: discord.Interaction, effect: str):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            return await interaction.response.send_message("❌ Bot chưa phát nhạc", ephemeral=True)

        filters = player.filters

        if effect == "lofi":
            filters.timescale.set(pitch=0.9)
            msg = "🎧 Đã bật **Lofi**"
        elif effect == "vaporwave":
            filters.timescale.set(speed=0.8, pitch=0.85)
            msg = "🌊 Đã bật **Vaporwave**"
        elif effect == "nightcore":
            filters.timescale.set(speed=1.2, pitch=1.2)
            msg = "⚡ Đã bật **Nightcore**"
        elif effect == "bass":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.6},
                {"band": 1, "gain": 0.5},
            ])
            msg = "🔊 Đã bật **Bass Boost**"
        else:
            filters.reset()
            msg = "🔄 Đã reset hiệu ứng"

        await player.set_filters(filters)
        await interaction.response.send_message(msg)

    playlist_group = app_commands.Group(name="playlist", description="Quản lý playlist cá nhân")

    @playlist_group.command(name="create", description="Tạo playlist mới")
    @app_commands.describe(name="Tên playlist")
    async def playlist_create(self, interaction: discord.Interaction, name: str):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        if len(name) > 100:
            return await interaction.response.send_message("❌ Tên playlist quá dài (tối đa 100 ký tự)", ephemeral=True)

        playlist_id = await PlaylistService.create_playlist(
            interaction.user.id, interaction.guild.id, name
        )

        if playlist_id:
            await interaction.response.send_message(f"✅ Đã tạo playlist **{name}**")
        else:
            await interaction.response.send_message(f"❌ Playlist **{name}** đã tồn tại", ephemeral=True)

    @playlist_group.command(name="add", description="Thêm bài hát đang phát vào playlist")
    @app_commands.describe(name="Tên playlist")
    async def playlist_add(self, interaction: discord.Interaction, name: str):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player or not player.current:
            return await interaction.response.send_message("❌ Không có bài đang phát", ephemeral=True)

        playlist = await PlaylistService.get_playlist(
            interaction.user.id, interaction.guild.id, name
        )

        if not playlist:
            return await interaction.response.send_message(f"❌ Playlist **{name}** không tồn tại", ephemeral=True)

        track = player.current
        success = await PlaylistService.add_track(
            playlist.id,
            track.title,
            track.uri or "",
            track.author or "Unknown",
            track.length or 0
        )

        if success:
            await interaction.response.send_message(
                f"✅ Đã thêm **{track.title}** vào playlist **{name}**"
            )
        else:
            await interaction.response.send_message("❌ Không thể thêm bài hát", ephemeral=True)

    @playlist_group.command(name="list", description="Xem danh sách playlist của bạn")
    async def playlist_list(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        playlists = await PlaylistService.list_playlists(
            interaction.user.id, interaction.guild.id
        )

        if not playlists:
            return await interaction.response.send_message(
                "📭 Bạn chưa có playlist nào. Dùng `/playlist create` để tạo mới!",
                ephemeral=True
            )

        embed = discord.Embed(
            title="📋 Playlist của bạn",
            color=discord.Color.blue()
        )

        for pl in playlists:
            duration_min = pl.total_duration_ms // 60000
            embed.add_field(
                name=f"🎵 {pl.name}",
                value=f"{pl.track_count} bài • {duration_min} phút",
                inline=True
            )

        await interaction.response.send_message(embed=embed)

    @playlist_group.command(name="view", description="Xem chi tiết playlist")
    @app_commands.describe(name="Tên playlist")
    async def playlist_view(self, interaction: discord.Interaction, name: str):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        playlist = await PlaylistService.get_playlist(
            interaction.user.id, interaction.guild.id, name
        )

        if not playlist:
            return await interaction.response.send_message(f"❌ Playlist **{name}** không tồn tại", ephemeral=True)

        embed = discord.Embed(
            title=f"🎵 {playlist.name}",
            description=f"{playlist.track_count} bài hát",
            color=discord.Color.blue()
        )

        if playlist.tracks:
            track_list = []
            for i, track in enumerate(playlist.tracks[:15], 1):
                duration_str = f"{track.duration_ms // 60000}:{(track.duration_ms // 1000) % 60:02d}"
                track_list.append(f"`{i}.` **{track.title}** ({duration_str})")

            embed.add_field(
                name="Bài hát",
                value="\n".join(track_list),
                inline=False
            )

            if len(playlist.tracks) > 15:
                embed.set_footer(text=f"... và {len(playlist.tracks) - 15} bài nữa")
        else:
            embed.add_field(name="Bài hát", value="Playlist trống", inline=False)

        await interaction.response.send_message(embed=embed)

    @playlist_group.command(name="play", description="Phát playlist")
    @app_commands.describe(name="Tên playlist")
    @require_lavalink()
    async def playlist_play(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()

        if not interaction.guild:
            return await interaction.followup.send("❌ Chỉ dùng trong server", ephemeral=True)

        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.voice or not member.voice.channel:
            return await interaction.followup.send("❌ Bạn cần vào voice channel!", ephemeral=True)

        playlist = await PlaylistService.get_playlist(
            interaction.user.id, interaction.guild.id, name
        )

        if not playlist:
            return await interaction.followup.send(f"❌ Playlist **{name}** không tồn tại", ephemeral=True)

        if not playlist.tracks:
            return await interaction.followup.send(f"❌ Playlist **{name}** trống", ephemeral=True)

        player = cast(wavelink.Player, interaction.guild.voice_client)
        if not player:
            try:
                player = await member.voice.channel.connect(cls=wavelink.Player)
            except Exception as e:
                return await interaction.followup.send(f"❌ Không thể kết nối: {e}", ephemeral=True)

        added = 0
        for track_data in playlist.tracks:
            try:
                tracks = await wavelink.Playable.search(track_data.uri)
                if tracks:
                    if isinstance(tracks, list):
                        await player.queue.put_wait(tracks[0])
                    else:
                        await player.queue.put_wait(tracks)
                    added += 1
            except Exception:
                continue

        if not player.playing and not player.queue.is_empty:
            await player.play(player.queue.get())

        await interaction.followup.send(
            f"🎶 Đang phát playlist **{name}** ({added}/{len(playlist.tracks)} bài)"
        )

    @playlist_group.command(name="remove", description="Xóa bài hát khỏi playlist")
    @app_commands.describe(name="Tên playlist", position="Vị trí bài hát (1, 2, 3...)")
    async def playlist_remove(self, interaction: discord.Interaction, name: str, position: int):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        playlist = await PlaylistService.get_playlist(
            interaction.user.id, interaction.guild.id, name
        )

        if not playlist:
            return await interaction.response.send_message(f"❌ Playlist **{name}** không tồn tại", ephemeral=True)

        if position < 1 or position > len(playlist.tracks):
            return await interaction.response.send_message(
                f"❌ Vị trí không hợp lệ (1-{len(playlist.tracks)})", ephemeral=True
            )

        removed_track = playlist.tracks[position - 1]
        success = await PlaylistService.remove_track(playlist.id, position)

        if success:
            await interaction.response.send_message(
                f"✅ Đã xóa **{removed_track.title}** khỏi playlist **{name}**"
            )
        else:
            await interaction.response.send_message("❌ Không thể xóa bài hát", ephemeral=True)

    @playlist_group.command(name="delete", description="Xóa playlist")
    @app_commands.describe(name="Tên playlist")
    async def playlist_delete(self, interaction: discord.Interaction, name: str):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Chỉ dùng trong server", ephemeral=True)

        success = await PlaylistService.delete_playlist(
            interaction.user.id, interaction.guild.id, name
        )

        if success:
            await interaction.response.send_message(f"🗑️ Đã xóa playlist **{name}**")
        else:
            await interaction.response.send_message(f"❌ Playlist **{name}** không tồn tại", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))

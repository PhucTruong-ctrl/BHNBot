# BHNBot - Option B: Chill Features Implementation Plan

**Date:** 2026-01-08  
**Focus:** Music System + Passive Features for Chill/Healing Server  
**Timeline:** 4-6 weeks  
**Research:** 52+ bots analyzed, Python wavelink code patterns identified

---

## 🎵 MUSIC SYSTEM - REUSABLE CODE SOURCES

### Best Python Music Bot Sources (MIT License - CAN REUSE)

| Source | License | Stars | Best For |
|--------|---------|-------|----------|
| **WannaBeGhoSt/Advanced-Discord-Music-Bot** | MIT | ~100 | Full cog structure, effects |
| **PythonistaGuild/Wavelink** (examples/) | MIT | 398 | Official patterns |
| **devoxin/Lavalink.py** (examples/music.py) | MIT | ~200 | Alternative to wavelink |
| **discord-super-utils** | MIT | ~400 | advance_music_cog.py |

### ⚠️ CANNOT REUSE (Wrong Language/License)
- EvoBot - TypeScript (NOT Python)
- Rawon - TypeScript + AGPL (restrictive)
- aiode - Java

### Recommended Approach
**Clone & Adapt** from `WannaBeGhoSt/Advanced-Discord-Music-Bot`:
- Already structured as discord.py cog
- Has all features we need
- MIT license allows full reuse
- Python 3.10+ compatible

---

## 📋 IMPLEMENTATION ROADMAP

### Phase 1: Music System Core (Week 1-2)

#### 1.1 Infrastructure Setup (Day 1)
```bash
# Install Lavalink server
docker pull ghcr.io/lavalink-devs/lavalink:4
docker run -d --name lavalink -p 2333:2333 \
  -v $(pwd)/application.yml:/opt/Lavalink/application.yml \
  ghcr.io/lavalink-devs/lavalink:4

# Add to requirements.txt
wavelink>=3.0.0
```

**application.yml (Lavalink config):**
```yaml
server:
  port: 2333
  address: 0.0.0.0
lavalink:
  server:
    password: "youshallnotpass"
    sources:
      youtube: true
      soundcloud: true
    filters:
      volume: true
      equalizer: true
      timescale: true
```

#### 1.2 Music Cog Structure (Day 2-3)
```
cogs/music/
├── __init__.py
├── cog.py              # Main commands
├── player.py           # Custom player class
├── views.py            # Now playing controls
├── filters.py          # Audio effects (lofi, vaporwave)
└── playlists.py        # Curated playlists
```

#### 1.3 Core Commands (Day 3-5)

| Command | Description | Priority |
|---------|-------------|----------|
| `/play <query>` | Play song from YouTube/Spotify | 🔴 Critical |
| `/skip` | Skip current song | 🔴 Critical |
| `/stop` | Stop and disconnect | 🔴 Critical |
| `/queue` | View queue | 🔴 Critical |
| `/nowplaying` | Current song with progress | 🔴 Critical |
| `/pause` / `/resume` | Pause/resume playback | 🟡 High |
| `/volume <1-100>` | Set volume | 🟡 High |
| `/shuffle` | Shuffle queue | 🟢 Medium |
| `/loop` | Loop song/queue | 🟢 Medium |

**Code Pattern (from research):**
```python
import wavelink
from discord.ext import commands

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_load(self):
        nodes = [wavelink.Node(uri="http://localhost:2333", password="youshallnotpass")]
        await wavelink.Pool.connect(nodes=nodes, client=self.bot)
    
    @commands.hybrid_command(name="play")
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Bạn phải vào voice channel!")
        
        player = ctx.voice_client or await ctx.author.voice.channel.connect(cls=wavelink.Player)
        
        tracks = await wavelink.Playable.search(query)
        if not tracks:
            return await ctx.send("❌ Không tìm thấy bài hát!")
        
        track = tracks[0]
        await player.queue.put_wait(track)
        
        if not player.playing:
            await player.play(player.queue.get())
        
        await ctx.send(f"🎵 Đã thêm: **{track.title}**")
```

#### 1.4 24/7 Mode (Day 5)
```python
@commands.hybrid_command(name="247")
async def stay_connected(self, ctx):
    """Bật/tắt chế độ 24/7 (không tự rời voice)"""
    player = ctx.voice_client
    if not player:
        return await ctx.send("❌ Bot chưa trong voice!")
    
    player.autoplay = wavelink.AutoPlayMode.enabled
    self.bot.music_247_guilds.add(ctx.guild.id)
    await ctx.send("✅ Đã bật chế độ 24/7! Bot sẽ không tự rời.")
```

#### 1.5 Audio Filters - Chill Effects (Day 6-7)
```python
CHILL_FILTERS = {
    "lofi": wavelink.Filters(
        timescale=wavelink.Timescale(pitch=0.95, rate=0.9),
        equalizer=wavelink.Equalizer(bands=[
            {"band": 0, "gain": 0.2},   # Bass boost
            {"band": 1, "gain": 0.15},
            {"band": 2, "gain": 0.1},
        ])
    ),
    "vaporwave": wavelink.Filters(
        timescale=wavelink.Timescale(pitch=0.8, rate=0.85),
    ),
    "nightcore": wavelink.Filters(
        timescale=wavelink.Timescale(pitch=1.2, rate=1.1),
    ),
    "rain": wavelink.Filters(
        equalizer=wavelink.Equalizer(bands=[
            {"band": 0, "gain": -0.1},  # Reduce bass
            {"band": 5, "gain": 0.1},   # Boost mids
        ])
    ),
}

@commands.hybrid_command(name="filter")
@app_commands.choices(effect=[
    app_commands.Choice(name="🎧 Lo-fi (Chill)", value="lofi"),
    app_commands.Choice(name="🌊 Vaporwave", value="vaporwave"),
    app_commands.Choice(name="⚡ Nightcore", value="nightcore"),
    app_commands.Choice(name="🌧️ Rain Ambience", value="rain"),
    app_commands.Choice(name="🔄 Reset", value="reset"),
])
async def audio_filter(self, ctx, effect: str):
    player = ctx.voice_client
    if effect == "reset":
        await player.set_filters(None)
        return await ctx.send("🔄 Đã reset filter!")
    
    await player.set_filters(CHILL_FILTERS[effect])
    await ctx.send(f"✅ Đã bật filter: **{effect}**")
```

---

### Phase 2: Chill Playlists & Radio (Week 2)

#### 2.1 Curated Playlists
```python
HEALING_PLAYLISTS = {
    "lofi": "https://www.youtube.com/playlist?list=PLOzDu-MXXLliO9fBNZOQTBDddoA3FzZUo",
    "meditation": "https://www.youtube.com/playlist?list=PLQ_PIlf6OzqLGBqKzpTLNmXzHLDSNkz4C",
    "nature": "https://www.youtube.com/playlist?list=PLJicmE8fK0EisZH3nGKWikdXwZl1n7cWR",
    "piano": "https://www.youtube.com/playlist?list=PLMIbmfP_9vb8BCxRoraJpoo4q1yMFg4CE",
    "rain": "https://www.youtube.com/watch?v=mPZkdNFkNps",  # 10hr rain
}

@commands.hybrid_command(name="playlist")
@app_commands.choices(name=[
    app_commands.Choice(name="🎵 Lo-fi Hip Hop", value="lofi"),
    app_commands.Choice(name="🧘 Thiền định", value="meditation"),
    app_commands.Choice(name="🌲 Tiếng thiên nhiên", value="nature"),
    app_commands.Choice(name="🎹 Piano nhẹ nhàng", value="piano"),
    app_commands.Choice(name="🌧️ Tiếng mưa 10 giờ", value="rain"),
])
async def playlist(self, ctx, name: str):
    url = HEALING_PLAYLISTS[name]
    # Load and play playlist
```

#### 2.2 Radio Mode
```python
@commands.hybrid_command(name="radio")
async def radio(self, ctx):
    """Bật radio lo-fi 24/7 với shuffle tự động"""
    player = ctx.voice_client or await ctx.author.voice.channel.connect(cls=wavelink.Player)
    
    tracks = await wavelink.Playable.search(HEALING_PLAYLISTS["lofi"])
    random.shuffle(tracks)
    
    for track in tracks:
        await player.queue.put_wait(track)
    
    player.autoplay = wavelink.AutoPlayMode.enabled
    await player.play(player.queue.get())
    
    await ctx.send("📻 **Radio Lo-fi** đang phát!\nDùng `/skip` để chuyển bài, `/stop` để tắt.")
```

---

### Phase 3: Passive Auto-Fishing (Week 3)

#### 3.1 Database Schema
```sql
CREATE TABLE auto_fishing (
    user_id BIGINT PRIMARY KEY,
    start_time TIMESTAMP,
    duration_hours INT DEFAULT 1,
    efficiency_level INT DEFAULT 1,  -- Fish/hour: 10, 25, 50, 75, 100
    duration_level INT DEFAULT 1,    -- Max hours: 1, 4, 8, 16, 24
    quality_level INT DEFAULT 1,     -- Rare %: 0, 2, 5, 8, 12
    total_essence INT DEFAULT 0,
    last_claim TIMESTAMP
);
```

#### 3.2 Commands
| Command | Description |
|---------|-------------|
| `/auto-fish start <hours>` | Deploy auto-fisher |
| `/auto-fish claim` | Claim caught fish |
| `/auto-fish upgrade` | Upgrade with essence |
| `/auto-fish status` | View progress |

#### 3.3 Upgrade System
```python
UPGRADE_COSTS = {
    "efficiency": [0, 100, 500, 2000, 5000],  # Essence cost per level
    "duration": [0, 200, 1000, 3000, 8000],
    "quality": [0, 300, 1500, 5000, 15000],
}

UPGRADE_VALUES = {
    "efficiency": [10, 25, 50, 75, 100],      # Fish per hour
    "duration": [1, 4, 8, 16, 24],             # Max hours
    "quality": [0, 2, 5, 8, 12],               # Rare fish %
}
```

#### 3.4 Essence System
```python
async def sacrifice_fish(user_id: int, fish_key: str, quantity: int):
    """Sacrifice fish for essence"""
    fish_data = ALL_FISH_DATA[fish_key]
    rarity_multiplier = {"common": 1, "rare": 5, "epic": 25, "legendary": 100}
    essence = quantity * rarity_multiplier[fish_data["rarity"]]
    
    await db_manager.modify(
        "UPDATE auto_fishing SET total_essence = total_essence + ? WHERE user_id = ?",
        (essence, user_id)
    )
    return essence
```

---

### Phase 4: Daily Streaks & Social (Week 4)

#### 4.1 Streak System
```sql
ALTER TABLE users ADD COLUMN daily_streak INT DEFAULT 0;
ALTER TABLE users ADD COLUMN longest_streak INT DEFAULT 0;
ALTER TABLE users ADD COLUMN last_daily TIMESTAMP;
ALTER TABLE users ADD COLUMN streak_protection INT DEFAULT 0;  -- Dream Catcher count
```

#### 4.2 Streak Logic
```python
async def claim_daily(user_id: int) -> dict:
    user = await db_manager.fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))
    
    now = datetime.now()
    last = user["last_daily"]
    streak = user["daily_streak"]
    
    if last:
        hours_since = (now - last).total_seconds() / 3600
        
        if hours_since < 24:
            return {"error": "Bạn đã nhận daily hôm nay rồi!"}
        elif hours_since > 48:
            # Missed day - check protection
            if user["streak_protection"] > 0:
                await db_manager.modify(
                    "UPDATE users SET streak_protection = streak_protection - 1 WHERE user_id = ?",
                    (user_id,)
                )
                streak += 1  # Keep streak
            else:
                streak = 1  # Reset
        else:
            streak += 1
    else:
        streak = 1
    
    # Calculate reward
    base_reward = 10
    streak_bonus = min(streak * 5, 100)  # Max +100 at 20 days
    total = base_reward + streak_bonus
    
    await db_manager.modify(
        "UPDATE users SET seeds = seeds + ?, daily_streak = ?, longest_streak = GREATEST(longest_streak, ?), last_daily = ? WHERE user_id = ?",
        (total, streak, streak, now, user_id)
    )
    
    return {
        "reward": total,
        "streak": streak,
        "bonus": streak_bonus,
        "protection_used": hours_since > 48 if last else False
    }
```

#### 4.3 Shared Daily Bonus
```python
@app_commands.command(name="daily-tang")
async def daily_give(interaction: discord.Interaction, user: discord.User):
    """Tặng daily cho người khác - cả 2 nhận +50% bonus"""
    if user.id == interaction.user.id:
        return await interaction.response.send_message("❌ Không thể tự tặng cho mình!")
    
    # Both get 150% of normal daily
    sender_reward = int(15 * 1.5)  # 22 instead of 10
    receiver_reward = int(15 * 1.5)
    
    await db_manager.modify("UPDATE users SET seeds = seeds + ? WHERE user_id = ?", (sender_reward, interaction.user.id))
    await db_manager.modify("UPDATE users SET seeds = seeds + ? WHERE user_id = ?", (receiver_reward, user.id))
    
    await interaction.response.send_message(
        f"💝 Bạn đã tặng daily cho {user.mention}!\n"
        f"Cả hai nhận **{sender_reward} Hạt** (+50% bonus vì chia sẻ!)"
    )
```

---

### Phase 5: Voice Rewards Enhancement (Week 5)

#### 5.1 Enhanced Voice Tracking
```python
VOICE_REWARDS = {
    "base": 5,           # 5 Hạt per 10 minutes (was 2)
    "streak_bonus": 1,   # +1 per consecutive day
    "max_bonus": 10,     # Max +10 from streaks
    "music_bonus": 2,    # +2 if music playing
}

@commands.Cog.listener()
async def on_voice_state_update(self, member, before, after):
    if after.channel and not before.channel:
        # Joined voice
        self.voice_sessions[member.id] = datetime.now()
    
    elif before.channel and not after.channel:
        # Left voice
        if member.id in self.voice_sessions:
            duration = datetime.now() - self.voice_sessions[member.id]
            minutes = duration.total_seconds() / 60
            
            # Calculate rewards
            intervals = int(minutes / 10)
            if intervals > 0:
                base = intervals * VOICE_REWARDS["base"]
                streak = min(self.get_voice_streak(member.id), VOICE_REWARDS["max_bonus"])
                music = VOICE_REWARDS["music_bonus"] if self.has_music(before.channel) else 0
                
                total = base + (intervals * streak) + (intervals * music)
                await self.add_voice_reward(member.id, total, minutes)
            
            del self.voice_sessions[member.id]
```

#### 5.2 Voice Leaderboard
```python
@app_commands.command(name="voice-top")
async def voice_leaderboard(interaction: discord.Interaction):
    """Top 10 người ở voice nhiều nhất"""
    rows = await db_manager.fetchall(
        "SELECT user_id, total_voice_minutes FROM user_stats ORDER BY total_voice_minutes DESC LIMIT 10"
    )
    
    embed = discord.Embed(title="🎤 Top Voice Time", color=0x5865F2)
    
    for i, (user_id, minutes) in enumerate(rows):
        hours = minutes / 60
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"`{i+1}.`"
        user = await self.bot.fetch_user(user_id)
        embed.add_field(
            name=f"{medal} {user.display_name}",
            value=f"⏱️ {hours:.1f} giờ",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed)
```

---

## 📊 TIMELINE SUMMARY

| Week | Focus | Deliverables |
|------|-------|--------------|
| **Week 1** | Music Core | /play, /skip, /queue, /stop, Lavalink setup |
| **Week 2** | Music Polish | Filters, playlists, 24/7, radio mode |
| **Week 3** | Auto-Fishing | Passive system, essence, upgrades |
| **Week 4** | Daily Streaks | Streak protection, shared daily, marriage foundation |
| **Week 5** | Voice Rewards | Enhanced rewards, streaks, leaderboard |
| **Week 6** | Polish & Test | Bug fixes, balance tuning, documentation |

---

## 🔧 DEPENDENCIES

### Python Packages
```txt
wavelink>=3.0.0
```

### Infrastructure
- **Lavalink Server:** Docker container on port 2333
- **PostgreSQL:** Existing (add new tables)

### Database Changes
```sql
-- Auto-fishing table
CREATE TABLE auto_fishing (...);

-- User columns for streaks
ALTER TABLE users ADD COLUMN daily_streak INT DEFAULT 0;
ALTER TABLE users ADD COLUMN longest_streak INT DEFAULT 0;
ALTER TABLE users ADD COLUMN last_daily TIMESTAMP;
ALTER TABLE users ADD COLUMN streak_protection INT DEFAULT 0;

-- Voice stats
ALTER TABLE user_stats ADD COLUMN total_voice_minutes INT DEFAULT 0;
ALTER TABLE user_stats ADD COLUMN voice_streak INT DEFAULT 0;
```

---

## 🎯 SUCCESS METRICS

### After Implementation
| Metric | Current | Target | Change |
|--------|---------|--------|--------|
| Voice Time | ~10 min/user/day | 30+ min | +200% |
| Daily Active | ~50% | 80% | +60% |
| Message Count | ~100/day | 200+ | +100% |
| Retention (30d) | Unknown | 60%+ | Trackable |

---

## 🚀 IMMEDIATE NEXT STEPS

### Today
1. Setup Lavalink Docker container
2. Install wavelink library
3. Clone music cog structure from research

### Tomorrow
1. Implement /play, /skip, /stop commands
2. Test with YouTube playback
3. Add queue management

### This Week
1. Complete music core (Day 1-5)
2. Add filters and playlists (Day 6-7)
3. Test with real users

---

## 📚 REFERENCE CODE SOURCES

| Feature | Source Repo | File |
|---------|-------------|------|
| Music Cog | WannaBeGhoSt/Advanced-Discord-Music-Bot | cogs/music.py |
| Wavelink Setup | PythonistaGuild/Wavelink | examples/simple.py |
| Filters | Wavelink docs | Filter class |
| Queue | Wavelink | Queue, Playable |

**License Status:** All sources are MIT - safe to copy and adapt.

---

**Plan Created:** 2026-01-08  
**Estimated Effort:** 6 weeks  
**Code Reuse:** ~60% from open-source sources  
**New Code:** ~40% (Vietnamese UI, BHNBot integration)

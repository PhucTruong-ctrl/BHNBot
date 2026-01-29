# BHNBot - Quick Action Guide

**Date:** 2026-01-07  
**Purpose:** Fast reference for next development steps

---

## 🚀 TOP 3 PRIORITIES (Start This Week)

### 1. Music System (Week 1-2) 🎵
**Why:** 90% of chill servers MUST have music

**Quick Start:**
```bash
# Install Lavalink
docker run -d -p 2333:2333 fredboat/lavalink:latest

# Add to requirements.txt
wavelink>=2.0.0
```

**Features to Build:**
- `/play <url>` - YouTube/Spotify playback
- `/lofi` - Auto-play curated lo-fi playlist
- `/247` - Stay in voice 24/7
- Audio filters (vaporwave, ambient)

**Reference Bots:** Wave-Music, aiode

---

### 2. Auto-Fishing System (Week 3) 🧘
**Why:** Passive income = less FOMO

**Database Schema:**
```sql
CREATE TABLE auto_fishing (
    user_id BIGINT PRIMARY KEY,
    start_time TIMESTAMP,
    duration_hours INT,
    efficiency_level INT,  -- Fish per hour (10-100)
    essence_spent INT
);
```

**Commands:**
- `/auto-fish start <hours>` - Deploy auto-fisher
- `/auto-fish check` - See progress
- `/auto-fish upgrade` - Spend essence to improve

**Upgrade System:**
```python
UPGRADES = {
    "efficiency": {1: 10, 5: 50, 10: 100},  # Fish/hour
    "duration": {1: 1, 5: 8, 10: 24},        # Max hours
    "quality": {1: 0, 5: 5, 10: 10}          # Rare %
}
```

**Reference:** OwO HuntBot

---

### 3. Daily Streaks (Week 4) ⭐
**Why:** Every competitor has this

**Database Schema:**
```sql
ALTER TABLE users ADD COLUMN daily_streak INT DEFAULT 0;
ALTER TABLE users ADD COLUMN last_daily TIMESTAMP;

CREATE TABLE items (
    ...
    'dream_catcher': {  -- Streak protection item
        'name': 'Dream Catcher',
        'price': 5000,
        'effect': 'Saves streak if missed 1 day'
    }
);
```

**Logic:**
```python
async def claim_daily(user_id):
    last = get_last_daily(user_id)
    
    # Check streak
    if within_24h(last):
        streak += 1
    elif within_48h(last) and has_item('dream_catcher'):
        # Used protection
        consume_item('dream_catcher')
        streak += 1
    else:
        streak = 1  # Reset
    
    reward = BASE_DAILY + (streak * 5)
    return reward
```

**Reference:** Mantaro, Loritta

---

## 📋 MONTH 1 CHECKLIST

### Week 1-2: Music
- [ ] Setup Lavalink server
- [ ] Install wavelink library
- [ ] Create music cog
- [ ] Add basic commands (play, pause, skip, queue)
- [ ] Add 24/7 mode
- [ ] Add lo-fi filter command
- [ ] Create 3 curated playlists (meditation, lo-fi, nature)
- [ ] Test with 5+ concurrent users

### Week 3: Auto-Fishing
- [ ] Design database schema
- [ ] Create auto-fish deployment system
- [ ] Add essence upgrade currency
- [ ] Build upgrade UI
- [ ] Add notification when auto-fish completes
- [ ] Balance fish rates (prevent inflation)
- [ ] Test with 10 users for 24h

### Week 4: Daily Streaks
- [ ] Add streak columns to users table
- [ ] Create Dream Catcher item
- [ ] Update /chao command with streak logic
- [ ] Add streak display to profile
- [ ] Create shared daily bonus system
- [ ] Add marriage foundation (if time permits)
- [ ] Test streak reset edge cases

---

## 🎨 THEME REALIGNMENT (Quick Fixes)

### Xi Dách / Bầu Cua
```python
# Add practice mode
@app_commands.command(name="xidach-practice")
async def xidach_practice(interaction):
    # Use fake currency
    # Same game, no real loss
    pass

# Add loss protection
FIRST_LOSS_REFUND = 0.5  # 50% back for first 3 losses/day
```

### Fishing Events
```python
# Change bad events to good
EVENTS = {
    "black_cat": {
        "old": "Steals biggest fish",
        "new": "Lucky Cat - Doubles fish"
    },
    "water_snake": {
        "old": "-5% balance",
        "new": "River Spirit - +wisdom buff"
    }
}
```

---

## 📊 METRICS TO TRACK

### Before Changes (Baseline)
- Daily Active Users: ?
- Average voice time: ?
- Messages per day: ?
- Fishing casts per user: ?
- Gambling participation: ?

### After Month 1 (Expected)
- Daily Active Users: +50%
- Average voice time: +100% (music)
- Passive fishing users: 70% of active
- Daily streak participants: 80%

### How to Measure
```python
# Add to database
CREATE TABLE daily_metrics (
    date DATE PRIMARY KEY,
    dau INT,
    total_voice_minutes INT,
    total_messages INT,
    total_fishing_casts INT,
    auto_fish_users INT
);

# Log daily at midnight
@tasks.loop(time=dt_time(hour=0))
async def log_metrics():
    await db.execute("""
        INSERT INTO daily_metrics ...
    """)
```

---

## 💡 QUICK WINS (1-2 Days Each)

### Reputation System
```python
@bot.event
async def on_message(message):
    # Auto-detect thanks
    if "cảm ơn" in message.content and message.mentions:
        for user in message.mentions:
            await add_reputation(user.id, +3, "thanks")
            await message.add_reaction("💖")
```

### Voice Rewards Enhancement
```python
# Increase from 2 to 5 Hạt/10min
VOICE_REWARD = 5  # Was 2

# Add voice streak
voice_streak = get_consecutive_days_in_voice(user_id)
bonus = voice_streak  # +1 per day
total_reward = VOICE_REWARD + bonus
```

### Profile Command
```python
@app_commands.command(name="profile")
async def profile(interaction, user: discord.User = None):
    user = user or interaction.user
    
    embed = discord.Embed(title=f"{user.name}'s Profile")
    embed.add_field(name="Fishing", value=f"{fish_caught} cá")
    embed.add_field(name="Voice", value=f"{hours}h")
    embed.add_field(name="Streak", value=f"{streak} ngày")
    embed.add_field(name="Kindness", value=f"{reputation} ❤️")
    
    await interaction.response.send_message(embed=embed)
```

---

## 🚨 COMMON PITFALLS TO AVOID

### Music System
- ❌ Don't implement without Lavalink (too slow)
- ❌ Don't allow unlimited queue (memory leak)
- ✅ DO implement auto-pause when empty
- ✅ DO add rate limiting (max 5 songs/min per user)

### Auto-Fishing
- ❌ Don't allow infinite duration (server load)
- ❌ Don't make it free (currency inflation)
- ✅ DO require upfront payment
- ✅ DO add server-wide limit (max 100 active)

### Daily Streaks
- ❌ Don't reset at midnight UTC (users sleep)
- ❌ Don't punish harshly for missing (stress)
- ✅ DO use 24h rolling window
- ✅ DO provide streak protection item

---

## 📚 REFERENCE DOCS

| Document | Purpose | Size |
|----------|---------|------|
| `FEATURE_RESEARCH_COMPREHENSIVE.md` | Full analysis of 52 bots | 15,000 words |
| `CURRENT_FEATURES_ANALYSIS.md` | BHNBot inventory | 5,000 words |
| `EXECUTIVE_SUMMARY_VN.md` | Vietnamese summary | 3,000 words |
| `AUDIT_REPORT_2026.md` | Technical health | 11 KB |

---

## 🔗 HELPFUL LINKS

### Music Bots Reference
- [Wave-Music](https://github.com/appujet/Wave-Music)
- [aiode](https://github.com/robinfriedli/aiode)
- [Wavelink Docs](https://wavelink.readthedocs.io/)

### Economy Bots Reference
- [OwO Bot Wiki](https://owobot.fandom.com/)
- [IdleRPG](https://github.com/Gelbpunkt/IdleRPG)
- [Mantaro](https://github.com/Mantaro/MantaroBot)

### Tools
- [Lavalink](https://github.com/freyacodes/Lavalink)
- [Discord.py Docs](https://discordpy.readthedocs.io/)

---

## ✅ COMPLETION CHECKLIST

### This Week
- [ ] Read all research documents
- [ ] Prioritize top 3 features
- [ ] Setup development environment
- [ ] Create Month 1 project board

### Next Week
- [ ] Start music system implementation
- [ ] Design auto-fishing UI mockups
- [ ] Write technical specs
- [ ] Begin coding

---

**Last Updated:** 2026-01-07 23:55 ICT  
**Next Review:** After Month 1 completion  
**Status:** 🚀 READY TO START

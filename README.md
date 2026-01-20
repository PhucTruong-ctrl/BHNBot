<p align="center">
  <img src="assets/logo.png" alt="BHNBot Logo" width="200"/>
</p>

<h1 align="center">🐟 BHNBot</h1>

<p align="center">
  <strong>A comprehensive Vietnamese Discord bot for mental wellness, community engagement, and entertainment</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue.svg" alt="Version"/>
  <img src="https://img.shields.io/badge/python-3.11+-green.svg" alt="Python"/>
  <img src="https://img.shields.io/badge/discord.py-2.6.4-7289da.svg" alt="discord.py"/>
  <img src="https://img.shields.io/badge/license-Proprietary-red.svg" alt="License"/>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#tech-stack">Tech Stack</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#commands">Commands</a> •
  <a href="#admin-panel">Admin Panel</a> •
  <a href="#license">License</a>
</p>

---

## 📖 About

**BHNBot** (Bên Hiên Nhà Bot) is a feature-rich Discord bot designed specifically for Vietnamese communities. It combines entertainment systems like fishing and gambling with mental wellness features, creating a unique space for community engagement and emotional support.

### 🎯 Core Philosophy
- **Community First** - Collaborative features that bring people together
- **Mental Wellness** - Emotional state tracking and supportive interactions
- **Vietnamese Culture** - Traditional games and Vietnamese language support
- **Engagement** - Rich reward systems that encourage daily participation

---

## ✨ Features

### 🎣 Fishing System
The crown jewel of BHNBot - a complete fishing ecosystem:
- **100+ Fish Species** across multiple rarity tiers
- **6 Unique Fishing Rods** with special abilities
- **Legendary Fish Quests** for rare catches
- **Dynamic Events** - Weather, seasons, and special occasions
- **Fishing Disasters** - Risk/reward mechanics
- **Auto-Fishing** - VIP feature for passive income
- **Bait System** - Consumables that affect catch rates

### 💰 Economy System
A balanced virtual economy:
- **Daily Rewards** with streak bonuses (up to 30-day multipliers)
- **Chat Activity Rewards** - XP and coins for participation
- **Voice Channel Tracking** - Rewards for voice activity
- **Welfare System** - Help for new and returning users
- **Interest System** - Savings account with daily interest
- **Multiple Currencies** - Coins and Leaf Coins

### 🎮 Games

| Game | Description |
|------|-------------|
| **🎲 Bầu Cua** | Traditional Vietnamese dice game with multiplayer betting |
| **🃏 Xì Dách** | Vietnamese Blackjack variant with side bets |
| **📝 Nối Từ** | Word chain game with Vietnamese dictionary validation |
| **🐺 Ma Sói** | Complex Werewolf game with **39 unique roles** |

### 🌳 Community Features

- **Community Tree** 🌲
  - Collaborative watering system
  - Seasonal changes and growth stages
  - Prestige system with badges
  - Server-wide goals

- **Aquarium** 🐠
  - Personal aquarium threads
  - Decorations and customization
  - Feng Shui system for bonuses
  - Fish display from catches

- **Social System** 💝
  - Gift giving between users
  - Buddy/friendship system
  - Kindness points tracking
  - Relationship/marriage features

### 🎵 Music System
Powered by Lavalink for high-quality audio:
- YouTube, Spotify, SoundCloud support
- Playlist management
- 24/7 continuous playback mode
- Audio filters (bass boost, nightcore, etc.)
- DJ role permissions
- Queue management with shuffle/loop

### 🎄 Seasonal Events
- **4 Major Seasons** - Spring Festival, Summer Beach, Autumn Harvest, Winter Holiday
- **16+ Unique Minigames** per event
- **Community Goals** with server-wide rewards
- **Limited-Time Collectibles** and achievements
- **Event Currencies** and exclusive items

### ⭐ VIP System
Three-tier membership with escalating benefits:

| Tier | Benefits |
|------|----------|
| 🥉 **Bronze** | 10% cashback, exclusive fish access |
| 🥈 **Silver** | 15% cashback, auto-fishing, enhanced daily |
| 🥇 **Gold** | 25% cashback, all features, priority support |

### 📊 Profile & Achievements
- Customizable user profiles
- Achievement system with badges
- Daily/weekly quest system
- Server leaderboards
- Statistics tracking

### 🛡️ Admin Features
- Comprehensive moderation tools
- Server configuration
- User management
- Backup/restore system
- Health monitoring

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| Python 3.11+ | Core runtime |
| discord.py 2.6.4 | Discord API wrapper |
| aiosqlite | Async SQLite for local data |
| asyncpg | PostgreSQL for production |
| wavelink | Lavalink client for music |
| aiohttp | Async HTTP client |

### Web Admin Panel
| Technology | Purpose |
|------------|---------|
| FastAPI | REST API backend |
| React 18 | Frontend framework |
| TypeScript | Type-safe frontend |
| Vite | Build tool |
| TailwindCSS | Styling |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Lavalink | Audio streaming |
| Redis | Caching layer |
| PostgreSQL | Production database |
| Grafana | Metrics visualization |
| Loki | Log aggregation |
| Tempo | Distributed tracing |

---

## 🏗️ Architecture

```
BHNBot/
├── cogs/                   # Discord bot modules (17 cogs)
│   ├── fishing/            # Fishing ecosystem
│   ├── economy/            # Economy & rewards
│   ├── music/              # Music playback
│   ├── games/              # Bầu Cua, Xì Dách, etc.
│   ├── social/             # Gifts, buddy system
│   ├── aquarium/           # Personal aquariums
│   ├── tree/               # Community tree
│   ├── seasonal/           # Seasonal events
│   ├── werewolf/           # Ma Sói game
│   ├── vip/                # VIP system
│   ├── admin/              # Admin commands
│   └── ...                 # Other modules
├── core/                   # Shared utilities
│   ├── database.py         # Database connections
│   ├── logging.py          # Logging configuration
│   └── utils.py            # Helper functions
├── web/                    # Admin panel
│   ├── routers/            # API endpoints
│   ├── frontend/           # React application
│   └── main.py             # FastAPI app
├── data/                   # Static data files
├── configs/                # Configuration files
├── infra/                  # Docker & infrastructure
├── docs/                   # Documentation
└── main.py                 # Bot entry point
```

### Design Patterns
- **Cog-based Architecture** - Modular feature separation
- **4-Layer Pattern** - Controller → Service → Core → Repository
- **Event-Driven** - Pub/sub for cross-cog communication
- **Dependency Injection** - Testable and maintainable code

---

## 📋 Commands

### Quick Reference

| Category | Commands | Description |
|----------|----------|-------------|
| 🎣 Fishing | `/fish`, `/rod`, `/bait`, `/inventory` | Fishing system |
| 💰 Economy | `/daily`, `/balance`, `/pay`, `/shop` | Currency & rewards |
| 🎮 Games | `/baucua`, `/xidach`, `/noitu`, `/masoi` | Minigames |
| 🌳 Community | `/tree`, `/aquarium`, `/gift`, `/buddy` | Social features |
| 🎵 Music | `/play`, `/queue`, `/skip`, `/volume` | Music playback |
| ⭐ VIP | `/vip` | VIP status & benefits |
| 👤 Profile | `/profile`, `/achievements`, `/quests` | User profile |
| 🛡️ Admin | `/config`, `/backup`, `/sync` | Administration |

> **Note:** Use `/help [category]` in Discord for detailed command information.

---

## 🖥️ Admin Panel

BHNBot includes a secure web-based admin panel:

### Features
- 📊 Real-time bot statistics
- 👥 User management
- ⚙️ Server configuration
- 📝 Audit logging
- 🔍 Log viewer with search
- 📈 Grafana integration
- 🔐 Discord OAuth2 authentication

### Access
The admin panel runs on port `8080` by default and requires authentication via Discord OAuth2. Only users listed in `ADMIN_USER_IDS` can access the panel.

---

## 📊 Statistics

- **17** Cog modules
- **70+** Slash commands
- **100+** Fish species
- **39** Werewolf roles
- **16+** Seasonal minigames
- **4** Major seasonal events

---

## 🔒 Security

BHNBot implements comprehensive security measures:

- ✅ All admin endpoints require authentication
- ✅ JWT-based session management
- ✅ Parameterized SQL queries (no injection)
- ✅ Input validation and sanitization
- ✅ Rate limiting on sensitive endpoints
- ✅ Audit logging for admin actions
- ✅ CORS configuration for web panel
- ✅ No secrets in codebase

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [COGS_REFERENCE.md](docs/COGS_REFERENCE.md) | Technical reference for all cogs |
| [FEATURE_RESEARCH.md](docs/FEATURE_RESEARCH_COMPREHENSIVE.md) | Feature analysis and roadmap |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

---

## 🗺️ Roadmap

### v1.x (Current)
- ✅ Core fishing system
- ✅ Economy & rewards
- ✅ Games (Bầu Cua, Xì Dách, Werewolf)
- ✅ Music system
- ✅ VIP tiers
- ✅ Admin panel

### v2.x (Planned)
- 🔄 Pet/Companion System
- 🔄 Enhanced Profile Customization
- 🔄 Marketplace/Trading
- 🔄 Healing Council AI
- 🔄 Mobile-responsive dashboard

---

## 🔧 Quick Reference (Development)

### Start Bot with Admin Panel
```bash
cd /home/phuctruong/Work/BHNBot && .venv/bin/python3 main.py
```

### Start Admin Panel Only
```bash
./scripts/start_admin.sh
# or
.venv/bin/python3 -m uvicorn web.main:app --host 0.0.0.0 --port 8080
```

### Health Check
```bash
bash scripts/monitor_health.sh
```

### Restore Database
```bash
cp ./data/backups/auto/database_auto_YYYYMMDD_HHMMSS.db ./data/database.db
sudo systemctl restart discordbot
```

---

## ⚖️ License

**PROPRIETARY SOFTWARE - ALL RIGHTS RESERVED**

This software is proprietary and confidential. No license is granted for use, modification, or distribution without explicit written permission.

See [LICENSE](LICENSE) for full terms.

---

## 👥 Credits

- **Development**: BHNBot Team
- **Framework**: [discord.py](https://github.com/Rapptz/discord.py)
- **Music**: [Lavalink](https://github.com/lavalink-devs/Lavalink)
- **Inspiration**: Vietnamese Discord community

---

<p align="center">
  Made with ❤️ for Vietnamese Discord communities
</p>

<p align="center">
  <sub>Copyright © 2024-2026 BHNBot. All Rights Reserved.</sub>
</p>

# Changelog

All notable changes to BHNBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Total Commits:** 332 | **Development Period:** Dec 11, 2025 → Jan 20, 2026

---

## [1.0.0] - 2026-01-20

### 🎉 Stable Release - Production Ready

The first major stable release of BHNBot with comprehensive logging, observability, and security hardening.

### Added
- `feat(logging): add structlog-based structured logging module` - 573a1ff
- `feat(telemetry): add OpenTelemetry SDK and command tracing` - b5e02fb
- `feat(infra): add Loki, Tempo, Grafana observability stack` - e78a665
- `feat(logging): implement dual format logging and Loki dashboard integration` - 2ca09ab
- `feat(main): integrate web server lifecycle with bot startup/shutdown` - 2b8194b
- `docs: add comprehensive README, LICENSE, CHANGELOG, and version 1.0.0` - b62359e

### Changed
- `refactor(logging): migrate 58 files from core.logger to core.logging` - 8f37b01
- `refactor(logging): complete migration to structured logging` - 6a2a398
- `refactor(web): centralize auth config and fix JWT_SECRET duplication` - c3ae763

### Fixed
- `fix(logging): resolve circular import and infinite recursion in core.logging` - 3418f4f
- `fix(logging): auto-append /loki/api/v1/push to LOKI_URL` - 220e44d
- `fix(logging): integrate Loki handler into QueueListener pipeline` - 56497ab
- `fix(logging): correct invalid logger kwargs syntax from migration` - acfb5df
- `fix(cogs): resolve F821 undefined name errors across 12 files` - 30b003a
- `fix(logging): remove emoji from console output and fix level padding` - f722a5a
- `fix(web): add missing Depends import to all router files` - 0e40d4d

### Security
- `security(web): add authentication to all admin endpoints and fix vulnerabilities` - 60aa267
  - Added `require_admin` dependency to ALL admin routers (10 files)
  - Removed stack trace exposure in global exception handler
  - Made CORS configurable via `CORS_ALLOWED_ORIGINS` env var

---

## [0.9.0] - 2026-01-17

### 🎄 Seasonal Events & Social Features

Complete seasonal event system and social/relationship features.

### Added

#### Seasonal Events System
- `feat(seasonal): add complete seasonal events system with Docker lifecycle` - 64ce10d
- `feat: Add seasonal minigames for treasure hunt, trick or treat, and birthday wishes` - e7f4873
- `feat(seasonal): improve boat_race and add logging to all minigames` - d7e4511
- `feat(seasonal): add seasonal achievements and enhance event handling` - 4be70eb
- `feat(tests): add comprehensive test commands for seasonal events` - 0ddb5d7
- `docs: update seasonal events testing guide with complete minigame trigger table` - ce7c7c5

#### Social & Relationship System
- `feat(profile): add Social & Profile modules with full customization` - fc03f92
- `feat(relationship): add /banthan buddy system with Vietnamese commands` - 68ee39c
- `feat(social): add kindness streak system with multipliers` - 54cc864
- `feat(social): add voice rewards system (10 Hạt/10 min)` - 3193525
- `feat(quest): add server-wide daily quests system` - 698b733
- `feat(quest): add admin test commands for morning/evening triggers` - 5936939

### Changed
- `refactor(fishing): extract _fish_action to commands/fish.py, add FishingStateManager` - d999193
- `refactor(fishing): centralize all Views into ui/ layer` - 3b3345f
- `refactor(commands): merge /sukien nhiemvu into /nhiemvu` - f6f30e3
- `refactor: modularize minigame configurations to use event-based settings` - 04878d9

### Fixed
- `fix(seasonal): resolve CommandAlreadyRegistered and missing setup errors` - 28ed8a6
- `fix(seasonal): update database queries and add migration for quest_type column` - 90b0340
- `fix(quests): update quest description handling` - 4272fb0
- `fix(quests): prevent duplicate quest types during seasonal events` - 0ddb5d7
- `fix(quests): prioritize non-overlapping types instead of removing them` - 99cd6ea
- `fix(profile): remove old /hoso from general.py, add setup() to new cogs` - d999193
- `fix(relationship): remove duplicate banthan command registration` - 24e13e7
- `fix(logger): re-enable Discord error ping notification` - 600ce67
- `fix(monitor): use run_in_executor for importlib.reload to prevent event loop blocking` - 41edcc7
- `fix(logger): reuse file handlers to prevent rotation race condition` - faa8abb

### Performance
- `perf: add centralized JSON cache and fix blocking I/O across cogs` - 41edcc7

---

## [0.8.0] - 2026-01-08

### ⭐ VIP System & Aquarium

Premium VIP system with three tiers and personal aquarium feature.

### Added

#### VIP System
- `feat: add VIP tier configurations and quotes, integrating them into fishing and selling features` - 6c1a13d
- `feat: add VIP premium items and dedicated commands` - 6a91ced
- `feat: Introduce VIP fish display badges, implement multi-catch premium buff, and allow negative luck values` - 5a807f6
- `feat: add VIP-specific win messages and instant cashback info to Bau Cua game summary` - e983b01
- `feat(vip): complete VIP Phase 2-3 with Enhanced Gifting and Confirmation Modal` - b98ba40
- `feat: Implement gift cooldown for tangqua command` - 2c51b39
- `docs: create comprehensive VIP system testing guide` - c7c9253

#### Aquarium System
- `feat: Implement full Aquarium UI/Controller and fix Schema` - 8f3d663
- `feat: add aquarium forum channel configuration and database migration scripts` - 6c1a13d
- `feat: Implement aquarium themes and refine tree contribution mechanics with bonus EXP` - e983b01

#### Auto-Fishing & Tournaments
- `feat(auto-fishing): add auto-fishing module + update docs` - 19b1401
- `feat: introduce user-hosted fishing tournament system with dedicated commands` - f10eb95
- `feat: Implement TournamentManager as a singleton, add channel ID to tournament creation` - c7c9253

#### Unified Shop
- `feat: implement unified shop for purchasing decor items and rod upgrades` - a80ad38

### Changed
- `refactor: standardize VIP embed content using fields and update VIPEngine import path` - 2eb7caa
- `refactor: update message sending helper to conditionally include view argument` - 36111f0

### Fixed
- `fix: Prevent fishing embed footer glitch from overwriting VIP quotes` - eec07d6
- `feat: Expand VIP_QUOTES with new categorized and culturally relevant sayings` - 2eb7caa

---

## [0.7.0] - 2025-12-31

### 🃏 Xì Dách Game & Web Admin Panel

Vietnamese Blackjack game and comprehensive web-based admin dashboard.

### Added

#### Xì Dách (Vietnamese Blackjack)
- `feat(xi-dach): implement Vietnamese Blackjack game cog with UI and game logic` - 49f43b4
- `feat: Implement the Xi Dach card game with a modular architecture` - 51ae9e8
- `feat: implement comprehensive Xi Dach hand evaluation logic` - 7924ff2
- `feat: introduce all-in and cancel bet options for Xi Dach` - d316f36
- `feat: enhance Xi Dach game UI with richer instant win, player turn, and dealer result embeds` - 3000405
- `feat: Add Xì Dách game assets and implement robust message handling` - 12831cd
- `feat: reduce Xi Dach card and layout dimensions for a more compact UI` - 622e80f
- `feat: Add Xi Dach statistics command and implement detailed transaction logging` - 0dd5206
- `feat: Implement loss for timed-out bust players in xi_dach` - 30b36bd

#### Web Admin Panel
- `feat: implement web-based admin panel for bot management and configuration` - 7ba311d
- `chore(frontend): Configure Vite development server host` - d9e7ab6
- `feat: Implement dark/light theme toggle and Catppuccin palettes for the admin panel` - 71f87cb
- `feat: introduce server health monitoring UI and API` - 1c02c6e
- `feat: Display CPU model name in server health UI and API` - 10b8823
- `feat(web): add Bot Logs page and fix dashboard errors` - 078e0b3
- `feat: reimplement role management with dynamic category roles stored in DB and a new web panel UI` - 4d4904f
- `feat: Implement cashflow API endpoint with transaction logging` - cb5a6bf
- `feat: Enhance dashboard charts by expanding the color palette` - 2ee62a3
- `feat: Add Discord logging configurable via database` - eff7e4c

### Changed
- `refactor: Update database import path and query execution` - 677cee9
- `chore: Remove various old scripts and tests` - 677cee9

### Fixed
- `fix: Correct Xi Dach table removal, add error handling to game resolution` - 7e337bd
- `fix: Implement background cleanup for stale Xi Dach tables` - 63410ce
- `fix: Correctly retrieve username in sell command using the aliased context object` - 4d194ea
- `fix: Correct transaction_logs parameter order and refactor emotional state name retrieval` - 622e80f

---

## [0.6.0] - 2025-12-27

### 🐉 Legendary Quests & Database Restructure

Legendary fish quest system and major database architecture improvements.

### Added

#### Legendary Quests & Events
- `feat(database): Implement legendary quests tracking and management` - 748c0fa
- `feat: Implement new global and NPC event mechanics, including dragon quest contributions` - e82fc11
- `feat: Implement Phoenix Egg mini-game` - 30b36bd
- `feat: Add "Bản đồ hắc ám" consumable to activate special legendary fish encounters` - 6692cb2

#### Database Improvements
- `feat(database): Implement new modular schema for user and game data` - e60e69a
- `feat(database): update schema for giveaways and game sessions` - 8b1bcca
- `feat: migrate web panel database from SQLite to PostgreSQL` - fd4ac99
- `feat: enable database WAL mode, add migration and backup scripts` - 431f625
- `feat: Implement WAL-safe database backup using SQLite API` - 0757276
- `feat: introduce database migration scripts, reorganize admin commands` - f7dc860

#### Item System Overhaul
- `feat: Implement a centralized item system loading categorized data from multiple JSON files` - 01209d9
- `refactor: standardize item identifiers using ItemKeys across fishing and core modules` - 1e6e6f5

### Changed
- `refactor: update economy transaction categories to be game-specific` - c5d6c9f
- `refactor: introduce inventory caching and update item management functions` - 529e2ed
- `refactor: centralize interaction deferral to views and update command responses` - fcbf50b

### Fixed
- `fix: Correct UPSERT syntax in inventory updates` - 9406720
- `fix: Await the asynchronous get_game method call in the config cog` - 91bac43
- `fix: improve interaction deferral error handling` - e9005db

### Performance
- `perf: Cache disaster and sell event configurations and add timeout to global disaster checks` - 410317b
- `feat: Implement watchdog to prevent user lock deadlocks` - 3bcd692

---

## [0.5.0] - 2025-12-23

### 🎁 Giveaway System & Disasters

Giveaway feature and global disaster event system.

### Added

#### Giveaway System
- `feat(giveaway): Implement giveaway system with participant requirements and winner selection` - ec2c379
- `feat: Add user achievements table for persistent tracking` - a98ce93

#### Disaster System
- `feat: implement global disaster system with various calamities and effects` - 6427c3b
- `feat(glitch): Implement global display glitch for fish names during Hacker Attack` - d7d18df
- `fix(disaster_events): increase catch rate penalty for environmental disaster` - 67d7ad7

#### Fishing Improvements
- `feat: enhance chest loot system with new "nothing" outcome and trash item integration` - b44a8c1
- `feat: add public announcement for user losses in fishing events` - bc7b334
- `feat: cap negative fishing event losses and implement Sixth Sense protection` - 06e7c6d
- `feat: Add Hạt rewards to fishing events` - bf5ca57

### Changed
- `feat(database): enhance tree_contributors table to track seasonal contributions` - 5db6a5f
- `refactor: Rename noi_tu cog file from noitu.py to cog.py` - 9b51b49

### Fixed
- `fix: prevent duplicate 'Cá Isekai' acquisition from 'Truck-kun' event` - 01209d9

---

## [0.4.0] - 2025-12-22

### 🎣 Complete Fishing System

Full fishing ecosystem with rods, events, consumables, and collection tracking.

### Added

#### Core Fishing
- `feat(fishing): add fishing mechanics with loot tables, inventory management, and sell functionality` - 2e4701a
- `feat(fishing): add notification embed for fertilizer usage and tree level up` - eb8a596
- `feat(fishing): add event protection mechanism to avoid negative outcomes` - afd06c1
- `feat(fishing): implement fish bucket limit and update event messages` - a0e22d8
- `feat: Implement fishing system enhancements: add random event triggers, legendary fish mechanics, rod durability management` - a1defdb

#### Rods & Equipment
- `feat: Add fishing rod columns to economy_users table` - 39b62d5
- `feat: add new rod levels 6 and 7 with special upgrade requirements and a no-bait-loss passive` - f2d6bd8
- `feat: Add a new paginated fishing collection view with progress and mark newly caught fish` - 07ca297

#### Consumables & Items
- `feat: add consumable items system with usage commands` - 7f9d77e
- `feat: Add legendary fish data, NPC events, and sell events with detailed descriptions` - 62123b4

#### Events & Interactions
- `feat: Implement interactive sell events, global event management, and balancing tools` - 89fc721
- `feat: add missing events to fishing events` - 848c4b6
- `feat: Implement persistent user buffs and integrate luck into fishing event mechanics` - 67f8c95
- `chore: update NPC event data` - 8849b2c
- `feat: Introduce 'Crypto Pump' fishing event with capped percentage-based seed gain` - c085dd5

#### UI Improvements
- `feat: Redesign fishing embeds, add inventory display command, implement database backup` - d7d81de
- `feat: Redesign sell command output to a detailed receipt` - 288c87f
- `feat: Enable bulk opening of treasure chests` - 40c7ce6
- `feat: Add custom trash item keys, refactor fishing trash processing` - 857cb6b
- `feat: Display detailed puzzle piece breakdown, implement greedy auto-claim for full sets` - aa86939

### Changed
- `refactor: Restructure fishing system by modularizing mechanics, commands, and utilities into dedicated submodules` - 14aaf11
- `refactor: Move fishing cog deferral and context assignment logic` - 8bb6c46

### Fixed
- `fix: update get_fish_count to return 1 if fish is caught, 0 if not` - ec9feae
- `fix trash recycle` - 204cc77
- `fix trash recycle to give fertilizer instead` - e36ea2c
- `fix: Remove redundant import of ALL_ITEMS_DATA to resolve UnboundLocalError` - 2ef82d4
- `fix: Prioritize event-defined durability loss in fishing` - dfc23f8

---

## [0.3.0] - 2025-12-16

### 💰 Economy & Community Tree

Virtual economy system and collaborative community tree feature.

### Added

#### Economy System
- `feat: Add economy, shop, and interaction cogs` - 9be6223
- `refactor: Refactor economy to remove XP and level tracking` - 9b56f04
- `feat: Update economy user schema and buff description` - b0ff6e5

#### Community Tree
- `feat: Add community tree feature and harvest buff system` - 13d0dd4
- `feat: Add season-based scaling to tree level requirements` - d5620b3
- `feat: Add tree configuration JSON with names, descriptions, images` - 08aab23
- `feat(database): add contribution_exp column to tree_contributors table` - 495a2f2

#### Profile System
- `feat: Add voice affinity task and redesign profile card` - 5a9705d
- `feat: Add new assets and redesign profile card` - 63267fa

#### Database Enhancements
- `feat: Enhance database initialization and optimization` - 44ffa13
- `feat: Add game_sessions table to store game state for resuming sessions` - 134a263
- `feat: Refactor database initialization and add new achievement tracking columns` - 66eb376

### Changed
- `refactor: Refactor and expand bot features, update help and tree UI` - 3d3e39c
- `refactor: Remove set_tree_channel admin command` - b886114

### Fixed
- `fix: Initialize database and setup folder before starting the bot` - 5db5d72

---

## [0.2.0] - 2025-12-15

### 🐺 Werewolf Game (Ma Sói)

Complete Werewolf social deduction game with 39 unique roles.

### Added

#### Core Game Engine
- `feat: Add Werewolf game module and improve bot features` - e3cc654
- `refactor: Refactor Werewolf game into modular engine structure` - fc67c9d
- `feat: Enhance game flow, role handling, and logging` - 479021d
- `feat: Add mayor tie-break and update role images` - 8fe89b9
- `feat: Add voice mode and dynamic role config to Werewolf` - 67624cf
- `feat: Add dynamic day phases and point-based role balancing` - 52d9071
- `feat: Revamp discussion skip vote and update timings` - 85262a7

#### Villager Roles (20 roles)
- `feat: Add Two Sisters role with coordination mechanics` - ccebbaf
- `feat: Add Moon Maiden and Hypnotist roles` - 38ae33a
- `feat: Add Pharmacist role with antidote and sleeping potion` - 26a58b6
- `feat: Add Cavalry role with day phase ability` - 0a7170c
- `feat: Add Avenger role and integrate with game logic` - 5c2f480
- `feat: Add Judge and Actor roles` - 7089304
- `feat: Add Elder Man role with custom win condition` - 8fe684b
- `feat: Add Bear Tamer role` - 12d4a57
- `feat: Add Devoted Servant and Fox roles` - ecc7588
- `feat: Implement Devoted Servant rulebook edge cases` - a7b21ae

#### Werewolf Roles (10 roles)
- `feat: Add Angel of Death role and improve game robustness` - ff9e92a
- `feat: Add Fire Wolf role with skill disabling ability` - 9f3cfac
- `feat: Add Wolf Brother & Sister roles with pairing and transformation logic` - 008d20a
- `feat: Add Assassin role with 2-day vote-triggered kill ability` - 6b0c1fc

#### Third Party Roles (9 roles)
- `feat: Add new roles and multi-role support` - 31f9aab
- `feat: Improve logging and add Fox night action logic` - 024e59a

#### Documentation
- `feat: Add werewolf role guide and update role configs` - c489239
- `feat: Add werewolf guide command and refactor guide cog` - 2696e8d
- `feat: Add dramatic in-game announcements for Idiot and Hunter roles` - 8c1812b

### Changed
- `refactor: Improve logging and role naming in Werewolf game` - abf72ff
- `refactor: Refactor config and werewolf commands, update data` - 92bcba3
- `feat: Prevent channel conflicts between Werewolf and NoiTu games` - 161965e

### Fixed
- `fix: Fix role state copying and permission reset bugs` - e203ddb
- `feat: Add logging to werewolf role classes for debugging` - 4f393e8

---

## [0.1.0] - 2025-12-11

### 🎮 Initial Release - Nối Từ Game

First version of BHNBot with Vietnamese word chain game.

### Added

#### Core Bot
- `first commit` - 74c4924
- `first commit` - 72dfd1d

#### Nối Từ (Word Chain Game)
- `feat: Add dictionary cog and improve word game logic` - ab8081a
- `refactor: Refactor config and dictionary cogs, enhance word game` - eea0dde
- `feat: Add memory-based word dictionary and word addition feature` - 50d60c0
- `feat: Add ranking, stats, and help features to game bot` - 56041f3

#### Admin Tools
- `feat: Add admin cog and improve reset command handling` - 33a8055

---

## [Unreleased]

### Planned for v2.x
- Pet/Companion System
- Enhanced Profile Customization with themes
- Marketplace/Trading System
- Healing Council AI Integration
- Mobile-responsive web dashboard improvements
- Advanced analytics and reporting

---

## Version Summary

| Version | Date | Commits | Major Features |
|---------|------|---------|----------------|
| 1.0.0 | 2026-01-20 | 17 | Logging, Telemetry, Security, Production Ready |
| 0.9.0 | 2026-01-17 | 35 | Seasonal Events, Social, Quests, Voice Rewards |
| 0.8.0 | 2026-01-08 | 28 | VIP System, Aquarium, Auto-Fishing, Tournaments |
| 0.7.0 | 2025-12-31 | 32 | Xì Dách Game, Web Admin Panel |
| 0.6.0 | 2025-12-27 | 25 | Legendary Quests, Database Migration, Item System |
| 0.5.0 | 2025-12-23 | 15 | Giveaway, Disasters, Fishing Events |
| 0.4.0 | 2025-12-22 | 85 | Complete Fishing System, Consumables |
| 0.3.0 | 2025-12-16 | 20 | Economy, Community Tree, Profile |
| 0.2.0 | 2025-12-15 | 35 | Werewolf (39 roles) |
| 0.1.0 | 2025-12-11 | 8 | Initial, Nối Từ Game |
| **Total** | **41 days** | **332** | **Full-featured Discord Bot** |

---

## Commit Statistics

### By Category
- **feat:** 180+ (New features)
- **fix:** 60+ (Bug fixes)
- **refactor:** 45+ (Code improvements)
- **docs:** 15+ (Documentation)
- **chore:** 20+ (Maintenance)
- **perf:** 5+ (Performance)
- **security:** 2 (Security fixes)

### By Module
- **Fishing:** 85+ commits
- **Werewolf:** 35 commits
- **Economy/Tree:** 25 commits
- **Web Panel:** 20 commits
- **Games (Bầu Cua, Xì Dách):** 30 commits
- **VIP System:** 15 commits
- **Seasonal Events:** 20 commits
- **Logging/Infra:** 15 commits
- **Database:** 25 commits
- **Core/Utils:** 40 commits

---

[1.0.0]: https://github.com/BHNBot/BHNBot/releases/tag/v1.0.0
[0.9.0]: https://github.com/BHNBot/BHNBot/releases/tag/v0.9.0
[0.8.0]: https://github.com/BHNBot/BHNBot/releases/tag/v0.8.0
[0.7.0]: https://github.com/BHNBot/BHNBot/releases/tag/v0.7.0
[0.6.0]: https://github.com/BHNBot/BHNBot/releases/tag/v0.6.0
[0.5.0]: https://github.com/BHNBot/BHNBot/releases/tag/v0.5.0
[0.4.0]: https://github.com/BHNBot/BHNBot/releases/tag/v0.4.0
[0.3.0]: https://github.com/BHNBot/BHNBot/releases/tag/v0.3.0
[0.2.0]: https://github.com/BHNBot/BHNBot/releases/tag/v0.2.0
[0.1.0]: https://github.com/BHNBot/BHNBot/releases/tag/v0.1.0

# BHNBot - Current Features Analysis

**Date:** 2026-01-07  
**Purpose:** Complete feature inventory for enhancement research  
**Theme:** Chill/Healing Community Server

---

## 📊 CURRENT FEATURES BREAKDOWN

### 🎣 1. FISHING SYSTEM (Core Module - 3,000+ lines)

**Complexity:** Very High  
**Engagement:** High (Primary activity loop)

#### Core Mechanics
- **Fishing Command** (`/cauca`): Cast fishing rod with cooldown-based progression
- **Bait System**: Auto-buy worm (mồi) if user has money, otherwise trash fishing
- **Rod Progression**: 7 rod levels with different stats:
  - Cooldown times (60s → 2s at max level)
  - Durability system (breaks after use)
  - Repair costs scaling with level
  - Passive abilities (e.g., Chrono Rod preserves bait 10% chance)

#### Collection System
- **Fish Rarity Tiers**: Common, Rare, Epic, Legendary
- **Legendary Fish**: 4 unique fish with boss battles
  - Cá Ngân Hà (Galaxy Fish)
  - Cthulhu Con (Eldritch Horror)
  - Cá Phượng Hoàng (Phoenix Fish)
  - Cá Voi 52Hz (Lonely Whale)
- **Collection Completion**: Rewards for catching all fish in tier
- **Aquarium Display**: Visual showcase of collection

#### Random Events (30+ events)
- **Good Events**: Double Rainbow (luck buff), Golden Turtle (cooldown reset), Crypto Pump (+5% balance)
- **Bad Events**: Shark Bite (cooldown penalty), Water Snake (-5% balance), Equipment Break
- **NPC Events**: Special encounters with unique rewards/costs
- **Global Disasters**: Server-wide events triggered by players (0.05% chance)
  - Police Raid (fine for all casters)
  - Hacker Attack (display glitch effect)
  - Cable Cut (cooldown increase)

#### Economy Integration
- **Selling System**: Interactive UI to sell fish with buffs
- **Trash Recycling**: Convert trash to bonus items
- **Chest System**: Lootboxes from fishing
- **Crafting**: Create higher-tier items from fish

#### Emotional State System
- **Buffs**: Lucky, Keo Ly (2x sell price), Sixth Sense (avoid bad event)
- **Debuffs**: Suy (50% rare reduction), Lag (3s delay per cast)
- **Duration-based**: Timed buffs (5 casts or 10 minutes)

#### Social Features
- **Tournaments**: Competitive events with rankings
- **Leaderboards**: Top fishers by fish count
- **Achievements**: Unlock titles based on stats

---

### 💰 2. ECONOMY SYSTEM

**Complexity:** Medium  
**Currency:** Hạt (Seeds)

#### Income Sources
- **Daily Reward** (`/chao`): 10 Hạt (5-10 AM window only)
- **Chat Activity**: 1-3 Hạt per message (60s cooldown)
- **Voice Activity**: 2 Hạt per 10 minutes in voice channel
- **Fishing**: Primary income (selling fish)
- **Weekly Welfare**: 100 Hạt for active poor users

#### Currency Sinks
- **Shop Purchases**: Items, bait, consumables
- **Fishing Costs**: Rod repairs, bait
- **Gambling**: Xi Dách, Bầu Cua
- **Crafting**: Resource requirements

#### Balance Features
- **Leaderboard** (`/bang-xep-hang`): Top 10 richest users
- **Balance Check**: View current Hạt

---

### 🛒 3. UNIFIED SHOP SYSTEM

**Complexity:** Medium  
**Items:** 50+ purchasable items

#### Item Categories
- **Consumables**: Bait, fertilizer, buffs
- **Gifts**: Coffee, flowers, chocolate, rings, cards
- **Crafting Materials**: Various fish-related items
- **Premium Items**: VIP-exclusive purchases

#### Shop Features
- **Dynamic Pricing**: Some items have variable costs
- **Stock System**: Some items limited availability
- **Buyback**: (if implemented)
- **Bundle Deals**: (potential feature)

---

### 🎲 4. GAMBLING SYSTEMS

#### Xi Dách (Card Game)
**Complexity:** High  
**Type:** Visual card game with betting

- **Mechanics**: Multi-round betting game with Vietnamese card deck
- **UI**: Custom card rendering with Pillow
- **Bet Limits**: Configurable min/max
- **Multiplayer**: Interactive button-based gameplay

#### Bầu Cua (Dice Game)
**Complexity:** Medium  
**Type:** Traditional Vietnamese dice game

- **Mechanics**: Bet on 6 symbols, 3 dice rolled
- **Visual**: Dice animation/display
- **Payouts**: Match-based rewards

---

### 🐺 5. WEREWOLF (Ma Sói)

**Complexity:** Very High (8,883 lines)  
**Architecture:** Excellent (8/10 score from audit)

#### Game Features
- **39 Unique Roles**: Werewolves, Villagers, Neutrals
- **Turn-Based Gameplay**: Night → Day → Voting cycles
- **Voice + Text Channels**: Dedicated category per game
- **Thread System**: Wolf thread, dead thread, main discussion
- **Phase Management**: Lobby → Night → Day → Vote → Finish

#### Social Features
- **Host Controls**: Configurable game settings
- **Expansion Packs**: New Moon, The Village
- **Player Permissions**: Dynamic channel access based on alive/dead status
- **Spectator Mode**: Dead players can watch

---

### 🌳 6. COMMUNITY TREE SYSTEM

**Complexity:** Medium-High  
**Type:** Server-wide collaborative growth

#### Tree Mechanics
- **6 Growth Levels**: Progressive requirements (100 → 500 → 1500 → 3000 → 5000 → 7500 seeds)
- **Seasonal Cycle**: 4 seasons with visual changes
- **Watering System**: Users contribute seeds to grow tree
- **Auto-Water**: VIP feature for passive contribution

#### Harvest System
- **Level 6 Harvest**: Unlocks 24h server-wide fishing boost
- **Harvest Cooldown**: 72 hours between harvests
- **Buff Effects**: Increases chest drop rate for fishing

#### Contributor Tracking
- **Top Contributors**: Rankings per season
- **All-Time Stats**: Historical contribution tracking
- **Title System**: Rewards based on contribution level

---

### 💕 7. RELATIONSHIP SYSTEM

**Complexity:** Low-Medium  
**Type:** Social gifting

#### Features
- **Gift Sending** (`/tangqua`): Send items from inventory to others
- **Anonymous Gifting**: Option to hide sender identity
- **Custom Messages**: Attach personal message to gift
- **Rate Limiting**: Max 10 gifts per hour per user

#### Supported Gifts
- Coffee (Cà phê)
- Flowers (Hoa)
- Chocolate (Sô-cô-la)
- Rings (Nhẫn)
- Cards (Thiệp)
- Generic gifts

---

### 🐟 8. AQUARIUM SYSTEM

**Complexity:** Medium  
**Type:** Visual fish showcase

#### Features
- **Thread-Based Display**: Each user gets a thread in aquarium channel
- **Auto-Update**: Dashboard refreshes on fish catch (with 30s debounce)
- **Fish Showcase**: Display collected fish with images
- **Collection Stats**: Show progress toward completion

---

### 🎯 9. NOI TU (Word Chain Game)

**Complexity:** Medium  
**Type:** Vietnamese word game

#### Features
- **Auto-Detection**: Listens in designated channel
- **Word Validation**: Checks Vietnamese dictionary
- **Chain Rules**: Last syllable → first syllable of next word
- **Scoring**: Points for valid words
- **Leaderboard**: Top word chain players

---

### 🎁 10. GIVEAWAY SYSTEM

**Complexity:** Low-Medium  
**Type:** Prize distribution

#### Features
- **Create Giveaway**: Admin command to set up prize
- **Entry System**: React to enter
- **Timer**: Auto-draw after duration
- **Winner Selection**: Random participant
- **Requirements**: Min participants, entry conditions

---

### 🔔 11. BUMP REMINDER

**Complexity:** Low  
**Type:** Server promotion helper

#### Features
- **Auto-Reminder**: Ping role when bump available (2h cooldown)
- **Channel Config**: Set reminder channel
- **Role Ping**: Notify specific role
- **Thank You**: Reward users who bump (potential)

---

### 🏆 12. ACHIEVEMENT SYSTEM (Core Service)

**Complexity:** Medium  
**Type:** Cross-module progression

#### Features
- **Centralized Manager**: Tracks achievements across all modules
- **Unlock Conditions**: Stat-based triggers
- **Notifications**: Announce unlocks in channel
- **Title Rewards**: Display titles based on achievements

#### Achievement Categories
- **Fishing**: Fish caught, collection completion, event triggers
- **Economy**: Balance milestones, transaction volume
- **Social**: Gifts sent, voice time, messages
- **Games**: Werewolf wins, gambling profits

---

### 🎨 13. VIP SYSTEM (Premium Features)

**Complexity:** Low-Medium  
**Type:** Monetization layer

#### VIP Perks
- **Auto-Water**: Passive tree contribution
- **Premium Consumables**: Exclusive items
- **Custom Themes**: Profile personalization (Phase 3)
- **Cashback**: Transaction rewards (Phase 2.2)

---

## 📊 FEATURE METRICS

| Category | Features | Complexity | Engagement | Theme Fit |
|----------|----------|------------|------------|-----------|
| **Core Gameplay** | Fishing, Werewolf | Very High | High | 7/10 (fishing intense, werewolf social) |
| **Economy** | Currency, Shop, Gambling | High | Medium | 5/10 (gambling not healing) |
| **Social** | Gifts, Tree, Relationship | Medium | Medium | 9/10 (perfect for chill) |
| **Utility** | Bump, Giveaway, Achievements | Low | Low | 6/10 (useful but not core) |
| **Creative** | Aquarium, Noi Tu | Medium | Low | 8/10 (creative expression) |

---

## 🎯 ENGAGEMENT LOOPS

### Primary Loop (Fishing)
```
Fish → Collect → Sell → Buy Upgrades → Fish Better → Repeat
```
**Retention:** High (progression-driven)  
**Time Investment:** Medium (active play required)

### Secondary Loop (Economy)
```
Activity → Earn Hạt → Buy Items → Use Items → More Activity
```
**Retention:** Medium (passive income available)  
**Time Investment:** Low (background accumulation)

### Social Loop (Tree + Gifts)
```
Contribute → See Progress → Harvest Buff → More Fishing → More Seeds → Contribute
```
**Retention:** Medium (collaborative, but slow)  
**Time Investment:** Low (occasional contributions)

### Competitive Loop (Werewolf)
```
Join Game → Play → Win/Lose → Learn Roles → Join Again
```
**Retention:** Medium-High (skill-based)  
**Time Investment:** High (60-90 min per game)

---

## ⚠️ CURRENT GAPS & WEAKNESSES

### Missing Features (Common in Chill Bots)
1. **Music System**: No music playback (common in chill servers)
2. **Voice Time Rewards**: Basic implementation, no leaderboards
3. **Karma/Rep System**: No user reputation tracking
4. **Profile Customization**: Minimal personalization
5. **Passive AFK Rewards**: No AFK farming mechanic (like OwO's HuntBot)
6. **PvP Battles**: No player vs player in fishing/economy
7. **Pet/Companion System**: No persistent companions
8. **Daily Quests**: No quest system (just daily bonus)
9. **Event Calendar**: No scheduled events
10. **Streaks**: No daily login streaks

### UX Issues
1. **Fishing Transaction Lock**: Blocks scaling (see AUDIT_REPORT)
2. **Gambling Theme**: Xi Dách/Bầu Cua may not fit "healing" vibe
3. **Complexity Barrier**: Fishing has steep learning curve
4. **Limited Social Hooks**: Few reasons to interact with other users
5. **No Chill Music**: Missing ambient/lo-fi integration

### Balance Issues
1. **Fishing Dominates**: 80% of economy from fishing
2. **Voice Rewards Low**: 2 Hạt/10min vs 1-3/message
3. **Tree Growth Slow**: Requires massive coordination
4. **Werewolf Inactive**: Requires 4-50 players, hard to fill

---

## 🎨 THEME ALIGNMENT: "CHILL/HEALING SERVER"

### What Fits Well ✅
- **Tree System**: Collaborative, nature theme, calming
- **Aquarium**: Visual, peaceful, collection-based
- **Relationship/Gifts**: Wholesome social interaction
- **Voice Rewards**: Encourages hanging out

### What Doesn't Fit ❌
- **Gambling (Xi Dách, Bầu Cua)**: High-stakes, stressful
- **Fishing Events**: Some events are punishing (theft, loss)
- **Werewolf**: Deception-based, can be intense

### Neutral 🤷
- **Fishing Core**: Could be reframed as "meditative fishing"
- **Economy**: Necessary evil, but not inherently chill
- **Noi Tu**: Competitive but language-learning

---

## 📈 CURRENT STATS

**Total Modules:** 13  
**Total Lines:** ~52,000  
**Active Users:** Unknown (no analytics)  
**Retention:** Unknown (no tracking)  
**Daily Active:** Unknown  
**Primary Activity:** Fishing (estimated 70% of commands)

---

**Analysis Completed:** Partial (waiting for research agents)  
**Next Step:** Synthesize research findings + create recommendations

# BHNBot - Tài Liệu Tham Chiếu Cogs (Complete Technical Reference)

**Last Updated**: January 26, 2026  
**Total Cogs**: 32 | **Slash Commands**: 126 | **Prefix Commands**: ~40  
**Command Groups**: /giaidau, /giveaway, /banthan, /masoi, /nha, /trangtri, /loadout, /playlist, /sukien, /danhhieu, /sukien_test, /sukien_admin, /tuoi, /config, /cog

## MỤC ĐÍCH TÀI LIỆU
Tài liệu này được tạo ra để AI assistant có thể:
1. Hiểu rõ TOÀN BỘ tính năng của mỗi module
2. Tránh vô tình xóa hoặc phá vỡ chức năng khi sửa code
3. Biết được các ràng buộc và quy tắc quan trọng
4. Tham khảo nhanh khi cần thông tin về một module cụ thể

---

## 1. FISHING MODULE (Câu Cá) - COMPLEX
**Files**: `cogs/fishing/` (cog.py, constants.py, commands/, mechanics/, utils/)

### Slash Commands
| Lệnh | Tham số | Chức năng | Cooldown |
|------|---------|-----------|----------|
| `/cauca` | Không | Câu cá | Theo cấp cần |
| `/banca` | fish_types, mode | Bán cá | Không |
| `/lichcauca` | Không | Xem lịch sự kiện | Không |
| `/bosuutap` | Không | Bộ sưu tập cá | Không |
| `/huyenthoai` | Không | Bảng vàng huyền thoại | Không |
| `/hiente` | fish_key | Hiến tế cá | Không |
| `/chetao` | item_key | Chế tạo vật phẩm | Không |
| `/dosong` | Không | Máy dò sóng | Theo item |
| `/ghepbando` | Không | Ghép bản đồ | Theo item |
| `/bonphan` | Không | Bón phân cho cây | Không |
| `/moruong` | Không | Mở rương kho báu | Không |
| `/nangcap` | Không | Nâng cấp cần câu | Không |

### Tournament Commands (Command Group `/giaidau`)
| Lệnh | Tham số | Chức năng | VIP Tier |
|------|---------|-----------|----------|
| `/giaidau create` | fee | Tổ chức giải đấu (trả phí tạo) | Tier 1+ |
| `/giaidau join` | tournament_id | Tham gia giải đấu đang mở | Any |
| `/giaidau rank` | Không | Xem bảng xếp hạng giải đấu hiện tại | Any |

**Tournament Flow:**
1. Host tạo giải bằng `/giaidau create [fee]` → Trả phí, tạo prize pool
2. Người chơi tham gia bằng `/giaidau join [id]` → Trả phí, prize pool tăng
3. Auto-start sau 15 phút hoặc khi đủ người (min 2)
4. Trong thời gian thi đấu: Điểm = tổng giá trị cá câu được
5. Kết thúc: Top 1 nhận 50%, Top 2 nhận 30%, Top 3 nhận 20%

### Core Features
- Fishing mechanics với catch rates theo Loot Table
- Rod system: 7 cấp, có durability
- Bucket system: giới hạn 100 con
- Sell system: ACID transactions

### Special Mechanics
- Random events: Double Rainbow, Golden Turtle, Sea Sickness...
- Global disasters: Hacker attack, Earthquake, Tsunami...
- Legendary quests: Thượng Luồng, Cá Ngân Hà, Phượng Hoàng, Cthulhu, 52Hz, Isekai
- Buff/Debuff system: suy, keo_ly, lag, lucky_buff
- **NPC Affinity System**: Repeated interactions unlock better rewards (Lv.1, Lv.2)
- **NEW**: All NPC declines result in -1 Affinity (now visible in UI)

### Inventory Display
- **FIXED**: Legendary fish (ca_isekai) now show in Fish category, not Tools
- Categories:  Fish,  Gifts,  Tools,  Trash
- Fish sorted by rarity with price calculations

### State Variables (FishingCog)
- `fishing_cooldown`: dict[user_id -> timestamp]
- `caught_items`: cache cá vừa câu
- `user_locks`: Lock xử lý race condition
- `phoenix_buff_active`, `thuong_luong_timers`, `dark_map_active`...

### Database Tables
- `inventory`, `fishing_profiles`, `fish_collection`, `legendary_quests`

### VIP Features
- VIP fish pool: 15 loài (Tier 1: 3, Tier 2: 8, Tier 3: 15)
- Tier 3: Auto recycle trash → Leaf Coin
- Premium consumables: Chấm Long Dịch, Lưới Thần Thánh

### Critical Notes
- Sử dụng `async with db_manager.transaction()` cho mọi thay đổi tài sản
- Cleanup task chạy mỗi giờ dọn memory
- Glitch mechanic làm nhiễu tên cá (Hacker Attack)

---

## 2. ECONOMY MODULE (Kinh Tế)
**File**: `cogs/economy.py`

### Slash Commands
| Lệnh | Chức năng |
|------|-----------|
| `/chao` | Chào buổi sáng nhận 10 hạt (5h-10h) + streak bonus |
| `/tuido [user]` | Xem số dư, cần câu, túi đồ |
| `/top` | Bảng xếp hạng đại gia |
| `/themhat [user] [amount]` | (Admin) Cộng hạt |

### Features
- Chat Reward: 1-3 hạt mỗi 60s
- Reaction Reward: nhận hạt khi được thả cảm xúc
- Voice Reward: 2 hạt / 10 phút voice
- Weekly Welfare: 500 hạt cho người nghèo mỗi Chủ Nhật

### Daily Streak System
- **Window**: 5 AM - 10 AM (DAILY_WINDOW_START/END)
- **Streak Bonus**: +hạt mỗi ngày liên tiếp (capped at MAX_STREAK_BONUS)
- **Streak Protection**: Boolean flag bảo vệ streak khi miss 1 ngày
- **Database columns**: `daily_streak`, `streak_protection` trong `users` table

### Database
- `users`: user_id, seeds, last_daily, last_chat_reward, daily_streak, streak_protection...
- `server_config`: harvest_buff_until, exclude_chat_channels
- `transaction_logs`: lịch sử giao dịch

---

## 3. SHOP MODULE (Cửa Hàng)
**File**: `cogs/shop.py`

### Slash Commands
| Lệnh | Chức năng |
|------|-----------|
| `/mua [item] [soluong]` | Mua vật phẩm |
| `/themitem [user] [item] [count]` | (Admin) Cấp item |

### Item Categories
- `gift`: Quà tặng
- `fishing`: Mồi câu, phụ kiện
- `buff`: Nước tăng lực, găng tay...
- `special`: Máy dò sóng, Bản đồ...
- `vip`: Vật phẩm VIP-only

---

## 4. CONSUMABLE MODULE (Sử Dụng Vật Phẩm)
**File**: `cogs/consumable.py`

### Slash Commands
| Lệnh | Chức năng |
|------|-----------|
| `/sudung [item_key]` | Sử dụng vật phẩm |

### Item Effects
- `tinh_cau`: Mini-game nối sao → Cá Ngân Hà
- `long_vu_lua`: Mini-game ấp trứng → Cá Phượng Hoàng
- `ban_do_ham_am`: Mở bản đồ 10 lần câu → Cthulhu
- `nuoc_tang_luc/gang_tay_xin`: Buff tỉ lệ/cooldown

### VIP Consumables
- `multi_catch`: Câu 3-5 con
- `guarantee_rare_multi`: Lưới Thần Thánh (5-10 cá hiếm)

---

## 5. UNIFIED SHOP (Cửa Hàng Tập Trung)
**Files**: `cogs/unified_shop/` (cog.py, logic.py, views.py)

### Features
- Giao diện Select Menu + Buttons
- Persistent View (sống qua restart)
- Modal nhập số lượng
- Hỗ trợ thanh toán: Hạt hoặc Xu Lá
- Tích hợp nâng cấp cần câu

---

## 6. AQUARIUM MODULE (Hồ Cá)
**Files**: `cogs/aquarium/` (cog.py, models.py, ui/, logic/)

### Slash Commands
| Lệnh | Chức năng |
|------|-----------|
| `/nha khoitao` | Tạo nhà (Thread trong Forum) |
| `/trangtri cuahang` | Mở shop nội thất |
| `/trangtri sapxep` | Đặt/gỡ nội thất (5 vị trí) |
| `/trangtri theme` | (VIP 2+) Đổi hình nền |
| `/thamnha` | Ghé thăm nhà người khác |
| `/taiche` | Tái chế rác → Xu Lá + Phân Bón |
| `/themxu` | (Admin) Cộng Xu Lá |

### Feng Shui Sets
- Rạn San Hô: +% Hạt từ Cây
- Kho Báu Cổ Đại: +giá bán cá
- Công Nghệ Tương Lai: Passive income

### Feng Shui Set System (18 Sets, 72 Items)
**Data File**: `data/aquarium/sets.json`

**Effect Types (11 Total):**
| Effect Key | Description | Consumer |
|------------|-------------|----------|
| `catch_rate_bonus` | +% tỉ lệ câu được cá | `cogs/fishing/commands/fish.py` |
| `rare_chance_bonus` | +% tỉ lệ cá hiếm | `cogs/fishing/commands/fish.py` |
| `legendary_chance_bonus` | +% tỉ lệ cá huyền thoại | `cogs/fishing/commands/fish.py` |
| `sell_price_bonus` | +% giá bán cá | `cogs/fishing/commands/sell.py` |
| `seed_bonus` | +% hạt từ cây | `cogs/tree/cog.py` |
| `passive_income` | Thu nhập tự động/giờ | `cogs/aquarium/logic/passive_income.py` |
| `minigame_bonus` | +% điểm minigame seasonal | `cogs/seasonal/services/participation.py` |
| `quest_reward_bonus` | +% thưởng nhiệm vụ | `cogs/quest/services/quest_service.py` |
| `baucua_luck_bonus` | +% may mắn bầu cua | `cogs/baucua/game_logic.py` |
| `gift_value_bonus` | +% giá trị quà tặng | `cogs/relationship/services/gift_service.py` |
| `buddy_xp_bonus` | +% XP bạn thân | `cogs/relationship/services/buddy_service.py` |

**Set Tiers:**
| Tier | Sets | Required Pieces | Effect Multiplier |
|------|------|-----------------|-------------------|
| 1 | 6 sets | 2 pieces | 1.0x |
| 2 | 6 sets | 2 pieces | 1.5x-2.0x |
| 3 | 6 sets | 2 pieces | 2.0x-3.0x |

### VIP Features
- Tier 2: Đổi theme hình nền
- Tier 3: Auto-Visit (tự động thăm 5 nhà/ngày)

### Database (Tortoise ORM)
- `user_aquarium`: leaf_coin, home_thread_id, theme_url...
- `home_slots`: vị trí nội thất
- `home_visits`: log thăm nhà

---

## 7. NÓI TỨ MODULE (Nối Từ)
**Files**: `cogs/noi_tu/` (cog.py, add_word.py)

### Slash Commands
| Lệnh | Chức năng |
|------|-----------|
| `/resetnoitu` | Reset game (anti-troll 5 phút) |
| `/themtu [từ]` | Đề xuất từ mới |
| `/ntrank` | Top 10 nối từ (trong general.py) |

### Game Rules
- Từ tiếp = bắt đầu bằng âm cuối của từ trước
- Phải có 2 âm tiết
- Không trùng từ đã dùng trong phiên
- Không tự nối tiếp

### Rewards
- Streak bonus: max(20, streak * 5) hạt
- +3 hạt mỗi từ đúng
- Milestone: +20 hạt mỗi 10 từ
- x2 nếu có Harvest Buff

### Stats Tracked
- correct_words, game_starters, low_time_answers, fast_answers
- night_answers, reduplicative_words, long_chain_participation

---

## 8. WEREWOLF MODULE (Ma Sói) - COMPLEX
**Files**: `cogs/werewolf/` (cog.py, engine/, roles/)

### Slash Commands
| Lệnh | Chức năng |
|------|-----------|
| `/masoi create` | Tạo bàn chơi |
| `/masoi guide` | Hướng dẫn vai trò |

### Game Flow
1. Lobby creation → Players join
2. Bot tạo Category + Threads (Bàn Tròn, Hang Sói, Nghĩa Địa)
3. Role assignment qua DM
4. Night cycle: mute voice, Sói chọn mục tiêu, các role dùng skill
5. Day cycle: thảo luận → biện hộ → biểu quyết → lời cuối
6. Win condition check

### Roles (39 vai trò)
**Phe Dân**: Tiên Tri, Phù Thủy, Thợ Săn, Bảo Vệ, Trưởng Làng, Già Làng, Hiệp Sĩ, Cáo...
**Phe Sói**: Ma Sói, Sói To Xấu Xa, Sói Quỷ, Sói Lửa, Sói Anh/Em...
**Trung Lập**: Thổi Sáo, Kẻ Phóng Hỏa, Sói Trắng, Thằng Ngốc...

### State Persistence
- Lưu game state dạng JSON vào `game_sessions`
- Voice state listener để auto mute/unmute

---

## 9. BẦU CUA MODULE
**Files**: `cogs/baucua/` (cog.py, game_logic.py, views.py...)

### Commands
| Lệnh | Chức năng |
|------|-----------|
| `/baucua` | Bắt đầu game |
| `!bc -q <tiền> <linh_vật>` | Đặt cược nhanh |

### Game Rules
- 6 linh vật: Bầu, Cua, Tôm, Cá, Gà, Nai
- Đặt cược 45s, lắc xúc xắc 6s
- Tiền cược max: 250,000 Hạt
- Payout: 2x/3x/4x theo số mặt trúng

### VIP Cashback
- Tier 1: 2%, Tier 2: 3%, Tier 3: 5% hoàn tiền khi thua
- Daily cashback: 2-5% net loss, max 10k hạt

---

## 10. XÌ DÁCH MODULE (Blackjack)
**Files**: `cogs/xi_dach/` (cog.py, services/, ui/)

### Commands
| Lệnh | Chức năng |
|------|-----------|
| `/xidach [bet]` | Tạo/vào phòng chơi |

### Special Rules (Việt Nam)
- Xì Bàn (2 A) > Xì Dách (A+10) > Ngũ Linh (5 lá ≤21) > Đủ tuổi (16-21)
- Payout: Thường 2x, Xì Dách 2.5x, Xì Bàn 3x, Ngũ Linh 3.5x

### Error Handling
- **IMPROVED**: Better exception handling in dealer turn
- Fallback result display if formatting fails
- Enhanced logging for debugging result display issues

### UI
- Card rendering bằng Pillow
- Assets tại `assets/cards/`

---

## 11. TREE MODULE (Cây Thần)
**Files**: `cogs/tree/` (cog.py, tree_manager.py, constants.py...)

### Commands
| Lệnh | Chức năng |
|------|-----------|
| `/cay` | Xem trạng thái cây |
| `/gophat [amount]` | Góp hạt cho cây |
| `/huyhieu` | Xem huy hiệu đóng góp |
| `/thuhoach` | (Admin) Thu hoạch |

### Watering Commands (Command Group `/tuoi`)
| Lệnh | Chức năng |
|------|-----------|
| `/tuoi` | Tưới cây miễn phí (1 lần/ngày, nhận XP + random reward) |

### Mechanics
- 6 giai đoạn: Hạt mầm → Nảy mầm → Cây non → Trưởng thành → Ra hoa → Kết trái
- Yêu cầu tăng 25% mỗi mùa

### Harvest Rewards
- Top 1: 13k hạt + Role "Thần Nông"
- Top 2: 5k, Top 3: 3k, Others: 1.5k
- Server buff: x2 hạt 24h

### Prestige Badges
**NEW**: Hệ thống huy hiệu dựa trên contribution XP

| Tier | Badge | Tên | XP yêu cầu |
|------|-------|-----|------------|
| 1 |  | Người Trồng Cây | 1,000 |
| 2 |  | Người Làm Vườn | 5,000 |
| 3 |  | Người Bảo Vệ Rừng | 25,000 |
| 4 |  | Thần Nông | 100,000 |
| 5 |  | Tiên Nhân | 500,000 |

**Commands:**
- `/huyhieu` - Xem badge hiện tại, progress, và tất cả tiers
- `/cay` - Leaderboard hiển thị badge trước tên user

---

## 12. GIVEAWAY MODULE
**Files**: `cogs/giveaway/` (cog.py, views.py, models.py...)

### Commands
| Lệnh | Chức năng |
|------|-----------|
| `/giveaway create` | Tạo giveaway |
| `/giveaway end` | Kết thúc sớm |
| `!giveaway reroll` | Chọn lại người thắng |

### Features
- Điều kiện: số invite, chi phí hạt
- Multi-winner support
- Persistent qua restart

---

## 13. RELATIONSHIP MODULE
**Files**: `cogs/relationship/` (cog.py, services/buddy_service.py, constants.py)

### Slash Commands
| Lệnh | Tham số | Chức năng |
|------|---------|-----------|
| `/tangqua` | user, item, message, an_danh | Tặng quà healing |
| `/qua-thongke` | loai | Xem thống kê quà tặng |

### Buddy System (Bạn Thân) - Command Group `/banthan`
| Lệnh | Chức năng |
|------|-----------|
| `/banthan moi <user>` | Gửi lời mời kết bạn thân |
| `/banthan chapnhan <user>` | Chấp nhận lời mời |
| `/banthan tuchoi <user>` | Từ chối lời mời |
| `/banthan danhsach` | Xem danh sách bạn thân (max 3) |
| `/banthan cho` | Xem lời mời đang chờ |
| `/banthan huy <user>` | Huỷ liên kết bạn thân |

### Buddy Bond Levels
| Level | Tên | XP yêu cầu | Bonus |
|-------|-----|------------|-------|
| 1 | Người quen | 0 | +10% |
| 2 | Tri kỷ | 1,000 | +15% |
| 3 | Thân thiết | 5,000 | +18% |
| 4 | Đồng hành | 15,000 | +22% |
| 5 | Chiến hữu | 50,000 | +25% |

### Features
- Maximum 3 buddies per user
- 10-25% XP bonus khi buddy online cùng câu cá
- Shared XP tracking giữa 2 người
- Auto level-up mỗi 1000 shared XP
- Gửi quà ẩn danh với lời nhắn ngẫu nhiên

### Database Tables
```sql
buddy_bonds (user1_id, user2_id, guild_id, bond_level, shared_xp, created_at)
buddy_requests (from_user_id, to_user_id, guild_id, created_at)
gift_history (sender_id, receiver_id, guild_id, item_key, is_anonymous, message, created_at)
```

### CRITICAL CONSTRAINT
**NO ROMANCE**: Chỉ hệ thống bạn bè, KHÔNG có marriage/dating/romantic features.

---

## 14. GENERAL MODULE
**File**: `cogs/general.py`

### Commands
| Lệnh | Chức năng |
|------|-----------|
| `/avatar` | Xem avatar |
| `/help` | Danh sách lệnh |
| `/hoso` | Profile card (Pillow) |
| `/ntrank` | Top nối từ |
| `!ping` | Latency check |

---

## 15. CONFIG MODULE
**File**: `cogs/config.py`

### Commands
| Lệnh | Chức năng |
|------|-----------|
| `/config set` | Cài đặt kênh chức năng |
| `/reset` | Reset game trong kênh |
| `/exclude` | Loại kênh khỏi nhận hạt |
| `/exclude_list` | Xem danh sách exclude |

### Config Set Options
| Option | Description |
|--------|-------------|
| `kenh_noitu` | Kênh chơi nối từ |
| `kenh_logs` | Kênh ghi log admin |
| `kenh_cay` | Kênh trồng cây server |
| `kenh_fishing` | Kênh thông báo sự kiện câu cá |
| `kenh_bump` | Kênh nhắc bump Disboard |
| `kenh_log_bot` | Kênh gửi log lỗi bot lên Discord |
| `kenh_aquarium` | Kênh Forum Làng Chài (Hồ Cá) |
| `kenh_nhiemvu` | Kênh thông báo nhiệm vụ hàng ngày |
| `log_ping_user` | Người nhận ping khi có lỗi ERROR/CRITICAL |
| `log_level` | Mức độ log gửi lên Discord (INFO/WARNING/ERROR/CRITICAL) |

---

## 16. BUMP REMINDER MODULE
**Files**: `cogs/bump_reminder/` (cog.py, detector.py, task.py...)

### Features
- Phát hiện Disboard bump
- Nhắc nhở sau 3 giờ
- Cooldown 1 giờ giữa các nhắc nhở

---

## 17. ADMIN MODULES
**Files**: `cogs/admin/` (health.py, backup.py, maintenance.py, management.py, monitor.py)

### Health Check (`/healthcheck`)
- Memory, CPU, Uptime, Active Views, Background Tasks, Latency

### Backup
- Auto backup mỗi 4 giờ
- Giữ 6 bản gần nhất
- `pg_dump` cho PostgreSQL

### Management
- `/sync`: Đồng bộ slash commands
- `!cog load/reload/unload`: Quản lý modules
- `!reload_items`: Cập nhật item data

### Monitor
- Hot reload config mỗi 10s

---

## 18. VIP SYSTEM \u0026 ACHIEVEMENTS

### Achievements System

**File**: `core/achievement_system.py`

**Features:**
- Unlock notifications with embedded rewards
- **NEW**: Rarity display - shows % of server who has the achievement
- Categorized by game (fishing, economy, social, etc.)
- Role rewards for special achievements
- Seed rewards for milestones

**Database:**
- `user_achievements`: Records unlock timestamps
- `achievements_data`: Achievement definitions

**Rarity Calculation:**
```python
# Example: "2.5% người chơi đã đạt được"
earned_count / total_guild_members * 100
```

---

## 19. VIP SYSTEM
**Files**: `cogs/vip_commands.py`, `core/services/vip_service.py`

### Tiers
| Tier | Tên | Chi phí/30 ngày |
|------|-----|-----------------|
| 0 | Member | Miễn phí |
| 1 | Bạc  | 50,000 Hạt |
| 2 | Vàng  | 150,000 Hạt |
| 3 | Kim Cương  | 500,000 Hạt |

### Commands
| Lệnh | Chức năng |
|------|-----------|
| `/thuongluu b` | Mua VIP |
| `/thuongluu t` | Bảng xếp hạng |
| `/thuongluu s` | Trạng thái |

### Benefits Summary
- **Fishing**: VIP fish, auto-sell, auto-recycle
- **Aquarium**: Extra slots, themes, auto-visit
- **Tree**: +10% XP, Magic Fruit chance, auto-water
- **Minigames**: Cashback 2-5%

### CRITICAL CONSTRAINT
**NO PAY-TO-WIN**: VIP chỉ mang tính thẩm mỹ và tiện lợi, KHÔNG tăng tỉ lệ thắng.

---

## DATABASE TABLES SUMMARY

### SQLite (Legacy)
- `users`: user_id, seeds, last_daily...
- `inventory`: user_id, item_key, quantity
- `fishing_profiles`: rod_level, durability
- `server_config`: guild settings
- `game_sessions`: werewolf/noitu state

### PostgreSQL (New)
- `user_aquarium`: leaf_coin, theme_url...
- `home_slots`: decoration placement
- `vip_subscriptions`: tier, expiry, stats

---

## CRITICAL DEVELOPMENT RULES

### COOLDOWNS REFERENCE TABLE
| Command | Cooldown | Type | File |
|---------|----------|------|------|
| `/baucua` | 10 seconds | Per user per guild | `cogs/baucua/cog.py` |
| `/xidach` | 15 seconds | Per user | `cogs/xi_dach/cog.py` |
| `/chao` | 1 hour (3600s) | Per user per guild | `cogs/economy/cog.py` |
| `/tuido` | 5 seconds | Per user per guild | `cogs/economy/cog.py` |
| `!cauca` | 5 seconds | Per user | `cogs/fishing/cog.py` |

### MUST DO
1. Sử dụng `async with db_manager.transaction()` cho mọi thay đổi tài sản
2. **CRITICAL**: Balance check và deduction phải trong CÙNG 1 transaction (tránh race condition)
3. Không blocking I/O trong async functions
4. Chạy `lsp_diagnostics` sau mỗi thay đổi (nếu có)
5. Test import trước khi commit
6. **NEW**: Transaction scope phải TỐI THIỂU - KHÔNG bao gồm `asyncio.sleep` hoặc `channel.send`

### MUST NOT DO
1. KHÔNG xóa hoặc rename functions mà không kiểm tra references
2. KHÔNG thay đổi database schema mà không update migrations
3. KHÔNG hardcode Discord IDs
4. KHÔNG sử dụng `type: ignore` trừ khi thực sự cần thiết
5. KHÔNG pay-to-win cho VIP features
6. **NEW**: KHÔNG dùng f-string cho dynamic column names trong SQL (risk SQL injection)
7. **NEW**: KHÔNG để `on_timeout` methods không thông báo user (phải edit message)

---

## KNOWN ISSUES \u0026 TECHNICAL DEBT

### Performance Bottlenecks
- **Fishing Transaction Lock** (`cogs/fishing/cog.py` lines 632-834): Transaction giữ lock 1-5 giây → cần refactor
- **N+1 Query Pattern** (fishing catches): Sequential DB updates cho mỗi con cá → cần batch
- **Aquarium Dashboard Spam** (`cogs/aquarium/`): Refresh mỗi message → cần debounce 30s

### Security Issues
-  **Xi Dach Race Condition** (`cogs/xi_dach/commands/multi.py`): Double-spend possible → wrap trong transaction
-  **SQL Injection Risk** (`database_manager.py`): Dynamic column names → thêm whitelist
- **Non-atomic Stats** (`increment_stat`): SELECT then UPDATE → dùng ON CONFLICT

### Scalability Limits
- **Fishing**: 500-1000 concurrent users (bottleneck: in-memory cooldowns)
- **Werewolf**: 10-20 games/guild (bottleneck: Discord channel creation API)
- **Aquarium**: 5-10 active threads (bottleneck: message edit rate limit)
- **Economy**: 10,000+ users (good scalability)

### Migration Status
-  **Seasonal SQL Fixed**: All `?` placeholders converted to `$1, $2` for asyncpg (Jan 2026)
-  **DB Layer Inconsistency**: Some legacy modules may still use SQLite `?` placeholders
- Migration strategy: Currently using `ensure_*_tables()` → should move to versioned migrations
- Cross-DB transactions (VIP): Seeds (SQLite?) + VIP (Postgres) → needs unification

**Detailed Analysis:** See `/docs/AUDIT_REPORT_2026.md`

---

## 20. MUSIC MODULE (Nhạc)
**Files**: `cogs/music/` (cog.py, ui/views.py, services/)

### Requirements
- **Lavalink Server**: Cần chạy Lavalink server tại `localhost:2333`
- **Wavelink Library**: Python wrapper cho Lavalink

### Slash Commands
| Lệnh | Tham số | Chức năng |
|------|---------|-----------|
| `/play` | query | Phát nhạc từ YouTube/Spotify/SoundCloud |
| `/skip` | Không | Bỏ qua bài hiện tại |
| `/stop` | Không | Dừng phát và rời kênh |
| `/pause` | Không | Tạm dừng/tiếp tục |
| `/queue` | Không | Xem hàng đợi |
| `/nowplaying` | Không | Xem bài đang phát |
| `/volume` | level (0-100) | Điều chỉnh âm lượng |
| `/shuffle` | Không | Xáo trộn hàng đợi |
| `/loop` | mode (off/track/queue) | Chế độ lặp |
| `/247` | Không | Bật/tắt chế độ 24/7 |
| `/filter` | effect | Áp dụng hiệu ứng âm thanh |

### Playlist Commands (Subgroup `/playlist`)
| Lệnh | Chức năng |
|------|-----------|
| `/playlist create [name]` | Tạo playlist mới |
| `/playlist add [name]` | Thêm bài đang phát vào playlist |
| `/playlist list` | Xem danh sách playlist |
| `/playlist view [name]` | Xem chi tiết playlist |
| `/playlist play [name]` | Phát playlist |
| `/playlist remove [name] [position]` | Xóa bài khỏi playlist |
| `/playlist delete [name]` | Xóa playlist |

### Audio Filters
| Filter | Effect |
|--------|--------|
| `lofi` | Pitch 0.9 (chill vibe) |
| `vaporwave` | Speed 0.8, Pitch 0.85 |
| `nightcore` | Speed 1.2, Pitch 1.2 |
| `bass` | Bass boost equalizer |
| `reset` | Reset về mặc định |

### Music Sources
- **YouTube**: Direct URL hoặc playlist
- **Spotify**: Track, Playlist, Album (convert sang SoundCloud/YouTube search)
- **SoundCloud**: Default search source
- **Fallback**: YouTube search nếu SoundCloud không tìm thấy

### State Variables
- `music_247_guilds`: Set[guild_id] - guilds bật 24/7
- `lavalink_connected`: Boolean - trạng thái kết nối
- `_now_playing_messages`: dict[guild_id → Message] - embed đang phát
- `_music_channels`: dict[guild_id → TextChannel] - kênh text

### Database Tables
- `music_playlists`: user_id, guild_id, name, track_count, total_duration_ms
- `music_playlist_tracks`: playlist_id, title, uri, artist, duration_ms, position

### Critical Notes
- Bot auto-disconnect sau 5 phút nếu queue trống (trừ chế độ 24/7)
- Persistent View cho MusicControlView (sống qua restart)
- Spotify không stream trực tiếp, chỉ lấy metadata rồi search trên SoundCloud/YouTube

---

## 21. AUTO-FISHING MODULE (Câu Cá Tự Động)
**Files**: `cogs/auto_fishing/` (cog.py, core/calculator.py, services/fishing_service.py, ui/views.py)

### Slash Commands
| Lệnh | Chức năng |
|------|-----------|
| `/autocauca` | Mở dashboard auto-fishing (ephemeral) |

### UI Buttons (MainMenuView)
| Button | Chức năng |
|--------|-----------|
|  Refresh | Làm mới + thu hoạch cá mới |
|  Bật/Tắt | Toggle auto-fishing on/off |
|  Xem kho | Xem kho cá tự động |
|  Nâng cấp | Menu nâng cấp |
|  Chuyển → Xô | Chuyển cá vào inventory chính |
|  Tinh luyện | Chuyển cá thành essence |
|  Bán cá | Bán cá lấy coins |

### Upgrade System
| Upgrade | Levels | Effect |
|---------|--------|--------|
|  Efficiency | 1-5 | 5/10/20/40/100 cá/giờ |
|  Duration | 1-5 | 4/8/12/18/24 giờ max tích lũy |
|  Quality | 1-5 | +5/10/20/35/50% cá hiếm |

### Essence System
| Rarity | Essence/con |
|--------|-------------|
| Common | 1 |
| Rare | 5 |
| Epic | 25 |
| Legendary | 100 |

### Background Task
- `harvest_loop`: Chạy mỗi 30 phút, auto-harvest cho tất cả user có `is_active=TRUE`

### Database Tables
```sql
auto_fishing (
    user_id BIGINT PRIMARY KEY,
    is_active BOOLEAN DEFAULT FALSE,
    efficiency_level INT DEFAULT 1,
    duration_level INT DEFAULT 1,
    quality_level INT DEFAULT 1,
    total_essence INT DEFAULT 0,
    last_harvest TIMESTAMP
)

auto_fish_storage (
    user_id BIGINT,
    fish_key VARCHAR(64),
    quantity INT DEFAULT 0,
    PRIMARY KEY (user_id, fish_key)
)
```

### Critical Notes
- **State Persistence**: `is_active` và `last_harvest` lưu trong DB → survive restart
- **Separate Storage**: Cá auto-fish lưu riêng trong `auto_fish_storage`, KHÔNG phải `inventory`
- **Ephemeral UI**: Dashboard chỉ user thấy, dùng nút  để refresh
- **Minimum Harvest Time**: 0.005 giờ (~18 giây) để tránh spam

---

## 22. SOCIAL MODULE (Tử Tế, Streak & Voice Rewards)
**Files**: `cogs/social/` (cog.py, services/voice_service.py, services/kindness_service.py, services/streak_service.py, services/voice_reward_service.py)

### Slash Commands
| Lệnh | Chức năng |
|------|-----------|
| `/tute [@user]` | Xem điểm tử tế của bạn hoặc người khác |
| `/tutetop` | Bảng xếp hạng người tử tế nhất server |

### Voice Hours Tracking
- `on_voice_state_update`: Track join/leave
- Background task mỗi 5 phút flush active sessions (crash protection)
- Stats: `total_seconds`, `sessions_count`

### Kindness Points System
| Hành động | Điểm |
|-----------|------|
| Reaction cho người khác | +1 |
| Nhận reaction | +0.5 |
| Nói cảm ơn | +2 |
| Được cảm ơn | +1 |
| Tặng quà | +5 |
| Nhận quà | +2 |

### Thanks Detection Patterns
- Vietnamese: `cảm ơn`, `cám ơn`, `camon`
- English: `thanks`, `thank you`, `ty`, `tysm`

### Kindness Streak System (NEW)
Streak multipliers cho điểm tử tế:

| Streak Days | Multiplier |
|-------------|------------|
| 7 ngày | x1.10 |
| 14 ngày | x1.15 |
| 30 ngày | x1.25 |
| 60 ngày | x1.35 |
| 90 ngày | x1.50 |

**Features:**
- Streak protection: Boolean flag bảo vệ streak khi miss 1 ngày
- Auto-record khi thả reaction hoặc cảm ơn
- Hiển thị streak trong `/tute` command

### Voice Rewards System (NEW)
Nhận Hạt khi ở trong voice channel:

| Config | Value |
|--------|-------|
| Hạt mỗi 10 phút | 10 |
| Daily cap | 300 Hạt |
| Buddy online bonus | +20% |

**Voice Streak Milestones:**
| Streak | Bonus per interval |
|--------|-------------------|
| 7 ngày | +2 Hạt |
| 14 ngày | +3 Hạt |
| 30 ngày | +5 Hạt |

### Database Tables
```sql
voice_stats (user_id, guild_id, total_seconds, sessions_count, last_session_start)
kindness_stats (user_id, guild_id, reactions_given, reactions_received, thanks_given, thanks_received)
kindness_streaks (user_id, guild_id, current_streak, longest_streak, last_kind_action, streak_protected)
voice_rewards (user_id, guild_id, rewarded_seconds, total_rewards_today, last_reward_date, voice_streak, last_voice_date)
```

---

## 23. PROFILE MODULE (Hồ Sơ Cá Nhân)
**Files**: `cogs/profile/` (cog.py, core/themes.py, core/stats.py, services/profile_service.py, ui/)

### Slash Commands
| Lệnh | Chức năng |
|------|-----------|
| `/hoso [@user]` | Xem profile card (image) |
| `/theme` | Chọn theme hồ sơ (Select Menu) |
| `/bio [text]` | Đặt bio cá nhân (max 200 ký tự) |
| `/thanhtuu [@user]` | Xem thành tựu đã đạt được |

### Themes Available
| Theme | Emoji | Font | VIP Tier |
|-------|-------|------|----------|
| Forest Sanctuary |  | Quicksand | Free |
| Ocean Depths |  | Comfortaa | Free |
| Starry Night |  | Nunito | Free |
| Cozy Cabin |  | Caveat | VIP 1 |
| Sunrise Meadow |  | Outfit | VIP 2 |

### Profile Card Stats
| Icon | Stat | Source |
|------|------|--------|
|  | Seeds | `users.seeds` |
|  | Fish | `COUNT(fish_collection)` |
|  | Voice Hours | `voice_stats.total_seconds / 3600` |
|  | Kindness | Computed score từ kindness_stats |
|  | Streak | `users.daily_streak` |
|  | Badges | Top 4 achievements emojis |

### Database Table
```sql
user_profiles (user_id, theme, badges_display, bio)
```

### Assets
- `assets/profile/bg_*.png`: 5 theme backgrounds (900x350px)
- `assets/profile/fonts/*.ttf`: 5 Google Fonts

---

## 24. QUEST MODULE (Nhiệm Vụ Hàng Ngày)
**Files**: `cogs/quest/` (cog.py, core/quest_types.py, services/quest_service.py)

### Slash Commands
| Lệnh | Chức năng | Quyền |
|------|-----------|-------|
| `/nhiemvu` | Xem nhiệm vụ hàng ngày của server | User |
| `/nv-test-sang` | Test trigger morning announcement | Admin |
| `/nv-test-toi` | Test trigger evening summary | Admin |

### Quest Types
| Type | Name | Icon | Target | Reward Pool |
|------|------|------|--------|-------------|
| `fish_total` | Câu cá |  | 50 cá | 100 Hạt |
| `voice_total` | Voice chat |  | 120 phút | 100 Hạt |
| `gift_total` | Tặng quà |  | 5 quà | 75 Hạt |
| `react_total` | Thả tim |  | 30 reactions | 50 Hạt |
| `tree_water` | Tưới cây |  | 10 lần | 50 Hạt |
| `thank_total` | Cảm ơn |  | 10 lần | 50 Hạt |

### Daily Flow
1. **7:00 AM** - Bot chọn random 3 quest và announce trong `kenh_nhiemvu`
2. **Trong ngày** - Thành viên hoạt động, progress được track tự động
3. **10:00 PM** - Bot tổng kết, phát thưởng theo tỉ lệ đóng góp

### Server Streak System
| Streak Days | Bonus Multiplier |
|-------------|------------------|
| 3 ngày | +10% |
| 7 ngày | +25% |
| 14 ngày | +50% |
| 30 ngày | +100% |

### Reward Distribution
- Phần thưởng chia theo tỉ lệ % đóng góp của mỗi người
- Bonus +50 Hạt nếu hoàn thành cả 3 quest
- Streak bonus áp dụng cho toàn server

### Integration Points
Các module khác gọi `QuestService.add_contribution()`:
- `cogs/social/cog.py` - on_reaction_add, on_message (thanks)
- `cogs/fishing/commands/fish.py` - after catching fish
- `cogs/tree/views.py` - when watering tree
- `cogs/relationship/cog.py` - when sending gift

### Database Tables
```sql
server_daily_quests (guild_id, quest_date, quests JSONB, completed_count, server_streak)
quest_contributions (guild_id, quest_date, user_id, quest_type, contribution_amount)
```

### Critical Notes
- Quest reset lúc 00:00 UTC+7 (Vietnam timezone)
- Cần config `kenh_nhiemvu` channel trước khi dùng
- Morning task chạy lúc 7:00 AM, evening lúc 10:00 PM

---

## 25. SEASONAL MODULE (Sự Kiện Theo Mùa) - COMPLEX
**Files**: `cogs/seasonal/` (cog.py, event_commands.py, event_fish_hook.py, minigames/, services/, ui/)
**Total Commands**: 32 slash commands, 4 command groups

### Command Groups

#### `/sukien` - User Event Commands
| Lệnh | Chức năng |
|------|-----------|
| `/sukien info` | Xem thông tin event đang diễn ra |
| `/sukien thamgia` | Tham gia event hiện tại |
| `/sukien tiendo` | Xem tiến độ cá nhân |
| `/sukien cuahang` | Mở shop event |
| `/sukien bangxephang` | Bảng xếp hạng event |
| `/sukien nhiemvu` | Xem nhiệm vụ event |
| `/sukien diemdanh` | Điểm danh nhận thưởng hàng ngày |

#### `/danhhieu` - Title Commands  
| Lệnh | Chức năng |
|------|-----------|
| `/danhhieu xem` | Xem danh hiệu đã mở khoá |
| `/danhhieu trangbi` | Trang bị danh hiệu |
| `/danhhieu bo` | Bỏ danh hiệu đang đeo |

#### `/sukien_test` - Test Commands (Admin)
| Lệnh | Chức năng |
|------|-----------|
| `/sukien_test start <event>` | Bắt đầu event test |
| `/sukien_test stop` | Dừng event hiện tại |
| `/sukien_test minigame <type>` | Spawn minigame thủ công |
| `/sukien_test goal <type> <target>` | Tạo community goal test |
| `/sukien_test currency <amount>` | Thêm event currency |

#### `/sukien_admin` - Admin Management
| Lệnh | Chức năng |
|------|-----------|
| `/sukien_admin create` | Tạo event mới |
| `/sukien_admin end` | Kết thúc event sớm |
| `/sukien_admin announce` | Gửi thông báo event |
| `/sukien_admin reset_user <user>` | Reset dữ liệu user |

### Event Types (4 Mùa)
| Event | Thời gian | Theme |
|-------|-----------|-------|
| `lunar_new_year` | Tháng 1-2 |  Tết Nguyên Đán |
| `mid_autumn` | Tháng 8-9 |  Trung Thu |
| `halloween` | Tháng 10 |  Halloween |
| `christmas` | Tháng 12 |  Giáng Sinh |

### Minigame System (16 loại)
| Minigame | Event | Mô tả |
|----------|-------|-------|
| `balloon_pop` | Lunar New Year | Bắn bóng bay lấy lì xì |
| `tea_brewing` | Lunar New Year | Pha trà tết |
| `wishes` | Lunar New Year | Viết lời chúc năm mới |
| `thank_letter` | Lunar New Year | Viết thư cảm ơn |
| `lixi` | Lunar New Year | Mở lì xì may mắn |
| `lantern_parade` | Mid Autumn | Diễu hành đèn lồng |
| `quiz` | Mid Autumn | Đố vui Trung Thu |
| `countdown` | Mid Autumn | Đếm ngược trăng tròn |
| `ghost_hunt` | Halloween | Săn ma (có asyncio.Lock) |
| `treasure_hunt` | Halloween | Đào kho báu (grid-based) |
| `trash_sort` | Halloween | Phân loại rác |
| `snowman` | Christmas | Xây người tuyết |
| `secret_santa` | Christmas | Tặng quà bí mật (matching system) |
| `leaf_collect` | Christmas | Thu thập lá (grid-based) |
| `beach_cleanup` | Christmas | Dọn dẹp bãi biển |

### Services Architecture (9 Services)
| Service | Chức năng |
|---------|-----------|
| `EventService` | Quản lý lifecycle event (start/stop/status) |
| `ParticipationService` | Track participation, currency, contributions |
| `CommunityGoalService` | Server-wide goals với milestone rewards |
| `ShopService` | Event shop với stock management |
| `QuestService` | Event-specific quests |
| `TitleService` | Unlock và quản lý danh hiệu |
| `LifecycleService` | Auto-start/end events theo schedule |
| `RotationService` | Yearly content rotation (fish, items) |
| `DatabaseService` | Low-level DB operations |

### Community Goals System
Mục tiêu chung cho cả server, khi đạt milestone sẽ unlock rewards:
```
┌─────────────────────────────────────────────────┐
│  Progress: ████████░░░░░░░░░░░░  42%            │
│  Milestones: ✅ 25%  ⏳ 50%  🔒 75%  🔒 100%     │
└─────────────────────────────────────────────────┘
```
- Tiered rewards với title unlocks
- Contributions từ minigames được track
- **FIX Applied**: `update_community_progress(guild_id, event_id, progress)` 

### Event Currency & Shop
| Currency | Nguồn | Sử dụng |
|----------|-------|---------|
| Event Tokens | Minigames, daily check-in | Event Shop items |
| Contribution Points | Community goals | Leaderboard ranking |

### Fishing Hook Integration
`event_fish_hook.py` tích hợp với Fishing module:
- Seasonal fish spawns (từ `data/seasonal/pool.json`)
- Event-specific loot drops với pool rotation
- Yearly versioning (vd: `fish_2026_tet_*`)

### Database Tables
```sql
seasonal_events (guild_id, event_id, event_type, status, start_time, end_time, config)
event_participation (user_id, guild_id, event_id, currency, contribution, streak, last_checkin)
event_community_progress (guild_id, event_id, current_progress, target)
event_milestones_reached (guild_id, event_id, milestone_key, reached_at)
event_purchases (user_id, guild_id, event_id, item_key, quantity, purchased_at)
event_user_titles (user_id, title_key, title_name, event_id, unlocked_at)
event_active_titles (user_id, guild_id, title_key)
```

### Background Tasks
- `lifecycle_check_loop`: Auto-start/end events theo schedule (mỗi 1 phút)
- `minigame_spawn_loop`: Random spawn minigames (30-60 phút)
- `progress_sync_loop`: Sync community progress (mỗi 5 phút)

### Recent Fixes (Jan 2026)
-  SQL placeholders converted from `?` to `$1, $2` for asyncpg
-  `update_community_progress` implemented (was no-op `pass`)
-  `unlock_title` argument order fixed
-  All minigame files updated to call 3-arg `update_community_progress`
-  `asyncio.Lock` added to `ghost_hunt.py` for race condition prevention
-  All Views have `on_timeout` for cleanup

### Critical Notes
- Event config trong `data/seasonal/events/` và `data/seasonal/pool.json`
- Minigame Views có timeout cleanup để prevent memory leaks
- Rewards scale theo participation, not server size
- Title system persists across events

---

## 26. ANALYTICS MODULE
**Files**: `cogs/analytics.py`
**Type**: Background Service (No User Commands)

### Features
- Tracks command usage (slash & prefix)
- Tracks user activity (join/leave/voice)
- Error tracking per command/user
- Peak usage statistics

### Database Tables
```sql
command_usage (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    guild_id BIGINT,
    command_name TEXT,
    is_slash BOOLEAN,
    used_at TIMESTAMP DEFAULT NOW(),
    error_message TEXT
)

user_activity (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    guild_id BIGINT,
    activity_type TEXT, -- 'JOIN', 'LEAVE', 'VOICE_JOIN', 'VOICE_LEAVE'
    created_at TIMESTAMP DEFAULT NOW(),
    details JSONB
)
```

### Critical Notes
- All analytics calls must be non-blocking (fire-and-forget)
- Usage data is critical for balancing and feature planning
- Error messages are truncated to 1000 chars to save space

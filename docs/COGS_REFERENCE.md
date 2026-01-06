# BHNBot - Tài Liệu Tham Chiếu Cogs (Complete Technical Reference)

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
| `/chao` | Chào buổi sáng nhận 10 hạt (5h-12h) |
| `/tuido [user]` | Xem số dư, cần câu, túi đồ |
| `/top` | Bảng xếp hạng đại gia |
| `/themhat [user] [amount]` | (Admin) Cộng hạt |

### Features
- Chat Reward: 1-3 hạt mỗi 60s
- Reaction Reward: nhận hạt khi được thả cảm xúc
- Voice Reward: 2 hạt / 10 phút voice
- Weekly Welfare: 500 hạt cho người nghèo mỗi Chủ Nhật

### Database
- `users`: user_id, seeds, last_daily, last_chat_reward...
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
| `/thuhoach` | (Admin) Thu hoạch |

### Mechanics
- 6 giai đoạn: Hạt mầm → Nảy mầm → Cây non → Trưởng thành → Ra hoa → Kết trái
- Yêu cầu tăng 25% mỗi mùa

### Harvest Rewards
- Top 1: 13k hạt + Role "Thần Nông"
- Top 2: 5k, Top 3: 3k, Others: 1.5k
- Server buff: x2 hạt 24h

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
**File**: `cogs/relationship/cog.py`

### Commands
| Lệnh | Chức năng |
|------|-----------|
| `/tangqua` | Tặng quà (cafe, flower, ring...) |

### Features
- Gửi ẩn danh
- Lời nhắn ngẫu nhiên dí dỏm

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

## 18. VIP SYSTEM
**Files**: `cogs/vip_commands.py`, `core/services/vip_service.py`

### Tiers
| Tier | Tên | Chi phí/30 ngày |
|------|-----|-----------------|
| 0 | Member | Miễn phí |
| 1 | Bạc 🥈 | 50,000 Hạt |
| 2 | Vàng 🥇 | 150,000 Hạt |
| 3 | Kim Cương 💎 | 500,000 Hạt |

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

### MUST DO
1. Sử dụng `async with db_manager.transaction()` cho mọi thay đổi tài sản
2. Không blocking I/O trong async functions
3. Chạy `lsp_diagnostics` sau mỗi thay đổi (nếu có)
4. Test import trước khi commit

### MUST NOT DO
1. KHÔNG xóa hoặc rename functions mà không kiểm tra references
2. KHÔNG thay đổi database schema mà không update migrations
3. KHÔNG hardcode Discord IDs
4. KHÔNG sử dụng `type: ignore` trừ khi thực sự cần thiết
5. KHÔNG pay-to-win cho VIP features

---

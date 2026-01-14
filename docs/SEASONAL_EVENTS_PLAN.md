# 🎋 BHNBot Seasonal Events System - Complete Plan

> **Version:** 2.0  
> **Last Updated:** 2026-01-12  
> **Status:** Implementation Phase  

---

## 📑 Mục Lục

1. [Tổng Quan Hệ Thống](#1-tổng-quan-hệ-thống)
2. [Hệ Thống Title, Badge, Role](#2-hệ-thống-title-badge-role)
3. [Hệ Thống Quest](#3-hệ-thống-quest)
4. [Community Goal & Milestones](#4-community-goal--milestones)
5. [Event Fish System](#5-event-fish-system)
6. [Spring Event - Lễ Hội Hoa Xuân](#6-spring-event---lễ-hội-hoa-xuân)
7. [Summer Event - Lễ Hội Biển](#7-summer-event---lễ-hội-biển)
8. [Autumn Event - Thu Hoạch Mùa Thu](#8-autumn-event---thu-hoạch-mùa-thu)
9. [Winter Event - Đông Ấm Áp](#9-winter-event---đông-ấm-áp)
10. [Halloween Mini Event](#10-halloween-mini-event)
11. [Earth Day Mini Event](#11-earth-day-mini-event)
12. [Mid-Autumn Mini Event](#12-mid-autumn-mini-event)
13. [Birthday Mini Event](#13-birthday-mini-event)
14. [Database Schema](#14-database-schema)
15. [Folder Structure & Implementation](#15-folder-structure--implementation)
16. [Extensibility & Data-Driven Design](#16-extensibility--data-driven-design)
17. [Testing Strategy](#17-testing-strategy)

---

## 1. Tổng Quan Hệ Thống

### 1.1 Lịch Sự Kiện Năm

| Event | Thời Gian | Duration | Loại |
|-------|-----------|----------|------|
| 🌸 Lễ Hội Hoa Xuân | 01/02 - 15/02 | 14 ngày | Major |
| 💚 Earth Day | 20/04 - 24/04 | 5 ngày | Mini |
| 🌊 Lễ Hội Biển | 01/06 - 21/06 | 21 ngày | Major |
| 🌙 Tết Trung Thu | 10/09 - 15/09 | 6 ngày | Mini |
| 🍂 Thu Hoạch Mùa Thu | 15/09 - 30/09 | 15 ngày | Major |
| 🎃 Halloween | 25/10 - 31/10 | 7 ngày | Mini |
| ❄️ Đông Ấm Áp | 20/12 - 05/01 | 16 ngày | Major |
| 🎂 Sinh Nhật Server | TBD | 3 ngày | Mini |

### 1.2 Cấu Hình Kênh

```
/config set kenh_sukien:#thông-báo-sự-kiện
/config set kenh_sukien_auto:#minigame-tự-động  
/config set role_sukien:@SuKien
```

| Kênh | Mục Đích |
|------|----------|
| `kenh_sukien` | Thông báo bắt đầu/kết thúc, Community Goal, Leaderboard, Secret Santa |
| `kenh_sukien_auto` | Auto minigames (Treasure Hunt, Ghost Spawn, Boat Race, etc.) |
| `role_sukien` | Ping khi có minigame hoặc thông báo quan trọng |

### 1.3 Commands

#### User Commands

| Command | Mô Tả |
|---------|-------|
| `/sukien` | Xem sự kiện hiện tại, currency, tiến độ cá nhân |
| `/sukien nhiemvu` | Xem daily + fixed quests của event |
| `/sukien shop` | Cửa hàng sự kiện |
| `/sukien rank` | Bảng xếp hạng currency |
| `/sukien bosuutap` | Bộ sưu tập cá sự kiện (Kỷ Vật) |
| `/sukien vuirac` | Vứt rác đúng cách (Earth Day only) |
| `/danhhieu` | Xem danh sách title đã unlock |
| `/danhhieu set <name>` | Đổi title hiển thị trong profile |

#### Admin Commands

| Command | Mô Tả |
|---------|-------|
| `/sukien-admin start <event>` | Bắt đầu sự kiện thủ công |
| `/sukien-admin end` | Kết thúc sự kiện sớm |
| `/sukien-admin secretsanta start` | Gửi embed đăng ký Secret Santa |
| `/sukien-admin announce` | Gửi thông báo sự kiện |
| `/sukien-admin addcurrency <user> <amount>` | Debug: cộng currency |

### 1.4 Nguyên Tắc Chung

| Aspect | Quy Định |
|--------|----------|
| Event Currency | Riêng mỗi event, không thể chuyển đổi giữa events |
| Event Fish | Lưu vĩnh viễn trong "Kỷ Vật", hiển thị trong `/tuido` |
| Badges | Emoji, lưu trong `badges_display`, hiển thị `/hoso` |
| Titles | Text hiển thị dưới username trong `/hoso` |
| Roles | Chỉ tạo Discord Role khi đạt 100% Community Goal |
| Daily Quests | Event quests SONG SONG với daily quests thường |
| Minigames | Healing theme - không ai mất tiền, tất cả có thưởng |

---

## 2. Hệ Thống Title, Badge, Role

### 2.1 Title (Danh Hiệu)

**Title là gì?**
- Text hiển thị dưới username trong `/hoso`
- Mỗi user chỉ có 1 title active tại một thời điểm
- Có thể đổi qua `/danhhieu set <name>`
- Lưu trong database, KHÔNG phải Discord Role

**Hiển thị trong Profile:**
```
┌─────────────────────────────────────┐
│  [Avatar]                           │
│  @Username                          │
│  ✨ "Tinh Linh Mùa Xuân" ✨         │  ← TITLE
│  ─────────────────────────────────  │
│  🌱 Seeds: 5,000                    │
│  🐟 Fish: 150                       │
│  ...                                │
└─────────────────────────────────────┘
```

**Cách Nhận Title:**
| Nguồn | Ví Dụ |
|-------|-------|
| Milestone 50% | "Xuân Đến", "Thủy Thủ", "Lòng Biết Ơn" |
| Fixed Quest | "Rồng Vàng" (câu được Epic fish) |
| Special Achievement | "Nhà Tiên Tri" (đoán đúng 3 lần Boat Race) |

### 2.2 Badge (Huy Hiệu)

**Badge là gì?**
- Emoji hiển thị trong profile (tối đa 8)
- Có thể có nhiều badges cùng lúc
- Mua trong Event Shop hoặc unlock qua quest
- Lưu trong `badges_display` (JSON array)

**Event Badges:**
| Event | Badge | Cách Nhận |
|-------|-------|-----------|
| Spring | 🌸 | Mua 1000 🌸 hoặc sưu tầm đủ 7 cá |
| Summer | 🐚 | Mua 1200 🐚 hoặc sưu tầm đủ 7 cá |
| Autumn | 🍂 | Mua 1000 🍂 hoặc gửi 30 thư cảm ơn |
| Winter | ❄️ | Mua 1200 ❄️ hoặc tham gia Secret Santa |
| Halloween | 🎃 | Bắt 50 con ma |
| Earth Day | 💚 | Vứt 100 rác |
| Mid-Autumn | 🌙 | Thắp 100 đèn lồng |
| Birthday | 🎂 | Tham gia + Community Goal 100% |

### 2.3 Role (Discord Role)

**Khi nào tạo Role?**
- CHỈ khi đạt 100% Community Goal
- Role đặc biệt, hiếm, có ý nghĩa
- Gán cho TẤT CẢ participants (người có ít nhất 1 đóng góp)

**Naming Convention:**
```
🌸 Xuân Đến 2026
🌊 Thủy Thủ 2026
🍂 Thu Vàng 2026
❄️ Mùa Đông 2026
```

---

## 3. Hệ Thống Quest

### 3.1 Event Quests vs Daily Quests

| Aspect | Daily Quests (Hiện tại) | Event Quests (Mới) |
|--------|-------------------------|-------------------|
| Scope | Server-wide | Server-wide |
| Duration | 1 ngày | Cả event |
| Generation | Random 3/ngày | Fixed theo event |
| Reward | Seeds | Event Currency |
| Thay thế? | ❌ Vẫn chạy | ➕ Thêm vào |

**Kết luận:** Event Quests chạy SONG SONG với Daily Quests, không thay thế.

### 3.2 Event Daily Quests

- 2-3 quests random từ pool của event
- Reset mỗi ngày 00:00 Vietnam timezone
- Reward: Event Currency

**UI Example:**
```
📋 NHIỆM VỤ SỰ KIỆN HÔM NAY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 🎣 Câu 20 cá        [12/20] +30 🌸
2. 🧧 Gửi 3 lì xì      [1/3]   +50 🌸
3. 💬 Chat 50 tin nhắn [45/50] +20 🌸
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 3.3 Event Fixed Quests

- Mục tiêu lớn, cả event để hoàn thành
- Không reset
- Reward: Title, Badge, hoặc currency lớn

**UI Example:**
```
🏆 THÀNH TỰU SỰ KIỆN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 🐉 Câu được Cá Rồng Vàng     [0/1]  → Title "Rồng Vàng"
2. 🧧 Gửi tổng 50 lì xì         [23/50] → +500 🌸
3. 🌸 Sưu tầm đủ 7 loại cá      [4/7]   → Badge 🌸
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 4. Community Goal & Milestones

### 4.1 Community Goal

**Community Goal là gì?**
- Mục tiêu TOÀN SERVER cùng đóng góp
- Tiến độ cộng dồn từ tất cả thành viên
- Khi đạt milestone → TOÀN SERVER được thưởng

**Hiển thị:**
- Kênh: `kenh_sukien`
- Embed được pin và update mỗi 6 giờ hoặc khi đạt milestone

**UI Example:**
```
🌸 MỤC TIÊU CỘNG ĐỒNG - LỄ HỘI HOA XUÂN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Thu thập 50,000 🌸 Hoa Đào

📊 Tiến độ: 32,450 / 50,000 (64.9%)
[████████████████░░░░░░░░░] 

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 25% - Tất cả +100 seeds [ĐÃ ĐẠT]
✅ 50% - Title "Xuân Đến" [ĐÃ ĐẠT]
⏳ 75% - x2 fishing 24h [64.9%]
⏳ 100% - Role + Background miễn phí
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 4.2 Milestone Rewards

| Milestone | Reward | Cách Nhận |
|-----------|--------|-----------|
| 25% | +100 seeds cho tất cả participants | Tự động cộng khi đạt |
| 50% | Title unlock cho tất cả participants | Tự động unlock, `/danhhieu set` để dùng |
| 75% | Buff x2 cho tất cả (24h) | Tự động activate |
| 100% | Discord Role + Free Background | Role tự gán, BG vào inventory |

**Ai được nhận?**
- Participants = User có ít nhất 1 đóng góp trong event
- Không tham gia = không nhận milestone rewards

### 4.3 Community Goals Mỗi Event

| Event | Goal | Đơn vị |
|-------|------|--------|
| Spring | 50,000 | 🌸 Hoa Đào collected |
| Summer | 100 | Kho báu tìm được |
| Autumn | 500 | Thư cảm ơn gửi |
| Winter | 10,000 | Phần người tuyết góp |
| Halloween | 1,000 | Con ma bắt được |
| Earth Day | 5,000 | Rác thu gom |
| Mid-Autumn | 2,000 | Đèn lồng thắp |
| Birthday | 500 | Lời chúc gửi |

---

## 5. Event Fish System

### 5.1 Thiết Kế

- Event fish RIÊNG BIỆT với `fishing_data.json`
- Lưu trong `data/events/<event>.json`
- 3 tier: Common, Rare, Epic
- Khi câu cá trong event: 15% chance ra event fish

### 5.2 Drop Rates

| Tier | Drop Rate | Currency Reward |
|------|-----------|-----------------|
| Common | 70% | 5 |
| Rare | 25% | 15 |
| Epic | 5% | 50 |

### 5.3 Kỷ Vật (Permanent Collection)

- Event fish lưu VĨNH VIỄN trong `event_fish_collection`
- Hiển thị trong `/sukien bosuutap`
- Hiển thị trong `/tuido` section "Kỷ Vật Sự Kiện"

---

## 6. Spring Event - Lễ Hội Hoa Xuân

### 6.1 Thông Tin Cơ Bản

| Thuộc Tính | Giá Trị |
|------------|---------|
| Event ID | `spring_2026` |
| Tên | Lễ Hội Hoa Xuân |
| Thời gian | 01/02 - 15/02 (14 ngày) |
| Theme | Tết Nguyên Đán + Valentine's |
| Currency | 🌸 Hoa Đào |
| Community Goal | Thu thập 50,000 🌸 |
| Color | #FFB7C5 (hồng đào) |

### 6.2 Milestones

| % | Reward | Mô Tả |
|---|--------|-------|
| 25% | +100 seeds | Tự động cộng |
| 50% | Title "Xuân Đến" | Tự động unlock |
| 75% | x2 fishing 24h | Buff activate |
| 100% | Role "🌸 Xuân Đến 2026" + Background "Hoa Đào" | Role + BG vào inventory |

### 6.3 Cách Kiếm Currency

| Hoạt Động | 🌸 Hoa Đào | Ghi Chú |
|-----------|------------|---------|
| Câu cá event (Common) | +5 | Mỗi con |
| Câu cá event (Rare) | +15 | Mỗi con |
| Câu cá event (Epic) | +50 | Mỗi con |
| Gửi lì xì `/sukien lixi @user` | +5-25 | Người gửi |
| Nhận lì xì | +10-50 | Người nhận |
| Lì Xì Trời Cho (auto) | +20-100 | Click button |
| Daily check-in `/chao` | +30 | Bonus thêm |
| Voice 10 phút | +15 | Stack với voice rewards |
| Cảm ơn người khác | +5 | Detect "cảm ơn" |
| Hoàn thành quest | Theo quest | Xem bảng quest |

### 6.4 Event Fish (7 con)

| Key | Tên | Emoji | Tier | Drop | 🌸 |
|-----|-----|-------|------|------|-----|
| `ca_hoa_dao` | Cá Hoa Đào | 🌸🐟 | Common | 70% | 5 |
| `ca_den_long` | Cá Đèn Lồng | 🏮🐟 | Common | 70% | 5 |
| `ca_mai_vang` | Cá Mai Vàng | 🌼🐟 | Common | 70% | 5 |
| `ca_than_tai` | Cá Thần Tài | 🧧🐟 | Rare | 25% | 15 |
| `ca_phuc_loc` | Cá Phúc Lộc | 🎊🐟 | Rare | 25% | 15 |
| `ca_phao_hoa` | Cá Pháo Hoa | 🎆🐟 | Rare | 25% | 15 |
| `ca_rong_vang` | Cá Rồng Vàng | 🐉✨ | Epic | 5% | 50 |

### 6.5 Minigames

#### 6.5.1 Lì Xì May Mắn (Manual)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Command | `/sukien lixi @user` |
| Cooldown | 1 lần/người/ngày |
| Người gửi nhận | 5-25 🌸 (random) |
| Người nhận được | 10-50 🌸 (random) |
| Valentine Bonus (14/02) | x2 rewards |

**Flow:**
```
User: /sukien lixi @Friend
Bot: 🧧 Bạn đã gửi lì xì cho @Friend!
     Bạn nhận: +18 🌸
     @Friend nhận: +35 🌸
```

#### 6.5.2 Lì Xì Trời Cho (Auto Spawn)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Spawn | Random 3-5 lần/ngày |
| Channel | `kenh_sukien_auto` |
| Max người nhận | 5 người đầu tiên click |
| Reward | Random 20-100 🌸 mỗi người |
| Timeout | 60 giây |

**UI:**
```
🧧 LÌ XÌ TRỜI CHO!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ông Địa đang phát lì xì! Nhanh tay nhận nào!

🎁 Còn lại: 5/5 phần
⏰ Hết hạn: <t:xxx:R>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[🧧 Nhận Lì Xì]
```

**Kết quả:**
```
🧧 LÌ XÌ ĐÃ HẾT!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Người may mắn:
🎁 @User1 → +87 🌸
🎁 @User2 → +45 🌸
🎁 @User3 → +62 🌸
🎁 @User4 → +33 🌸
🎁 @User5 → +91 🌸
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 6.6 Event Shop

| Key | Tên | Giá | Loại | Mô Tả | Limit |
|-----|-----|-----|------|-------|-------|
| `bg_spring` | Background Hoa Đào | 500 🌸 | Cosmetic | Profile background | 1/user |
| `frame_spring` | Khung Đèn Lồng | 300 🌸 | Cosmetic | Avatar frame | 1/user |
| `lucky_envelope` | Phong Bao May Mắn | 100 🌸 | Consumable | x2 seeds 1 giờ | 5/user |
| `badge_spring` | Badge 🌸 | 1000 🌸 | Badge | Permanent | 1/user |
| `valentine_card` | Thiệp Valentine | 150 🌸 | Gift | +20 kindness khi tặng | Unlimited |

### 6.7 Daily Quests (2-3 random/ngày)

| Quest ID | Tên | Target | Reward |
|----------|-----|--------|--------|
| `spring_fish` | Câu Cá Mùa Xuân | 20 cá | +30 🌸 |
| `spring_lixi` | Gửi Lì Xì | 3 lần | +50 🌸 |
| `spring_chat` | Trò Chuyện | 50 tin nhắn | +20 🌸 |
| `spring_react` | Tương Tác | 20 reactions | +25 🌸 |
| `spring_voice` | Voice Chat | 30 phút | +40 🌸 |
| `spring_tree` | Góp Cây | 50 hạt | +25 🌸 |

### 6.8 Fixed Quests

| Quest ID | Tên | Target | Reward |
|----------|-----|--------|--------|
| `spring_epic_fish` | Rồng Vàng Xuất Hiện | Câu 1 Cá Rồng Vàng | Title "Rồng Vàng" |
| `spring_all_fish` | Bộ Sưu Tập Xuân | 7/7 loại cá event | Badge 🌸 |
| `spring_lixi_50` | Người Hào Phóng | Gửi 50 lì xì | +500 🌸 |
| `spring_minigame` | Chơi Hết Mình | 20 minigames | +300 🌸 |
| `spring_currency_1000` | Triệu Phú Hoa Đào | Kiếm 1000 🌸 | +200 🌸 bonus |

### 6.9 Special: Valentine's Day (14/02)

- Tất cả lì xì rewards x2
- Event fish drop rate +50%
- Exclusive item: "💌 Thiệp Tình Yêu" chỉ mua được ngày này
- Buddy activities cho thêm 50% currency

---

## 7. Summer Event - Lễ Hội Biển

### 7.1 Thông Tin Cơ Bản

| Thuộc Tính | Giá Trị |
|------------|---------|
| Event ID | `summer_2026` |
| Tên | Lễ Hội Biển |
| Thời gian | 01/06 - 21/06 (21 ngày) |
| Theme | Beach vacation, tropical adventure |
| Currency | 🐚 Vỏ Sò |
| Community Goal | Tìm 100 kho báu |
| Color | #00CED1 (turquoise) |

### 7.2 Milestones

| % | Reward |
|---|--------|
| 25% | +150 seeds |
| 50% | Title "Thủy Thủ" |
| 75% | x2 fishing 24h |
| 100% | Role "🌊 Thủy Thủ 2026" + Background "Hoàng Hôn Biển" |

### 7.3 Event Fish (7 con)

| Key | Tên | Emoji | Tier | 🐚 |
|-----|-----|-------|------|-----|
| `ca_sao_bien` | Cá Sao Biển | ⭐🐟 | Common | 5 |
| `ca_san_ho` | Cá San Hô | 🪸🐟 | Common | 5 |
| `ca_sua_xanh` | Cá Sứa Xanh | 🪼🐟 | Common | 5 |
| `ca_ngoc_trai` | Cá Ngọc Trai | 🦪🐟 | Rare | 15 |
| `ca_cau_vong` | Cá Cầu Vồng | 🌈🐟 | Rare | 15 |
| `ca_mat_troi` | Cá Mặt Trời | ☀️🐟 | Rare | 15 |
| `ca_than_bien` | Cá Thần Biển | 🔱✨ | Epic | 50 |

### 7.4 Minigames

#### 7.4.1 Săn Kho Báu (Auto Spawn)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Spawn | Random 4-6 lần/ngày |
| Channel | `kenh_sukien_auto` |
| UI | 3x3 grid buttons, 1 ô là kho báu |
| Reward đúng | +50-100 🐚 + 1 kho báu vào Goal |
| Reward sai | "Chỉ có cát!" (không mất gì) |
| Timeout | 60 giây |

**UI:**
```
🏝️ KHO BÁU XUẤT HIỆN!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Có kho báu ẩn giấu đâu đó trên bãi biển!
Mỗi người chỉ được đào 1 ô!

⏰ Hết hạn: <t:xxx:R>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[🏖️ 1] [🏖️ 2] [🏖️ 3]
[🏖️ 4] [🏖️ 5] [🏖️ 6]
[🏖️ 7] [🏖️ 8] [🏖️ 9]
```

#### 7.4.2 Đua Thuyền (Scheduled + Random)

**Thông số kỹ thuật:**

| Thuộc Tính | Giá Trị |
|------------|---------|
| Scheduled | 20:00 hàng ngày |
| Random | 2-3 lần/ngày |
| Số thuyền | 8 |
| Số ô đường đua | 15 |
| Edit interval | 2.5 giây |
| Thời gian đua | ~38 giây |

**8 Thuyền:**

| Emoji | Tên | Đặc Điểm (Hiển thị) | Stats Ẩn |
|-------|-----|---------------------|----------|
| ⛵ | Sóng Bạc | "Cân bằng, ổn định" | Speed: 2, Luck: 50%, Resist: 30% |
| 🚤 | Gió Đông | "Nhanh nhưng dễ gặp sự cố" | Speed: 3, Luck: 30%, Resist: 10% |
| 🛥️ | Hải Âu | "Chậm chắc, ít tai nạn" | Speed: 1.5, Luck: 40%, Resist: 60% |
| 🚢 | Đại Dương | "Khổng lồ, immune sóng nhỏ" | Speed: 1, Luck: 50%, Resist: 80% |
| ⛴️ | Thủy Triều | "Bí ẩn, không ai đoán được" | Speed: random(1-4), Luck: 70%, Resist: 20% |
| 🛶 | Sóng Thần | "Cực nhanh, cực rủi ro" | Speed: 4, Luck: 20%, Resist: 0% |
| 🚣 | Rái Cá | "Nhỏ gọn, dễ lách sóng" | Speed: 2.5, Luck: 60%, Resist: 40% |
| 🛳️ | Long Vương | "Huyền thoại, khó lường" | Speed: random(0-5), Luck: 80%, Resist: 50% |

**Giải thưởng:**

| Hạng | Thưởng | Mô Tả |
|------|--------|-------|
| 🥇 1st | 100 🐚 | Vô địch |
| 🥈 2nd | 50 🐚 | Á quân |
| 🥉 3rd | 25 🐚 | Hạng 3 |
| 🎖️ Tham gia | 10 🐚 | Không top 3 |

**Bonus:**
- Underdog Victory: Thuyền win rate < 15% thắng → x2 thưởng
- Photo Finish: 2+ thuyền về cùng → Tất cả được giải cao hơn
- Perfect Prediction: Đoán đúng 3 lần liên tiếp → Badge "🔮 Nhà Tiên Tri"

**Sự kiện trong đua:**

| Event | Emoji | Tần Suất | Hiệu Ứng |
|-------|-------|----------|----------|
| Gió Thuận | 💨 | 15% | +2 ô |
| Sóng Lớn | 🌊 | 12% | -1 ô |
| Cá Heo Giúp | 🐬 | 8% | +2 ô |
| Rái Cá Đẩy | 🦦 | 8% | +3 ô |
| Mắc Rong Biển | 🌿 | 10% | -2 ô, đứng 1 lượt |
| Turbo | ⚡ | 5% | +4 ô |
| Động Cơ Hỏng | 🔧 | 5% | Đứng 1 lượt |
| Sương Mù | 🌫️ | 5% | Ẩn vị trí 1 lượt |
| Hoán Đổi Vị Trí | 🔄 | 3% | 2 thuyền random đổi chỗ |
| Tiên Cá Giúp | 🧜‍♀️ | 3% | Thuyền cuối +5 ô |
| Sóng Thần | 🌊💥 | 2% | TẤT CẢ -2 ô |

**UI Giai đoạn chọn:**
```
🚤 ĐUA THUYỀN - CHỌN THUYỀN!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⛵ Sóng Bạc │ "Cân bằng, ổn định" │ 🏆 12 (42%)
🚤 Gió Đông │ "Nhanh nhưng dễ gặp sự cố" │ 🏆 18 (51%)
🛥️ Hải Âu │ "Chậm chắc, ít tai nạn" │ 🏆 8 (35%)
🚢 Đại Dương │ "Khổng lồ, immune sóng nhỏ" │ 🏆 5 (28%)
⛴️ Thủy Triều │ "Bí ẩn, không ai đoán được" │ 🏆 15 (47%)
🛶 Sóng Thần │ "Cực nhanh, cực rủi ro" │ 🏆 20 (45%)
🚣 Rái Cá │ "Nhỏ gọn, dễ lách sóng" │ 🏆 10 (38%)
🛳️ Long Vương │ "Huyền thoại, khó lường" │ 🏆 7 (32%)

👥 Người chơi: 15 │ ⏰ Bắt đầu: <t:xxx:R>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[⛵] [🚤] [🛥️] [🚢] [⛴️] [🛶] [🚣] [🛳️]
```

**UI Đang đua:**
```
🏁 ĐUA THUYỀN - VÒNG 8/12
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 ĐÍCH ═══════════════════════════════════════╗
                                                ║
🛶 Sóng Thần ════════════════════▶ 🛶 ░░░░░░░ ║ 87% ⚡
🚤 Gió Đông ═══════════════════▶ 🚤 ░░░░░░░░░ ║ 80%
⛴️ Thủy Triều ════════════════▶ ⛴️ ░░░░░░░░░░ ║ 73%
🚣 Rái Cá ══════════════════▶ 🚣 ░░░░░░░░░░░░ ║ 67%
⛵ Sóng Bạc ═════════════════▶ ⛵ ░░░░░░░░░░░░ ║ 67% 🦦
🛥️ Hải Âu ════════════════▶ 🛥️ ░░░░░░░░░░░░░░ ║ 53%
🚢 Đại Dương ══════════▶ 🚢 ░░░░░░░░░░░░░░░░░░ ║ 40%
🛳️ Long Vương ═══════▶ 🛳️ ░░░░░░░░░░░░░░░░░░░░ ║ 33% 🔧
                                                ║
🏁 XUẤT PHÁT ════════════════════════════════════╝
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📢 DIỄN BIẾN:
🌊 Sóng lớn! Đại Dương vượt qua nhờ thân tàu khổng lồ!
⚡ Sóng Thần kích hoạt TURBO! Vượt lên dẫn đầu!
🦦 Đàn rái cá đẩy Sóng Bạc tiến lên!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 7.5 Event Shop

| Tên | Giá | Loại |
|-----|-----|------|
| Background Hoàng Hôn Biển | 600 🐚 | Cosmetic |
| Frame Sóng Biển | 350 🐚 | Cosmetic |
| Mồi Vàng x5 | 150 🐚 | Consumable |
| Kem Dừa (x2 XP 1h) | 80 🐚 | Consumable |
| Badge 🐚 | 1200 🐚 | Badge |

### 7.6 Daily Quests

| Quest | Target | Reward |
|-------|--------|--------|
| Câu 25 cá | 25 cá | +35 🐚 |
| Tìm 1 kho báu | 1 kho | +60 🐚 |
| Voice 45 phút | 45p | +50 🐚 |
| React 25 lần | 25 | +30 🐚 |
| Tham gia 1 đua thuyền | 1 race | +40 🐚 |

### 7.7 Fixed Quests

| Quest | Target | Reward |
|-------|--------|--------|
| Câu Cá Thần Biển (Epic) | 1 con | Title "Vua Biển Cả" |
| Sưu tầm 7 loại cá | 7/7 | Badge 🐚 |
| Tìm 20 kho báu | 20 | +600 🐚 |
| Thắng 5 cuộc đua | 5 wins | Title "Thuyền Trưởng" |
| Đoán đúng 3 lần liên tiếp | 3 streak | Badge "🔮 Nhà Tiên Tri" |

---

## 8. Autumn Event - Thu Hoạch Mùa Thu

### 8.1 Thông Tin Cơ Bản

| Thuộc Tính | Giá Trị |
|------------|---------|
| Event ID | `autumn_2026` |
| Tên | Thu Hoạch Mùa Thu |
| Thời gian | 15/09 - 30/09 (15 ngày) |
| Theme | Harvest, gratitude, cozy |
| Currency | 🍂 Lá Vàng |
| Community Goal | Gửi 500 thư cảm ơn |
| Color | #DAA520 (golden) |

### 8.2 Milestones

| % | Reward |
|---|--------|
| 25% | +100 seeds |
| 50% | Title "Lòng Biết Ơn" |
| 75% | x2 tree XP 24h |
| 100% | Role "🍂 Thu Vàng 2026" + Background "Rừng Thu" |

### 8.3 Event Fish (7 con)

| Key | Tên | Emoji | Tier | 🍂 |
|-----|-----|-------|------|-----|
| `ca_la_phong` | Cá Lá Phong | 🍁🐟 | Common | 5 |
| `ca_hat_de` | Cá Hạt Dẻ | 🌰🐟 | Common | 5 |
| `ca_nam_rung` | Cá Nấm Rừng | 🍄🐟 | Common | 5 |
| `ca_hoang_hon` | Cá Hoàng Hôn | 🌅🐟 | Rare | 15 |
| `ca_suong_mu` | Cá Sương Mù | 🌫️🐟 | Rare | 15 |
| `ca_trang_thu` | Cá Trăng Thu | 🌙🐟 | Rare | 15 |
| `ca_phuong_hoang` | Cá Phượng Hoàng | 🔥✨ | Epic | 50 |

### 8.4 Minigames

#### 8.4.1 Thư Cảm Ơn (Manual)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Channel | `kenh_sukien` (embed với button) |
| Cooldown | 3 thư/ngày gửi |
| Max nhận | Unlimited |
| Message length | Max 200 ký tự |
| Reward | Cả 2 nhận 20 🍂 |
| Goal contribution | +1 thư vào Community Goal |

**UI:**
```
✉️ THƯ CẢM ƠN MÙA THU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gửi lời cảm ơn đến ai đó trong server!

📬 Thư đã gửi hôm nay: 1/3
🌍 Tổng thư server: 234/500
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[✉️ Viết Thư Mới]
```

**Modal:**
```
📝 VIẾT THƯ CẢM ƠN
━━━━━━━━━━━━━━━━━━━━
Gửi đến: [Select User]
Nội dung: [Text Input - max 200 chars]
━━━━━━━━━━━━━━━━━━━━
[Gửi] [Hủy]
```

**DM cho người nhận:**
```
💌 THƯ CẢM ƠN MÙA THU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Từ: @SenderName

"Cảm ơn bạn đã luôn giúp đỡ mình trong server!"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bạn nhận được: +20 🍂 Lá Vàng
```

#### 8.4.2 Nhặt Lá (Auto Spawn)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Spawn | Random 4-5 lần/ngày |
| Channel | `kenh_sukien_auto` |
| UI | 3x3 grid, 3-5 ô có lá |
| Mỗi người | Chỉ click được 1 ô |
| Reward/lá | +5-15 🍂 |
| Timeout | 60 giây |

**UI:**
```
🍂 LÁ VÀNG RƠI!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lá vàng đang rơi khắp nơi! Nhặt lấy một chiếc!
(Mỗi người chỉ được nhặt 1 lá)

⏰ Hết hạn: <t:xxx:R>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[🍂] [🌳] [🍂]
[🌳] [🍂] [🌳]
[🌳] [🍂] [🍂]
```

#### 8.4.3 Pha Trà (Manual)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Command | `/sukien phatra` |
| Cooldown | 4 giờ |
| Cơ chế | Chọn 3 nguyên liệu từ 6 options |
| Reward | 25-200 🍂 tùy combo |

**Nguyên liệu:**
- 🌿 Bạc Hà
- 🍯 Mật Ong
- 🍋 Chanh
- 🌸 Hoa Cúc
- 🍵 Lá Trà
- 🫚 Gừng

**Combo:**

| Combo | Kết Quả | Reward |
|-------|---------|--------|
| 🌿+🍯+🍋 | Trà Thượng Hạng | 100 🍂 |
| 🌸+🍵+🍯 | Trà Thượng Hạng | 100 🍂 |
| 🫚+🍯+🍋 | Trà Ấm | 75 🍂 |
| 🍵+🫚+🌿 | Trà Thảo Mộc | 75 🍂 |
| Bất kỳ 2 match | Trà Ngon | 50 🍂 |
| Không match | Trà Lạ Miệng | 25 🍂 |
| 🍵+🍯+🌸+🌿+🫚+🍋 (secret) | Golden Recipe | 200 🍂 |

### 8.5 Event Shop

| Tên | Giá | Loại |
|-----|-----|------|
| Background Rừng Thu | 500 🍂 | Cosmetic |
| Frame Lá Phong | 300 🍂 | Cosmetic |
| Trà Ấm (x2 XP 1h) | 80 🍂 | Consumable |
| Khăn Len | 200 🍂 | Cosmetic |
| Badge 🍂 | 1000 🍂 | Badge |

### 8.6 Daily Quests

| Quest | Target | Reward |
|-------|--------|--------|
| Gửi 2 thư cảm ơn | 2 thư | +40 🍂 |
| Nhặt 30 lá | 30 lá | +25 🍂 |
| Góp cây 30 hạt | 30 hạt | +30 🍂 |
| Pha 1 trà | 1 lần | +35 🍂 |
| Chat 40 tin | 40 tin | +20 🍂 |

### 8.7 Fixed Quests

| Quest | Target | Reward |
|-------|--------|--------|
| Câu Cá Phượng Hoàng | 1 con | Title "Phượng Hoàng" |
| Gửi 30 thư cảm ơn | 30 thư | Badge 🍂 |
| Pha Golden Recipe | 1 lần | Title "Trà Sư" |
| Nhận 20 thư | 20 thư | +300 🍂 |
| Sưu tầm 7 loại cá | 7/7 | +400 🍂 |

---

## 9. Winter Event - Đông Ấm Áp

### 9.1 Thông Tin Cơ Bản

| Thuộc Tính | Giá Trị |
|------------|---------|
| Event ID | `winter_2026` |
| Tên | Đông Ấm Áp |
| Thời gian | 20/12 - 05/01 (16 ngày) |
| Theme | Christmas + New Year |
| Currency | ❄️ Bông Tuyết |
| Community Goal | Xây 10,000 phần người tuyết |
| Color | #4169E1 (royal blue) |

### 9.2 Milestones

| % | Reward |
|---|--------|
| 25% | +150 seeds |
| 50% | Title "Tinh Linh Tuyết" |
| 75% | x2 all rewards 24h |
| 100% | Role "❄️ Mùa Đông 2026" + Background "Đêm Tuyết" |

### 9.3 Event Fish (7 con)

| Key | Tên | Emoji | Tier | ❄️ |
|-----|-----|-------|------|-----|
| `ca_tuyet` | Cá Tuyết | ❄️🐟 | Common | 5 |
| `ca_thong_xanh` | Cá Thông Xanh | 🌲🐟 | Common | 5 |
| `ca_chuong_vang` | Cá Chuông Vàng | 🔔🐟 | Common | 5 |
| `ca_qua_tang` | Cá Quà Tặng | 🎁🐟 | Rare | 15 |
| `ca_ngoi_sao` | Cá Ngôi Sao | ⭐🐟 | Rare | 15 |
| `ca_keo_gay` | Cá Kẹo Gậy | 🍬🐟 | Rare | 15 |
| `ca_ong_gia_noel` | Cá Ông Già Noel | 🎅✨ | Epic | 50 |

### 9.4 Minigames

#### 9.4.1 Secret Santa

**Giai đoạn 1: Đăng ký (20/12 - 22/12)**

| Thuộc Tính | Giá Trị |
|------------|---------|
| Channel | `kenh_sukien` |
| UI | Embed + Button |
| Deadline | 22/12 23:59 |

**UI Đăng ký:**
```
🎄 SECRET SANTA 2026 🎄
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tham gia tặng quà bí mật cho thành viên khác!

📅 Đăng ký: Đến 22/12 23:59
🎁 Tặng quà: 23/12 - 24/12
🎉 Reveal: 25/12 20:00

👥 Đã tham gia: 24 người
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[🎁 Tham Gia] [📋 Xem Danh Sách]
```

**Giai đoạn 2: Ghép cặp (23/12 00:00)**
- Bot random ghép cặp vòng tròn: A→B, B→C, C→A
- DM mỗi người thông tin người nhận

**DM:**
```
🎅 SECRET SANTA - NHIỆM VỤ CỦA BẠN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bạn sẽ tặng quà cho: @ReceiverName

📝 Thông tin về họ:
├ Đã chơi: 45 ngày
├ Thích: Câu cá, Voice chat
└ Badge có: 🌸 🌊

🎁 Mua quà: /sukien shop
📤 Gửi quà: Bấm button bên dưới

Deadline: 24/12 23:59
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[🎁 Gửi Quà Bây Giờ]
```

**Giai đoạn 3: Tặng quà (23/12 - 24/12)**
- Chọn quà từ shop hoặc inventory
- Thêm lời chúc (optional, max 200 chars)

**Quà Secret Santa trong Shop:**

| Tên | Giá | Tier |
|-----|-----|------|
| Quà Bình Thường | 100 ❄️ | ⭐ |
| Quà Đặc Biệt | 300 ❄️ | ⭐⭐ |
| Quà Hoàn Hảo | 600 ❄️ | ⭐⭐⭐ |

**Giai đoạn 4: Reveal (25/12 20:00)**

**UI Reveal:**
```
🎊 SECRET SANTA 2026 - REVEAL! 🎊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎁 CÁC CẶP TẶNG QUÀ:

🎅 @User1 → @User2
   📦 Quà Hoàn Hảo
   💬 "Chúc bạn Giáng sinh vui vẻ!"

🎅 @User2 → @User3
   📦 Quà Đặc Biệt
   💬 "Cảm ơn đã là bạn tốt!"

... (và nhiều hơn)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 BEST GIFT (voted by server):
🥇 @User1 → @User2

Tất cả participants: +100 ❄️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### 9.4.2 Xây Người Tuyết (Auto + Manual)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Command manual | `/sukien goptuyet` |
| Cooldown manual | 10 phút |
| Auto spawn | "Tìm Nhánh Cây" 3-4 lần/ngày |
| Goal | 10,000 phần |

**UI Community:**
```
⛄ XÂY NGƯỜI TUYẾT KHỔNG LỒ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cùng nhau xây người tuyết lớn nhất server!

⛄ Tiến độ: 4,567 / 10,000 phần
[████████░░░░░░░░░░░░] 45.7%

🏆 Top đóng góp:
1. @User1 - 234 phần
2. @User2 - 189 phần
3. @User3 - 156 phần
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[⛄ Góp 1 Phần]
```

#### 9.4.3 Countdown Năm Mới (31/12)

**Timeline:**
- 23:50 - Bot gửi embed đếm ngược
- 23:55 - "⏰ Còn 5 phút!"
- 23:58 - "⏰ Còn 2 phút!"
- 23:59 - "⏰ Còn 1 phút! Sẵn sàng chưa?"
- 00:00 - "🎆🎇🎆 CHÚC MỪNG NĂM MỚI 2027! 🎆🎇🎆"
- React 🎆 trong 60 giây → +100 ❄️
- Top 10 nhanh nhất → +50 ❄️ bonus

### 9.5 Event Shop

| Tên | Giá | Loại |
|-----|-----|------|
| Background Đêm Tuyết | 600 ❄️ | Cosmetic |
| Frame Bông Tuyết | 350 ❄️ | Cosmetic |
| Sô Cô La Nóng (x2 buddy XP 3h) | 90 ❄️ | Consumable |
| Mũ Ông Già Noel | 500 ❄️ | Cosmetic |
| Hộp Quà Bí Ẩn | 200 ❄️ | Lootbox |
| Quà Bình Thường | 100 ❄️ | Secret Santa |
| Quà Đặc Biệt | 300 ❄️ | Secret Santa |
| Quà Hoàn Hảo | 600 ❄️ | Secret Santa |
| Badge ❄️ | 1200 ❄️ | Badge |

### 9.6 Daily Quests

| Quest | Target | Reward |
|-------|--------|--------|
| Góp 5 phần người tuyết | 5 | +30 ❄️ |
| Câu 15 cá | 15 | +25 ❄️ |
| Voice 30 phút | 30p | +35 ❄️ |
| Hoạt động với buddy | 20p | +40 ❄️ |

### 9.7 Fixed Quests

| Quest | Target | Reward |
|-------|--------|--------|
| Câu Cá Ông Già Noel | 1 con | Title "Santa's Helper" |
| Tham gia Secret Santa | Complete | Badge ❄️ |
| Góp 100 phần người tuyết | 100 | +400 ❄️ |
| React Countdown | Có mặt 00:00 | +100 ❄️ |
| Sưu tầm 7 loại cá | 7/7 | +500 ❄️ |

### 9.8 Night Owl Bonus

- Voice 8PM - 2AM: +50% ❄️
- Lý do: Đêm Giáng Sinh, đêm Giao Thừa

---

## 10. Halloween Mini Event

### 10.1 Thông Tin Cơ Bản

| Thuộc Tính | Giá Trị |
|------------|---------|
| Event ID | `halloween_2026` |
| Tên | Halloween Vui Vẻ |
| Thời gian | 25/10 - 31/10 (7 ngày) |
| Theme | Friendly spooky |
| Currency | 🍬 Kẹo |
| Community Goal | Săn 1,000 con ma |
| Color | #FF6600 (orange) |

### 10.2 Milestones

| % | Reward |
|---|--------|
| 50% | +100 seeds |
| 100% | Role "🎃 Halloween 2026" + Background "Đêm Ma" |

### 10.3 Event Fish (5 con)

| Key | Tên | Emoji | Tier | 🍬 |
|-----|-----|-------|------|-----|
| `ca_bi_ngo` | Cá Bí Ngô | 🎃🐟 | Common | 5 |
| `ca_doi` | Cá Dơi | 🦇🐟 | Common | 5 |
| `ca_ma` | Cá Ma | 👻🐟 | Rare | 15 |
| `ca_xuong` | Cá Xương | 💀🐟 | Rare | 15 |
| `ca_phu_thuy` | Cá Phù Thủy | 🧙✨ | Epic | 50 |

### 10.4 Minigames

#### 10.4.1 Trick or Treat (Manual)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Command | `/sukien tricktreat @user` |
| Cooldown | 1 lần/người/ngày |
| Random | Trick (-10 🍬 cả 2) hoặc Treat (+30 🍬 cả 2) |
| Target bonus | +5 🍬 (cảm ơn đã chơi cùng) |

**Flow:**
```
User: /sukien tricktreat @Friend

Bot: 🎃 @User đang Trick or Treat @Friend!
     
     [Sau 3 giây random]
     
Bot: 🍬 TREAT! 
     @User và @Friend mỗi người +30 🍬!
     
HOẶC

Bot: 👻 TRICK! 
     @User và @Friend mỗi người -10 🍬!
     (Nhưng rất vui!)
```

#### 10.4.2 Săn Ma (Auto Spawn)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Spawn | Random 5-8 lần/ngày |
| Channel | `kenh_sukien_auto` |
| Max bắt | 3 người đầu tiên |
| Reward | +20-50 🍬 mỗi người |
| Goal | +1 ma/người bắt được |
| Timeout | 30 giây |

**UI:**
```
👻 MA XUẤT HIỆN!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Một con ma đang lảng vảng! Bắt lấy nó!

⏰ Biến mất sau: <t:xxx:R>
👻 Còn: 3/3 lượt bắt
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[👻 Bắt Ma!]
```

### 10.5 Event Shop

| Tên | Giá | Loại |
|-----|-----|------|
| Background Đêm Ma | 400 🍬 | Cosmetic |
| Frame Bí Ngô | 250 🍬 | Cosmetic |
| Kẹo Ngọt (x2 luck 1h) | 50 🍬 | Consumable |
| Mặt Nạ Ma | 150 🍬 | Cosmetic |
| Badge 🎃 | 800 🍬 | Badge |

### 10.6 Quests

**Daily:**
| Quest | Target | Reward |
|-------|--------|--------|
| Bắt 3 con ma | 3 | +40 🍬 |
| Trick or treat 2 lần | 2 | +30 🍬 |
| Câu 10 cá | 10 | +20 🍬 |

**Fixed:**
| Quest | Target | Reward |
|-------|--------|--------|
| Câu Cá Phù Thủy | 1 con | Title "Phù Thủy" |
| Bắt 50 con ma | 50 | Badge 🎃 |
| Sưu tầm 5 loại cá | 5/5 | +300 🍬 |

---

## 11. Earth Day Mini Event

### 11.1 Thông Tin Cơ Bản

| Thuộc Tính | Giá Trị |
|------------|---------|
| Event ID | `earthday_2026` |
| Tên | Ngày Trái Đất |
| Thời gian | 20/04 - 24/04 (5 ngày) |
| Theme | Nature, environment |
| Currency | 💧 Giọt Sương |
| Community Goal | Thu gom 5,000 rác |
| Tree Boost | /gophat x2 XP |
| Color | #228B22 (forest green) |

### 11.2 Milestones

| % | Reward |
|---|--------|
| 50% | +100 seeds |
| 100% | Role "💚 Earth Day 2026" + Background "Thiên Nhiên" |

### 11.3 Event Fish (4 con)

| Key | Tên | Emoji | Tier | 💧 |
|-----|-----|-------|------|-----|
| `ca_la_sen` | Cá Lá Sen | 🪷🐟 | Common | 5 |
| `ca_co_xanh` | Cá Cỏ Xanh | 🌿🐟 | Common | 5 |
| `ca_cau_vong_xanh` | Cá Cầu Vồng Xanh | 🌈🐟 | Rare | 15 |
| `ca_than_rung` | Cá Thần Rừng | 🌲✨ | Epic | 50 |

### 11.4 Cách Tích Lũy Community Goal

| Nguồn | Rác/lần | 💧 Reward |
|-------|---------|-----------|
| Câu cá (có rác) + bấm 🗑️ Vứt Rác | 1-2 | 3/rác |
| Phân Loại Rác đúng | 1/câu đúng | 5/câu |
| Nhặt Rác Biển | 3-5 | 10-25 |
| Câu Event Fish | 1 | 5-50 |

### 11.5 Vứt Rác vs Tái Chế

| Hành Động | Nhận Được |
|-----------|-----------|
| Tái Chế (bình thường) | 10 rác → 1 Phân Bón |
| Vứt Rác (Earth Day) | 1 rác → 3 💧 + 1 vào Goal |

**Lý do vứt rác hấp dẫn hơn:** 💧 Giọt Sương chỉ có 5 ngày!

### 11.6 Minigames

#### 11.6.1 Phân Loại Rác (Scheduled)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Thời gian | 20:00 và 21:00 hàng ngày |
| Channel | `kenh_sukien_auto` |
| Ping | @role_sukien |
| Số câu | Random 5-8 câu |
| UI | Button, Edit message mỗi câu |

**Trigger chuyển câu:**
- Câu 1: Sau 60 giây (thu thập participants)
- Câu 2+: Khi 80% participants đã trả lời HOẶC timeout 2 phút

**3 Loại rác:**
- 🟢 Tái Chế: Chai nhựa, lon nước, giấy báo, hộp carton, chai thủy tinh
- 🟡 Hữu Cơ: Vỏ chuối, cơm thừa, lá cây, xương cá, vỏ trứng
- 🔴 Nguy Hại: Pin, bóng đèn, thuốc hết hạn, sơn, dầu máy

**UI Câu hỏi:**
```
♻️ PHÂN LOẠI RÁC (Câu 3/6)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗑️ Pin điện thoại cũ → thuộc loại nào?

💡 Gợi ý: Có thể gây ô nhiễm đất và nước

👥 Đã trả lời: 8/12 người (67%)
⏰ Tự động chuyển: <t:xxx:R>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[🟢 Tái Chế] [🟡 Hữu Cơ] [🔴 Nguy Hại]
```

**UI Kết quả:**
```
♻️ PHÂN LOẠI RÁC - KẾT THÚC!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 BẢNG XẾP HẠNG:
🥇 @User1 - 6/6 → +30 💧 + 6 rác
🥈 @User2 - 5/6 → +25 💧 + 5 rác
🥉 @User3 - 4/6 → +20 💧 + 4 rác
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 Community Goal: 1,284 / 5,000 rác (+42)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### 11.6.2 Nhặt Rác Biển (Auto Spawn)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Spawn | Random 3-4 lần/ngày |
| Channel | `kenh_sukien_auto` |
| Max người | Top 5 người click nhanh nhất |
| Rác hiển thị | Random từ misc.json |

**UI:**
```
🏖️ RÁC BIỂN XUẤT HIỆN!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bãi biển cần được dọn dẹp! Ai nhanh tay nhất?

🗑️ Rác phát hiện: 🥤 Chai Nhựa, 🛍️ Túi Ni Lông, 🥾 Ủng Rách

⏰ Hết hạn: <t:xxx:R>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[🧹 Nhặt Rác]
```

**Kết quả:**
```
🏖️ DỌN RÁC HOÀN TẤT!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🥇 @User1 → +25 💧 + 🥤 Chai Nhựa
🥈 @User2 → +20 💧 + 🛍️ Túi Ni Lông
🥉 @User3 → +15 💧 + 🥾 Ủng Rách
4. @User4 → +10 💧
5. @User5 → +10 💧
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 Community Goal: 1,287 / 5,000 rác (+3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 11.7 Event Shop

| Tên | Giá | Loại |
|-----|-----|------|
| Background Thiên Nhiên | 300 💧 | Cosmetic |
| Frame Lá Xanh | 200 💧 | Cosmetic |
| Phân Bón Đặc Biệt (x3 XP cây) | 100 💧 | Consumable |
| Badge 💚 | 600 💧 | Badge |

### 11.8 Quests

**Daily:**
| Quest | Target | Reward |
|-------|--------|--------|
| Vứt 10 rác | 10 | +30 💧 |
| Góp cây 50 hạt | 50 | +25 💧 |
| Phân loại đúng 10 câu | 10 | +40 💧 |

**Fixed:**
| Quest | Target | Reward |
|-------|--------|--------|
| Câu Cá Thần Rừng | 1 con | Title "Thần Rừng" |
| Vứt 100 rác | 100 | Badge 💚 |
| Sưu tầm 4 loại cá | 4/4 | +200 💧 |

---

## 12. Mid-Autumn Mini Event

### 12.1 Thông Tin Cơ Bản

| Thuộc Tính | Giá Trị |
|------------|---------|
| Event ID | `midautumn_2026` |
| Tên | Tết Trung Thu |
| Thời gian | 10/09 - 15/09 (6 ngày) |
| Theme | Lanterns, mooncake, family |
| Currency | 🥮 Bánh Trung Thu |
| Community Goal | Thắp 2,000 đèn lồng |
| Color | #FFD700 (gold) |

### 12.2 Milestones

| % | Reward |
|---|--------|
| 50% | +100 seeds |
| 100% | Role "🌙 Trung Thu 2026" + Background "Trăng Rằm" |

### 12.3 Event Fish (4 con)

| Key | Tên | Emoji | Tier | 🥮 |
|-----|-----|-------|------|-----|
| `ca_den_long` | Cá Đèn Lồng | 🏮🐟 | Common | 5 |
| `ca_tho_ngoc` | Cá Thỏ Ngọc | 🐰🐟 | Common | 5 |
| `ca_trang_ram` | Cá Trăng Rằm | 🌕🐟 | Rare | 15 |
| `ca_hang_nga` | Cá Hằng Nga | 👸🐟 | Rare | 15 |

### 12.4 Minigames

#### 12.4.1 Rước Đèn (Voice Bonus)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Thời gian | Tự động khi trong voice |
| Reward | +1 đèn + 5 🥮 mỗi 5 phút |
| Goal | Tích lũy đèn lồng |

#### 12.4.2 Đố Vui Trung Thu (Scheduled)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Thời gian | 20:00 hàng ngày |
| Số câu | 8-10 câu về Trung Thu |
| UI | Tương tự Phân Loại Rác (4 đáp án) |

**Câu hỏi mẫu:**
- Trung Thu diễn ra vào ngày nào âm lịch?
- Bánh Trung Thu truyền thống có hình gì?
- Chú Cuội ngồi gốc cây gì?
- Đèn ông sao có bao nhiêu cánh?

### 12.5 Event Shop

| Tên | Giá | Loại |
|-----|-----|------|
| Background Trăng Rằm | 350 🥮 | Cosmetic |
| Frame Đèn Lồng | 200 🥮 | Cosmetic |
| Đèn Ông Sao | 80 🥮 | Decoration |
| Bánh Dẻo | 50 🥮 | Gift |
| Badge 🌙 | 700 🥮 | Badge |

### 12.6 Quests

**Daily:**
| Quest | Target | Reward |
|-------|--------|--------|
| Thắp 10 đèn (voice 50p) | 50 phút | +40 🥮 |
| Trả lời đúng 5 câu đố | 5 | +30 🥮 |
| Câu 15 cá | 15 | +25 🥮 |

**Fixed:**
| Quest | Target | Reward |
|-------|--------|--------|
| Sưu tầm 4 loại cá | 4/4 | Badge 🌙 |
| Thắp 100 đèn | 100 | Title "Ánh Trăng" |
| Trả lời đúng 30 câu | 30 | +300 🥮 |

---

## 13. Birthday Mini Event

### 13.1 Thông Tin Cơ Bản

| Thuộc Tính | Giá Trị |
|------------|---------|
| Event ID | `birthday_2026` |
| Tên | Sinh Nhật Server |
| Thời gian | TBD (3 ngày) |
| Theme | Celebration |
| Currency | 🎈 Bong Bóng |
| Community Goal | Gửi 500 lời chúc |
| Color | #FF69B4 (hot pink) |

### 13.2 Milestones

| % | Reward |
|---|--------|
| 100% | +200 seeds cho TẤT CẢ + Badge 🎂 |

### 13.3 Event Fish

Không có event fish - tập trung vào celebration.

### 13.4 Minigames

#### 13.4.1 Viết Lời Chúc (Manual)

| Thuộc Tính | Giá Trị |
|------------|---------|
| UI | Modal input |
| Max length | 200 ký tự |
| Reward | +20 🎈 mỗi lời chúc |
| Hiển thị | Bảng lời chúc trong kenh_sukien |
| Limit | 3 lần/ngày |

#### 13.4.2 Bóng Bay (Auto Spawn)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Spawn | Random nhiều lần/ngày |
| Reward | +10-30 🎈 mỗi click |
| Max | Tất cả người react trong 30s |

#### 13.4.3 Birthday Cake (Free Claim)

| Thuộc Tính | Giá Trị |
|------------|---------|
| Command | `/sukien cake` |
| Limit | 1 lần/event |
| Reward | +100 🎈 + Random buff 24h |

### 13.5 Event Shop

| Tên | Giá | Loại |
|-----|-----|------|
| Background Sinh Nhật | 200 🎈 | Cosmetic |
| Frame Bong Bóng | 150 🎈 | Cosmetic |
| Party Hat | 100 🎈 | Cosmetic |
| Confetti | 80 🎈 | Effect |
| Badge 🎂 | 500 🎈 | Badge |

### 13.6 Quests

**Fixed only:**
| Quest | Target | Reward |
|-------|--------|--------|
| Gửi lời chúc | 1 | +50 🎈 |
| Claim cake | 1 | Included |
| Bắt 10 bóng bay | 10 | +40 🎈 |
| Lời chúc được vote top 10 | Voted | Badge 🎂 |

---

## 14. Database Schema

```sql
-- =============================================
-- SEASONAL EVENTS DATABASE SCHEMA
-- =============================================

-- Sự kiện đang active
CREATE TABLE active_events (
    guild_id BIGINT PRIMARY KEY,
    event_id VARCHAR(32),           -- 'spring_2026'
    started_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    community_progress INT DEFAULT 0,
    community_goal INT DEFAULT 0,
    milestones_reached JSONB DEFAULT '[]'  -- ["25", "50"]
);

-- User participation trong event
CREATE TABLE event_participation (
    guild_id BIGINT,
    user_id BIGINT,
    event_id VARCHAR(32),
    currency INT DEFAULT 0,
    contributions INT DEFAULT 0,    -- Đóng góp cho community goal
    PRIMARY KEY (guild_id, user_id, event_id)
);

-- Event quest progress
CREATE TABLE event_quest_progress (
    guild_id BIGINT,
    user_id BIGINT,
    event_id VARCHAR(32),
    quest_id VARCHAR(64),
    quest_type VARCHAR(16),         -- 'daily' | 'fixed'
    current_value INT DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    last_reset TIMESTAMPTZ,         -- For daily quests
    PRIMARY KEY (guild_id, user_id, event_id, quest_id)
);

-- Kỷ Vật - Event fish collection (PERMANENT)
CREATE TABLE event_fish_collection (
    user_id BIGINT,
    fish_key VARCHAR(64),
    event_id VARCHAR(32),           -- Để biết cá từ event nào
    quantity INT DEFAULT 1,
    first_caught_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, fish_key)
);

-- User titles
CREATE TABLE user_titles (
    user_id BIGINT,
    title_key VARCHAR(64),
    title_name VARCHAR(128),
    source VARCHAR(64),             -- 'spring_2026_milestone_50', 'spring_2026_quest_epic_fish'
    unlocked_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, title_key)
);

-- Thêm active_title vào user_profiles
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS active_title VARCHAR(64) DEFAULT NULL;

-- Secret Santa
CREATE TABLE secret_santa (
    guild_id BIGINT,
    event_id VARCHAR(32),
    giver_id BIGINT,
    receiver_id BIGINT,
    gift_item VARCHAR(64),
    gift_message TEXT,
    revealed BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (guild_id, event_id, giver_id)
);

-- Thank letters (Autumn)
CREATE TABLE thank_letters (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    event_id VARCHAR(32),
    sender_id BIGINT,
    receiver_id BIGINT,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Boat race history
CREATE TABLE boat_race_history (
    guild_id BIGINT,
    boat_id VARCHAR(32),
    wins INT DEFAULT 0,
    races INT DEFAULT 0,
    PRIMARY KEY (guild_id, boat_id)
);

-- Boat race predictions streak
CREATE TABLE boat_race_streaks (
    guild_id BIGINT,
    user_id BIGINT,
    current_streak INT DEFAULT 0,
    best_streak INT DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

-- =============================================
-- INDEXES FOR PERFORMANCE
-- =============================================

CREATE INDEX idx_event_participation_event ON event_participation(event_id);
CREATE INDEX idx_event_quest_progress_event ON event_quest_progress(event_id);
CREATE INDEX idx_event_fish_collection_event ON event_fish_collection(event_id);
CREATE INDEX idx_thank_letters_event ON thank_letters(event_id, receiver_id);
CREATE INDEX idx_secret_santa_event ON secret_santa(event_id);
```

---

## 15. Folder Structure & Implementation

### 15.1 Folder Structure

```
cogs/seasonal/
├── __init__.py
├── cog.py                          # Main cog, scheduler, commands
├── test_cog.py                     # Test commands for development
├── core/
│   ├── __init__.py
│   ├── event_manager.py            # Singleton, registry, active event tracking
│   ├── event_types.py              # EventConfig dataclass (JSON-driven)
│   ├── constants.py                # Emoji, colors, limits
│   └── event_fish.py               # Event fish system
├── services/
│   ├── __init__.py
│   ├── currency_service.py         # Add/spend event currency
│   ├── participation_service.py    # Track user participation
│   ├── community_goal_service.py   # Milestone tracking & rewards
│   ├── quest_service.py            # Event quests (JSON-driven)
│   ├── title_service.py            # Title unlock/equip
│   └── shop_service.py             # Event shop purchases
├── ui/
│   ├── __init__.py
│   ├── views.py                    # Persistent views (SecretSanta, buttons)
│   ├── embeds.py                   # Event embeds
│   └── modals.py                   # Thank letter, gift message
├── minigames/
│   ├── __init__.py                 # Auto-discovery, MINIGAME_REGISTRY
│   ├── base.py                     # BaseMinigame + @register_minigame decorator
│   ├── lixi.py                     # Spring: Lì Xì
│   ├── treasure_hunt.py            # Summer: Săn Kho Báu
│   ├── boat_race.py                # Summer: Đua Thuyền
│   ├── thank_letter.py             # Autumn: Thư Cảm Ơn
│   ├── leaf_collect.py             # Autumn: Nhặt Lá
│   ├── tea_brewing.py              # Autumn: Pha Trà
│   ├── secret_santa.py             # Winter: Secret Santa
│   ├── snowman.py                  # Winter: Xây Người Tuyết
│   ├── countdown.py                # Winter: Countdown Năm Mới
│   ├── ghost_hunt.py               # Halloween: Săn Ma
│   ├── trick_treat.py              # Halloween: Trick or Treat
│   ├── trash_sort.py               # Earth Day: Phân Loại Rác
│   ├── beach_cleanup.py            # Earth Day: Nhặt Rác Biển
│   ├── lantern_parade.py           # Mid-Autumn: Rước Đèn
│   ├── quiz.py                     # Mid-Autumn: Đố Vui
│   ├── wishes.py                   # Birthday: Viết Lời Chúc
│   └── balloon_pop.py              # Birthday: Bóng Bay

data/events/
├── registry.json                   # Central event registry (dates, types)
├── spring.json                     # Fish, quests, shop, milestones
├── summer.json
├── autumn.json
├── winter.json
├── halloween.json
├── earthday.json                   # Includes trash sorting Q&A
├── midautumn.json                  # Includes quiz questions
└── birthday.json
```

### 15.2 Implementation Phases

#### Phase 1: Core Framework (4-5 ngày)
- [ ] Folder structure
- [ ] Database tables + migrations
- [ ] EventManager singleton
- [ ] Config: kenh_sukien, kenh_sukien_auto, role_sukien
- [ ] Title service + /danhhieu command
- [ ] Basic /sukien command
- [ ] Scheduler (check start/end, milestone distribution)

#### Phase 2: Quest System (2-3 ngày)
- [ ] Event quest types (daily + fixed)
- [ ] Quest progress tracking
- [ ] Quest reward distribution
- [ ] /sukien nhiemvu command

#### Phase 3: Community Goal (2 ngày)
- [ ] Community progress tracking
- [ ] Milestone detection + reward distribution
- [ ] Goal embed in kenh_sukien
- [ ] Auto-update embed (mỗi 6h hoặc khi đạt milestone)

#### Phase 4: Spring Event (3-4 ngày)
- [ ] Spring JSON config (fish, quests, shop)
- [ ] Event fish integration with fishing module
- [ ] Lì Xì minigames (manual + auto)
- [ ] Shop UI
- [ ] Valentine bonus logic

#### Phase 5: Earth Day (2-3 ngày)
- [ ] Trash Sort minigame (Button + Edit)
- [ ] Beach Cleanup minigame
- [ ] Fishing hook (vứt rác button)
- [ ] earthday.json với 30-50 câu hỏi

#### Phase 6: Summer Event (3-4 ngày)
- [ ] Treasure Hunt minigame
- [ ] Boat Race minigame (full feature)
- [ ] Summer JSON config
- [ ] Boat history tracking

#### Phase 7: Autumn Event (2-3 ngày)
- [ ] Thank Letter system
- [ ] Leaf Collect minigame
- [ ] Tea Brewing minigame
- [ ] Autumn JSON config

#### Phase 8: Winter Event (3-4 ngày)
- [ ] Secret Santa full flow
- [ ] Snowman building
- [ ] NYE Countdown
- [ ] Winter JSON config

#### Phase 9: Mini Events (1-2 ngày mỗi cái)
- [ ] Halloween
- [ ] Mid-Autumn
- [ ] Birthday

#### Phase 10: Polish (2-3 ngày)
- [ ] Announcements (start/end)
- [ ] Leaderboard (/sukien rank)
- [ ] Kỷ Vật collection (/sukien bosuutap)
- [ ] Profile integration (title display)
- [ ] Testing & bug fixes

---

## Appendix A: Summary Table

| Event | Duration | Currency | Fish | Minigames | Community Goal |
|-------|----------|----------|------|-----------|----------------|
| 🌸 Spring | 14d | 🌸 Hoa Đào | 7 | Lì Xì (2) | 50,000 🌸 |
| 🌊 Summer | 21d | 🐚 Vỏ Sò | 7 | Treasure + Boat Race | 100 kho báu |
| 🍂 Autumn | 15d | 🍂 Lá Vàng | 7 | Letter + Leaf + Tea | 500 thư |
| ❄️ Winter | 16d | ❄️ Bông Tuyết | 7 | Santa + Snowman + NYE | 10,000 phần |
| 🎃 Halloween | 7d | 🍬 Kẹo | 5 | Trick/Treat + Ghost | 1,000 ma |
| 💚 Earth Day | 5d | 💧 Giọt Sương | 4 | Trash Sort + Beach | 5,000 rác |
| 🌙 Mid-Autumn | 6d | 🥮 Bánh | 4 | Lantern + Quiz | 2,000 đèn |
| 🎂 Birthday | 3d | 🎈 Bong Bóng | 0 | Wishes + Balloon | 500 chúc |

---

## 16. Extensibility & Data-Driven Design

### 16.1 Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Data over Code** | Event configs, quests, fish, shop items → JSON |
| **Registry Pattern** | Auto-discover minigames, no manual imports |
| **Single Source of Truth** | `registry.json` defines all events |
| **Minimal Code Changes** | Add event = Add JSON files only |

### 16.2 Event Registry (`data/events/registry.json`)

```json
{
  "events": {
    "spring_2026": {
      "name": "Lễ Hội Hoa Xuân",
      "name_en": "Spring Festival",
      "type": "major",
      "start_date": "2026-02-01",
      "end_date": "2026-02-15",
      "currency": {
        "emoji": "🌸",
        "name": "Hoa Đào",
        "name_en": "Cherry Blossom"
      },
      "color": "#FFB7C5",
      "config_file": "spring.json",
      "minigames": ["lixi_auto", "lixi_manual"],
      "community_goal": {
        "type": "currency_collected",
        "target": 50000,
        "description": "Thu thập {target} {currency}"
      }
    },
    "summer_2026": {
      "name": "Lễ Hội Biển",
      "type": "major",
      "start_date": "2026-06-01",
      "end_date": "2026-06-21",
      "currency": {"emoji": "🐚", "name": "Vỏ Sò"},
      "color": "#00CED1",
      "config_file": "summer.json",
      "minigames": ["treasure_hunt", "boat_race"],
      "community_goal": {"type": "treasure_found", "target": 100}
    }
  },
  "auto_start": true,
  "timezone": "Asia/Ho_Chi_Minh"
}
```

### 16.3 Event Config File (e.g., `spring.json`)

```json
{
  "event_id": "spring_2026",
  
  "milestones": [
    {"percent": 25, "reward_type": "seeds", "amount": 100},
    {"percent": 50, "reward_type": "title", "title_key": "xuan_den", "title_name": "Xuân Đến"},
    {"percent": 75, "reward_type": "buff", "buff_type": "fishing_x2", "duration_hours": 24},
    {"percent": 100, "reward_type": "role", "role_name": "🌸 Xuân Đến 2026", "extra": {"type": "background", "key": "bg_spring"}}
  ],
  
  "fish": [
    {"key": "ca_hoa_dao", "name": "Cá Hoa Đào", "emoji": "🌸🐟", "tier": "common", "drop_rate": 0.70, "currency_reward": 5},
    {"key": "ca_rong_vang", "name": "Cá Rồng Vàng", "emoji": "🐉✨", "tier": "epic", "drop_rate": 0.05, "currency_reward": 50}
  ],
  
  "daily_quests": [
    {"id": "spring_fish", "type": "fish_count", "target": 20, "reward": 30, "description": "Câu {target} cá"},
    {"id": "spring_lixi", "type": "lixi_sent", "target": 3, "reward": 50, "description": "Gửi {target} lì xì"},
    {"id": "spring_chat", "type": "message_count", "target": 50, "reward": 20, "description": "Gửi {target} tin nhắn"}
  ],
  
  "fixed_quests": [
    {"id": "spring_epic_fish", "type": "catch_specific_fish", "fish_key": "ca_rong_vang", "target": 1, "reward_type": "title", "reward": "Rồng Vàng"},
    {"id": "spring_all_fish", "type": "collect_all_fish", "target": 7, "reward_type": "badge", "reward": "🌸"}
  ],
  
  "shop": [
    {"key": "bg_spring", "name": "Background Hoa Đào", "price": 500, "type": "cosmetic", "limit": 1},
    {"key": "badge_spring", "name": "Badge 🌸", "price": 1000, "type": "badge", "limit": 1}
  ],
  
  "special_days": {
    "2026-02-14": {
      "name": "Valentine's Day",
      "multipliers": {"lixi_reward": 2, "fish_drop": 1.5}
    }
  }
}
```

### 16.4 Minigame Registry Pattern

```python
# cogs/seasonal/minigames/base.py

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord import Interaction

# Global registry - populated by decorators
MINIGAME_REGISTRY: dict[str, type["BaseMinigame"]] = {}


def register_minigame(name: str):
    """Decorator to register a minigame handler."""
    def decorator(cls: type["BaseMinigame"]) -> type["BaseMinigame"]:
        MINIGAME_REGISTRY[name] = cls
        return cls
    return decorator


class BaseMinigame(ABC):
    """Base class for all minigames."""
    
    def __init__(self, bot, event_manager):
        self.bot = bot
        self.event_manager = event_manager
    
    @abstractmethod
    async def spawn(self, guild_id: int) -> None:
        """Spawn the minigame in the configured channel."""
        pass
    
    @abstractmethod
    async def handle_interaction(self, interaction: "Interaction") -> None:
        """Handle user interaction with the minigame."""
        pass
    
    @property
    @abstractmethod
    def spawn_config(self) -> dict:
        """Return spawn configuration (times_per_day, scheduled_times, etc.)"""
        pass


# Usage in lixi.py:
from .base import BaseMinigame, register_minigame

@register_minigame("lixi_auto")
class LixiAutoMinigame(BaseMinigame):
    
    @property
    def spawn_config(self) -> dict:
        return {
            "type": "random",
            "times_per_day": (3, 5),  # 3-5 times per day
            "active_hours": (8, 23),   # 8 AM - 11 PM
        }
    
    async def spawn(self, guild_id: int) -> None:
        # Implementation...
        pass
    
    async def handle_interaction(self, interaction) -> None:
        # Implementation...
        pass
```

### 16.5 Quest Type Handlers (JSON-Driven)

```python
# cogs/seasonal/services/quest_service.py

from typing import Callable, Awaitable

# Quest type handlers - maps quest type to progress checker
QUEST_HANDLERS: dict[str, Callable[..., Awaitable[int]]] = {}


def quest_handler(quest_type: str):
    """Decorator to register quest type handlers."""
    def decorator(func):
        QUEST_HANDLERS[quest_type] = func
        return func
    return decorator


@quest_handler("fish_count")
async def handle_fish_count(user_id: int, event_id: str, **kwargs) -> int:
    """Return current fish count for user in this event."""
    # Query from database
    pass


@quest_handler("lixi_sent")
async def handle_lixi_sent(user_id: int, event_id: str, **kwargs) -> int:
    """Return number of lixi sent today."""
    pass


@quest_handler("catch_specific_fish")
async def handle_catch_specific_fish(user_id: int, event_id: str, fish_key: str, **kwargs) -> int:
    """Check if user caught specific fish."""
    pass
```

### 16.6 Adding a New Event (Checklist)

| Step | Action | File(s) to Modify |
|------|--------|-------------------|
| 1 | Add event entry | `data/events/registry.json` |
| 2 | Create config file | `data/events/<event>.json` |
| 3 | (Optional) Add new minigame | `cogs/seasonal/minigames/<name>.py` with `@register_minigame` |
| 4 | (Optional) Add new quest type | `cogs/seasonal/services/quest_service.py` with `@quest_handler` |
| 5 | Restart bot | No code changes needed for steps 1-2 |

### 16.7 Extensibility Score

| Action | Before (v1.0) | After (v2.0) |
|--------|---------------|--------------|
| Add new event | Code + JSON | JSON only ✅ |
| Add new quest type | Code change | Code + decorator ✅ |
| Add new minigame | Code + imports | Code + decorator ✅ |
| Change event dates | Code change | JSON only ✅ |
| Add shop items | JSON | JSON ✅ |
| Add fish | JSON | JSON ✅ |
| Change milestones | JSON | JSON ✅ |

---

## 17. Testing Strategy

### 17.1 Test Commands

```
/sukien-test start <event_id>      # Force start any event (bypass date check)
/sukien-test end                    # Force end current event
/sukien-test currency <amount>      # Add currency to self
/sukien-test goal <amount>          # Add to community goal
/sukien-test milestone <percent>    # Trigger milestone manually
/sukien-test quest <quest_id>       # Complete a quest instantly
/sukien-test fish <fish_key>        # Add fish to collection
/sukien-test title <title_key>      # Unlock a title
/sukien-test minigame <name>        # Spawn a minigame now
/sukien-test reset                  # Reset all event data for guild
```

### 17.2 Test Scenarios

#### Scenario 1: Event Lifecycle
```
1. /sukien-test start spring_2026
2. Verify announcement in kenh_sukien
3. Verify /sukien shows event info
4. /sukien-test end
5. Verify end announcement
6. Verify currency preserved but event inactive
```

#### Scenario 2: Currency & Participation
```
1. Start event
2. /sukien-test currency 100
3. Verify /sukien shows 100 currency
4. Verify user in participation table
5. Test spending in shop
```

#### Scenario 3: Community Goal & Milestones
```
1. Start event with goal 1000
2. /sukien-test goal 250 → Verify 25% milestone triggered
3. Check all participants got +100 seeds
4. /sukien-test goal 500 → Verify 50% milestone (title unlocked)
5. /sukien-test goal 1000 → Verify 100% (role created)
```

#### Scenario 4: Quest System
```
1. /sukien nhiemvu → See daily + fixed quests
2. Complete quest action (e.g., fish 20 times)
3. Verify progress updates
4. Verify reward given on completion
5. Verify daily quest resets at midnight
```

#### Scenario 5: Minigame Spawn
```
1. /sukien-test minigame lixi_auto
2. Verify embed appears in kenh_sukien_auto
3. Click button → Verify reward
4. Verify currency added
5. Verify goal contribution (if applicable)
```

### 17.3 Integration Tests

| Test | Components | Expected Result |
|------|------------|-----------------|
| Fishing + Event Fish | Fishing cog + Seasonal | 15% chance event fish during event |
| Profile + Title | Profile cog + Title service | Title shows in /hoso |
| Tree + Earth Day | Tree cog + Seasonal | /gophat gives 2x XP during event |
| Config + Channels | Config cog + Seasonal | Event uses configured channels |

### 17.4 Test Data Isolation

```python
# Test guild ID for isolation
TEST_GUILD_ID = 123456789

# Test commands only work for:
# 1. Bot owner
# 2. Users with Administrator permission
# 3. In TEST_GUILD_ID (configurable)
```

---

## Appendix A: Summary Table

| Event | Duration | Currency | Fish | Minigames | Community Goal |
|-------|----------|----------|------|-----------|----------------|
| 🌸 Spring | 14d | 🌸 Hoa Đào | 7 | Lì Xì (2) | 50,000 🌸 |
| 🌊 Summer | 21d | 🐚 Vỏ Sò | 7 | Treasure + Boat Race | 100 kho báu |
| 🍂 Autumn | 15d | 🍂 Lá Vàng | 7 | Letter + Leaf + Tea | 500 thư |
| ❄️ Winter | 16d | ❄️ Bông Tuyết | 7 | Santa + Snowman + NYE | 10,000 phần |
| 🎃 Halloween | 7d | 🍬 Kẹo | 5 | Trick/Treat + Ghost | 1,000 ma |
| 💚 Earth Day | 5d | 💧 Giọt Sương | 4 | Trash Sort + Beach | 5,000 rác |
| 🌙 Mid-Autumn | 6d | 🥮 Bánh | 4 | Lantern + Quiz | 2,000 đèn |
| 🎂 Birthday | 3d | 🎈 Bong Bóng | 0 | Wishes + Balloon | 500 chúc |

---

**Document End**

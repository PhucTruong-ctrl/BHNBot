# Hướng Dẫn Test Seasonal Events - Complete Guide

> **Phiên bản:** 2.0  
> **Cập nhật:** Tháng 1/2026  
> **Bao gồm:** 8 sự kiện, 15 minigames, shop, quests, titles, fish collection

---

## Mục Lục

1. [Chuẩn Bị Môi Trường](#1-chuẩn-bị-môi-trường)
2. [Test Khởi Động Sự Kiện](#2-test-khởi-động-sự-kiện)
3. [Test Tiền Tệ Sự Kiện](#3-test-tiền-tệ-sự-kiện)
4. [Test Hệ Thống Nhiệm Vụ](#4-test-hệ-thống-nhiệm-vụ)
5. [Test Mục Tiêu Cộng Đồng](#5-test-mục-tiêu-cộng-đồng)
6. [Test Cửa Hàng Sự Kiện](#6-test-cửa-hàng-sự-kiện)
7. [Test Hệ Thống Danh Hiệu](#7-test-hệ-thống-danh-hiệu)
8. [Test Bộ Sưu Tập Cá](#8-test-bộ-sưu-tập-cá)
9. [Test Tích Hợp Profile](#9-test-tích-hợp-profile)
10. [Test Minigames - Spring](#10-test-minigames---spring)
11. [Test Minigames - Summer](#11-test-minigames---summer)
12. [Test Minigames - Autumn](#12-test-minigames---autumn)
13. [Test Minigames - Winter](#13-test-minigames---winter)
14. [Test Minigames - Halloween](#14-test-minigames---halloween)
15. [Test Minigames - Earth Day](#15-test-minigames---earth-day)
16. [Test Minigames - Mid-Autumn](#16-test-minigames---mid-autumn)
17. [Test Minigames - Birthday](#17-test-minigames---birthday)
18. [Test Kết Thúc Sự Kiện](#18-test-kết-thúc-sự-kiện)
19. [Test Bảng Xếp Hạng](#19-test-bảng-xếp-hạng)
20. [Danh Sách Sự Kiện Chi Tiết](#20-danh-sách-sự-kiện-chi-tiết)
21. [Checklist Tổng Hợp](#21-checklist-tổng-hợp)

---

## 1. Chuẩn Bị Môi Trường

### 1.1. Kiểm tra Database Tables

Bot tự tạo các bảng khi khởi động. Kiểm tra log có:
```
✓ Seasonal event tables initialized
```

**Bảng cần có (16 bảng):**
```sql
-- Core tables
active_events
event_participation
event_quest_progress
event_fish_collection
event_shop_purchases
event_quests
user_titles
user_active_title

-- Minigame tables
ghost_hunt_daily
trick_treat_daily
snowman_contributions
lantern_parade
lantern_voice_time
birthday_wishes
treasure_hunt_daily
beach_cleanup_daily
quiz_scores
countdown_participants
balloon_pop_daily
thank_letters
secret_santa_sessions
secret_santa_participants
boat_race_history
boat_race_streaks
```

### 1.2. Kiểm tra Event JSON Files

```bash
ls data/events/
```

**Files cần có (9 files):**
- `registry.json` - Đăng ký tất cả sự kiện
- `spring.json` - Lễ Hội Hoa Xuân
- `summer.json` - Lễ Hội Biển
- `autumn.json` - Thu Hoạch Mùa Thu
- `winter.json` - Đông Ấm Áp
- `halloween.json` - Halloween Vui Vẻ
- `earthday.json` - Ngày Trái Đất
- `midautumn.json` - Tết Trung Thu
- `birthday.json` - Sinh Nhật Server

### 1.3. Cấu hình kênh (Admin)

```
/config set kenh_sukien:#thông-báo-sự-kiện
/config set kenh_sukien_auto:#minigame-sự-kiện
/config set role_sukien:@Sự Kiện
```

**Kỳ vọng:**
- ✅ Lệnh thành công
- ✅ Kênh được lưu vào database

---

## 2. Test Khởi Động Sự Kiện

### 2.1. Bắt đầu sự kiện (Admin)

**Bước 1:** Chạy lệnh
```
/sukien-test start event_id:spring_2026
```

**Bước 2:** Kiểm tra kênh `kenh_sukien`

**Kỳ vọng:**
- ✅ Embed thông báo sự kiện được gửi
- ✅ Tiêu đề: "🌸 Lễ Hội Hoa Xuân 2026"
- ✅ Hiển thị thời gian: ngày bắt đầu - kết thúc
- ✅ Hiển thị tiền tệ: "🌸 Hoa Đào"
- ✅ Hiển thị mục tiêu cộng đồng với target
- ✅ Hiển thị các mốc thưởng (25%, 50%, 75%, 100%)
- ✅ Hiển thị danh sách cá sự kiện (7 loại)
- ✅ Hiển thị minigames có sẵn
- ✅ Banner image (nếu có URL trong config)
- ✅ Ping role @Sự Kiện

### 2.2. Xem thông tin sự kiện (User)

**Bước 1:** Chạy lệnh
```
/sukien
```

**Kỳ vọng:**
- ✅ Embed hiển thị tên sự kiện
- ✅ Số tiền tệ của user = 0 (mới tham gia)
- ✅ Progress bar mục tiêu cộng đồng
- ✅ Thời gian còn lại
- ✅ Hướng dẫn sử dụng các lệnh

### 2.3. Test Tabs (EventInfoView)

**Bước 1:** Sau khi dùng `/sukien`, bấm các tab

| Tab | Kỳ Vọng |
|-----|---------|
| 📋 Thông Tin | Hiển thị thông tin sự kiện |
| 🎯 Mục Tiêu | Hiển thị mục tiêu cộng đồng + progress |
| 🏆 Xếp Hạng | Hiển thị top 10 người chơi |

---

## 3. Test Tiền Tệ Sự Kiện

### 3.1. Thêm tiền tệ (Admin)

**Bước 1:**
```
/sukien-test currency action:add amount:500
```

**Kỳ vọng:**
- ✅ Thông báo: "Đã thêm 500 🌸"
- ✅ Số dư mới = 500

**Bước 2:** Kiểm tra số dư
```
/sukien
```

**Kỳ vọng:**
- ✅ Hiển thị: "Số dư: 500 🌸"

### 3.2. Trừ tiền tệ

**Bước 1:**
```
/sukien-test currency action:spend amount:100
```

**Kỳ vọng:**
- ✅ Thông báo: "Đã trừ 100 🌸"
- ✅ Số dư mới = 400

### 3.3. Trừ quá số dư

**Bước 1:**
```
/sukien-test currency action:spend amount:9999
```

**Kỳ vọng:**
- ✅ Lỗi: "Không đủ tiền"
- ✅ Số dư giữ nguyên

### 3.4. Kiểm tra số dư

**Bước 1:**
```
/sukien-test currency action:check
```

**Kỳ vọng:**
- ✅ Hiển thị số dư chính xác

---

## 4. Test Hệ Thống Nhiệm Vụ

### 4.1. Xem nhiệm vụ

**Bước 1:**
```
/sukien nhiemvu
```

**Kỳ vọng:**
- ✅ Tab "Hàng Ngày" mặc định được chọn
- ✅ Hiển thị 3 nhiệm vụ ngẫu nhiên (từ 6 loại)
- ✅ Mỗi nhiệm vụ có: tên, mô tả, tiến độ (0/X), phần thưởng

### 4.2. Chuyển tab nhiệm vụ

**Bước 1:** Bấm tab "🏆 Thành Tựu"

**Kỳ vọng:**
- ✅ Hiển thị nhiệm vụ cố định (achievement)
- ✅ Nhiệm vụ có target lớn hơn (collect 100 fish, etc.)

### 4.3. Cập nhật tiến độ nhiệm vụ (Admin test)

**Bước 1:**
```
/sukien-test quest type:catch_fish progress:5
```

**Kỳ vọng:**
- ✅ Tiến độ nhiệm vụ "Câu X cá" tăng 5

**Bước 2:** Xem lại nhiệm vụ
```
/sukien nhiemvu
```

**Kỳ vọng:**
- ✅ Tiến độ hiển thị: 5/X

### 4.4. Hoàn thành nhiệm vụ

**Bước 1:** Đẩy tiến độ đến target
```
/sukien-test quest type:catch_fish progress:100
```

**Bước 2:** Xem nhiệm vụ

**Kỳ vọng:**
- ✅ Nút "✅ Nhận" xuất hiện (trước đó là disabled)
- ✅ Trạng thái: "Hoàn thành"

### 4.5. Nhận thưởng nhiệm vụ

**Bước 1:** Bấm nút "✅ Nhận"

**Kỳ vọng:**
- ✅ Thông báo ephemeral: "Nhận thành công +50 🌸"
- ✅ Số dư tăng lên
- ✅ Nút chuyển thành "✓ Đã nhận" (disabled)
- ✅ Không thể bấm lần 2

### 4.6. Reset nhiệm vụ hàng ngày

Nhiệm vụ hàng ngày reset lúc 00:00 UTC.

**Test:**
- Đợi qua ngày mới hoặc thay đổi ngày hệ thống
- Chạy `/sukien nhiemvu`

**Kỳ vọng:**
- ✅ Nhiệm vụ mới được gán (có thể khác hôm trước)
- ✅ Tiến độ reset về 0

---

## 5. Test Mục Tiêu Cộng Đồng

### 5.1. Xem mục tiêu

**Bước 1:**
```
/sukien muctieu
```

**Kỳ vọng:**
- ✅ Hiển thị mô tả mục tiêu (ví dụ: "Thu thập 50,000 🌸 Hoa Đào")
- ✅ Progress bar: 0% (ban đầu)
- ✅ Danh sách 4 mốc: 25%, 50%, 75%, 100%
- ✅ Mỗi mốc có: phần thưởng, trạng thái (⏳ Chưa đạt)

### 5.2. Cập nhật tiến độ (Admin)

**Bước 1:** Thêm tiến độ
```
/sukien-test goal progress:10000
```

**Kỳ vọng:**
- ✅ Thông báo: "Đã thêm 10,000 tiến độ"

**Bước 2:** Xem lại mục tiêu

**Kỳ vọng:**
- ✅ Progress bar: 20% (10000/50000)

### 5.3. Đạt mốc 25%

**Bước 1:**
```
/sukien-test goal progress:2500
```
(Tổng = 12,500 = 25%)

**Kỳ vọng:**
- ✅ Thông báo đạt mốc 25% gửi vào `kenh_sukien`
- ✅ Tất cả người tham gia nhận bonus (currency hoặc item)
- ✅ Mốc 25% chuyển thành "✅ Đã đạt"

### 5.4. Đạt mốc 50%, 75%, 100%

Lặp lại bước 5.3 với các mốc:
- 50%: 25,000
- 75%: 37,500
- 100%: 50,000

**Kỳ vọng mốc 75%:**
- ✅ Unlock danh hiệu cho tất cả người chơi

**Kỳ vọng mốc 100%:**
- ✅ Thông báo HOÀN THÀNH mục tiêu
- ✅ Bonus đặc biệt cho tất cả

### 5.5. Top đóng góp cộng đồng

**Bước 1:** Xem bảng xếp hạng đóng góp
```
/sukien xephang
```

**Kỳ vọng:**
- ✅ Hiển thị top 10 người đóng góp nhiều nhất

---

## 6. Test Cửa Hàng Sự Kiện

### 6.1. Xem cửa hàng

**Bước 1:**
```
/sukien cuahang
```

**Kỳ vọng:**
- ✅ Hiển thị số dư hiện tại
- ✅ Danh sách vật phẩm (5 items trong spring)
- ✅ Mỗi item có: emoji, tên, giá, mô tả
- ✅ Nút "Mua" cho từng item
- ✅ Phân trang nếu > 5 items

### 6.2. Mua vật phẩm đủ tiền

**Chuẩn bị:** Đảm bảo có đủ tiền
```
/sukien-test currency action:add amount:1000
```

**Bước 1:** Bấm nút "Mua" cho item 500 🌸

**Kỳ vọng:**
- ✅ Thông báo ephemeral: "Đã mua thành công **Cành Đào Trang Trí**!"
- ✅ Số dư giảm 500
- ✅ Embed cập nhật số dư mới

### 6.3. Mua vật phẩm không đủ tiền

**Bước 1:** Bấm "Mua" item đắt hơn số dư

**Kỳ vọng:**
- ✅ Thông báo lỗi: "Không đủ tiền! Cần X nhưng chỉ có Y"
- ✅ Số dư không đổi

### 6.4. Mua vật phẩm giới hạn số lượng

Một số item có `limit_per_user`.

**Bước 1:** Mua item có limit = 1

**Bước 2:** Mua lại item đó

**Kỳ vọng:**
- ✅ Lỗi: "Bạn chỉ có thể mua tối đa 1 vật phẩm này"

### 6.5. Mua vật phẩm hết hàng

Một số item có `stock` giới hạn toàn server.

**Kỳ vọng khi hết:**
- ✅ Hiển thị "Hết hàng"
- ✅ Nút mua bị disable

### 6.6. Xem lịch sử mua hàng

**Bước 1:** (Nếu có lệnh)
```
/sukien lichsu
```

**Kỳ vọng:**
- ✅ Hiển thị các item đã mua

---

## 7. Test Hệ Thống Danh Hiệu

### 7.1. Xem danh hiệu đã mở khóa

**Bước 1:**
```
/danhhieu xem
```

**Kỳ vọng (chưa có danh hiệu):**
- ✅ Thông báo: "Bạn chưa mở khóa danh hiệu nào!"

### 7.2. Mở khóa danh hiệu qua milestone

**Bước 1:** Đạt mốc 75% (xem phần 5.4)

**Bước 2:**
```
/danhhieu xem
```

**Kỳ vọng:**
- ✅ Hiển thị danh hiệu "Người Hái Hoa"
- ✅ Nguồn: từ sự kiện spring_2026

### 7.3. Đặt danh hiệu

**Bước 1:**
```
/danhhieu set title:Người Hái Hoa
```

**Kỳ vọng:**
- ✅ Thông báo: "Đã đặt danh hiệu: **Người Hái Hoa**"

### 7.4. Xem danh hiệu đang dùng

**Bước 1:**
```
/danhhieu xem
```

**Kỳ vọng:**
- ✅ Danh hiệu đang dùng có icon 👑

### 7.5. Bỏ danh hiệu

**Bước 1:**
```
/danhhieu set
```
(không nhập title)

**Kỳ vọng:**
- ✅ Thông báo: "Đã bỏ danh hiệu"

### 7.6. Đặt danh hiệu chưa mở khóa

**Bước 1:**
```
/danhhieu set title:Vua Mùa Xuân
```
(chưa đạt mốc 100%)

**Kỳ vọng:**
- ✅ Lỗi: "Bạn chưa mở khóa danh hiệu **Vua Mùa Xuân**!"

---

## 8. Test Bộ Sưu Tập Cá

### 8.1. Xem bộ sưu tập (chưa có cá)

**Bước 1:**
```
/sukien bosuutap
```

**Kỳ vọng:**
- ✅ Hiển thị danh sách 7 loại cá sự kiện
- ✅ Tất cả hiển thị: "❓ ??? x0"
- ✅ Tiến độ: "0/7 loại cá"

### 8.2. Câu cá sự kiện (mô phỏng)

**Bước 1:** Thêm cá vào collection (Admin test)
```
/sukien-test fish key:ca_dao amount:1
```

**Bước 2:** Xem lại bộ sưu tập

**Kỳ vọng:**
- ✅ Cá "Cá Đào" hiển thị: "✅ 🐡 **Cá Đào** (⭐) x1"
- ✅ Tiến độ: "1/7 loại cá"

### 8.3. Câu cá qua fishing hook (integration)

**Bước 1:** Đi câu cá bình thường
```
/cauca
```

**Kỳ vọng (15% cơ hội):**
- ✅ Có thể nhận được cá sự kiện
- ✅ Thông báo: "🎉 Bạn câu được cá sự kiện: **Cá Đào**! +10 🌸"
- ✅ Cá được thêm vào bộ sưu tập

### 8.4. Câu cá mới vs cá đã có

**Cá mới:**
- ✅ Thông báo: "🆕 Cá mới trong bộ sưu tập!"

**Cá đã có:**
- ✅ Chỉ tăng số lượng, không có thông báo "mới"

---

## 9. Test Tích Hợp Profile

### 9.1. Profile không có danh hiệu

**Bước 1:**
```
/hoso
```

**Kỳ vọng:**
- ✅ Profile hiển thị bình thường
- ✅ Không có danh hiệu

### 9.2. Profile có danh hiệu

**Chuẩn bị:** Đặt danh hiệu (xem phần 7.3)

**Bước 1:**
```
/hoso
```

**Kỳ vọng:**
- ✅ Hiển thị danh hiệu: "🏅 **Người Hái Hoa**"
- ✅ Danh hiệu xuất hiện trong caption hoặc embed title

### 9.3. Xem profile người khác có danh hiệu

**Bước 1:**
```
/hoso user:@NgườiCóDanhHiệu
```

**Kỳ vọng:**
- ✅ Hiển thị danh hiệu của người đó

---

## 10. Test Minigames - Spring

### 10.1. Lì Xì Tự Động (lixi_auto)

**Trigger (Admin):**
```
/sukien-test minigame type:lixi_auto
```

**Kỳ vọng spawn:**
- ✅ Embed Lì Xì xuất hiện trong `kenh_sukien_auto`
- ✅ Hiển thị: "🧧 Lì Xì May Mắn!"
- ✅ Nút: "🧧 Nhận Lì Xì"
- ✅ Hiển thị: "0/10 người đã nhận"
- ✅ Hiển thị: "Hết hạn sau 60 giây"

**User nhận Lì Xì:**

**Bước 1:** Bấm nút "🧧 Nhận Lì Xì"

**Kỳ vọng:**
- ✅ Thông báo ephemeral: "Bạn nhận được 25 🌸!"
- ✅ Số dư tăng lên
- ✅ Embed cập nhật: "1/10 người đã nhận"

**Bước 2:** Bấm lại nút

**Kỳ vọng:**
- ✅ Lỗi: "Bạn đã nhận lì xì này rồi!"

**Hết lượt (10 người):**
- ✅ Embed chuyển: "🎊 Lì Xì đã hết!"
- ✅ Nút bị disable
- ✅ Hiển thị danh sách người nhận

**Hết thời gian (60s):**
- ✅ Embed chuyển: "⏰ Lì Xì đã hết hạn!"
- ✅ Nút bị disable

### 10.2. Lì Xì Tặng Bạn (lixi_manual)

**Chuẩn bị:** User có ít nhất 100 🌸

**Bước 1:** Tạo lì xì
```
/lixi tao so_tien:100 so_phan:5 loi_chuc:Chúc mừng năm mới!
```

**Kỳ vọng:**
- ✅ Trừ 100 🌸 từ người tạo
- ✅ Embed hiển thị trong kênh hiện tại
- ✅ Hiển thị: người gửi, tổng tiền, số phần, lời chúc
- ✅ Thời gian: 5 phút

**User khác nhận:**

**Bước 1:** User khác bấm "🧧 Nhận"

**Kỳ vọng:**
- ✅ Nhận ngẫu nhiên (tổng / số phần ~ 20)
- ✅ Người tạo KHÔNG thể tự nhận

**Hết phần:**
- ✅ Embed hiển thị danh sách: Ai nhận bao nhiêu

**Hết thời gian còn phần:**
- ✅ Hoàn tiền còn lại cho người tạo

---

## 11. Test Minigames - Summer

### 11.1. Săn Kho Báu (treasure_hunt)

**Trigger (Admin):**
```
/sukien-test minigame type:treasure_hunt
```

**Kỳ vọng spawn:**
- ✅ Embed hiển thị bản đồ 3x3 (9 ô)
- ✅ 9 nút (1-9 hoặc A1-C3)
- ✅ Tiêu đề: "🗺️ Săn Kho Báu"
- ✅ Thời gian: 30 giây

**User đào:**

**Bước 1:** Bấm 1 ô

**Kỳ vọng (random):**
- ✅ **Kho báu:** "🎉 Bạn tìm thấy kho báu! +50 🐚" + cộng tiến độ cộng đồng
- ✅ **Trống:** "💨 Ô này trống!"
- ✅ **Bẫy:** "💥 Bạn gặp bẫy! -10 🐚"

**Bước 2:** Bấm ô khác

**Kỳ vọng:**
- ✅ Mỗi người chỉ được đào 1 lần mỗi hunt

**Hết thời gian:**
- ✅ Embed kết thúc, hiển thị ai tìm được kho báu

### 11.2. Đua Thuyền (boat_race)

**Trigger (Admin):**
```
/sukien-test minigame type:boat_race
```

**Kỳ vọng đăng ký:**
- ✅ Embed: "🚤 Đua Thuyền - Đăng Ký"
- ✅ 4 nút thuyền: 🚤 🛶 ⛵ 🚢
- ✅ Thời gian đăng ký: 30 giây

**User chọn thuyền:**

**Bước 1:** Bấm 1 thuyền

**Kỳ vọng:**
- ✅ Thông báo: "Bạn đã chọn thuyền 🚤!"
- ✅ Embed cập nhật số người mỗi thuyền

**Bước 2:** Đổi thuyền

**Kỳ vọng:**
- ✅ Cho phép đổi trong thời gian đăng ký

**Hết thời gian đăng ký:**
- ✅ Animation đua (text update)
- ✅ Kết quả: Thuyền X thắng!
- ✅ Người chọn thuyền thắng: +30 🐚
- ✅ Chuỗi thắng liên tiếp: bonus thêm

---

## 12. Test Minigames - Autumn

### 12.1. Thư Cảm Ơn (thank_letter)

**Bước 1:**
```
/sukien camonsend user:@NgườiNhận
```

**Kỳ vọng:**
- ✅ Modal xuất hiện: "Gửi Thư Cảm Ơn"
- ✅ TextInput: "Lời cảm ơn của bạn" (10-500 ký tự)

**Bước 2:** Nhập lời cảm ơn và gửi

**Kỳ vọng:**
- ✅ Thông báo: "Đã gửi thư cảm ơn đến @NgườiNhận!"
- ✅ Người gửi: +20 🍂
- ✅ Người nhận: +10 🍂
- ✅ Tiến độ cộng đồng +1

**Giới hạn hàng ngày:**
- ✅ Tối đa 3 thư/ngày/người

### 12.2. Nhặt Lá (leaf_collect)

**Trigger (Admin):**
```
/sukien-test minigame type:leaf_collect
```

**Kỳ vọng:**
- ✅ Spawn lá rơi trong kênh
- ✅ Nút "🍂 Nhặt Lá"
- ✅ Số lượng lá giới hạn (10 lá/spawn)

**User nhặt:**
- ✅ +5 🍂 mỗi lá
- ✅ First come first served

### 12.3. Pha Trà (tea_brewing)

**Bước 1:**
```
/sukien phatra
```

**Kỳ vọng:**
- ✅ Minigame pha trà bắt đầu
- ✅ Các bước: Chọn lá trà → Đun nước → Pha → Đợi
- ✅ Thời gian mỗi bước

**Hoàn thành:**
- ✅ +50 🍂
- ✅ Cooldown 4 giờ

**Pha lại trong cooldown:**
- ✅ Lỗi: "Bạn cần đợi X giờ nữa!"

---

## 13. Test Minigames - Winter

### 13.1. Secret Santa (secret_santa)

**Phase 1: Đăng ký**

**Bước 1:**
```
/sukien secretsanta dangky
```

**Kỳ vọng:**
- ✅ Đăng ký thành công
- ✅ Xác nhận tham gia

**Phase 2: Ghép cặp (Admin)**

```
/sukien-test minigame type:secret_santa action:pair
```

**Kỳ vọng:**
- ✅ Mỗi người được gán 1 người nhận quà ngẫu nhiên
- ✅ DM thông báo: "Bạn sẽ tặng quà cho @NgườiNhận"

**Phase 3: Gửi quà**

**Bước 1:**
```
/sukien secretsanta tangqua
```

**Kỳ vọng:**
- ✅ Modal: "Lời nhắn tặng quà"
- ✅ TextInput: 5-300 ký tự

**Bước 2:** Gửi lời nhắn

**Kỳ vọng:**
- ✅ Quà được đánh dấu đã gửi
- ✅ +50 ❄️ cho người gửi

**Phase 4: Mở quà (ngày cuối)**

```
/sukien-test minigame type:secret_santa action:reveal
```

**Kỳ vọng:**
- ✅ Tất cả được công bố: Ai tặng ai
- ✅ Người nhận quà: +30 ❄️

### 13.2. Người Tuyết (snowman)

**Tự động spawn:**
- ✅ Thông báo: "☃️ Hãy cùng xây người tuyết!"
- ✅ Nút: "❄️ Góp Tuyết"

**User góp:**

**Bước 1:** Bấm "❄️ Góp Tuyết"

**Kỳ vọng:**
- ✅ +1 phần tuyết vào người tuyết
- ✅ +5 ❄️ cho user
- ✅ Tiến độ cộng đồng +1

**Giới hạn:**
- ✅ Tối đa 20 phần/ngày/người

**Hoàn thành người tuyết (100 phần):**
- ✅ Thông báo: "☃️ Người tuyết hoàn thành!"
- ✅ Bonus cho tất cả người đóng góp

**Lệnh thủ công:**
```
/sukien goptuyet
```

### 13.3. Đếm Ngược (countdown)

**Tự động vào 23:59 ngày 31/12:**
- ✅ Thông báo đếm ngược: "10... 9... 8..."
- ✅ Confetti animation

**00:00 ngày 01/01:**
- ✅ "🎉 CHÚC MỪNG NĂM MỚI!"
- ✅ Tất cả người online: +100 ❄️

---

## 14. Test Minigames - Halloween

### 14.1. Săn Ma (ghost_hunt)

**Trigger (Admin):**
```
/sukien-test minigame type:ghost_hunt
```

**Kỳ vọng spawn:**
- ✅ Embed: "👻 Con ma xuất hiện!"
- ✅ Nút: "👻 Bắt Ma"
- ✅ Thời gian: 45 giây
- ✅ Số lượng: 3 lượt bắt

**User bắt:**

**Bước 1:** Bấm "👻 Bắt Ma"

**Kỳ vọng:**
- ✅ +15 🍬
- ✅ Tiến độ cộng đồng +1
- ✅ Lượt còn lại giảm

**Giới hạn:**
- ✅ Tối đa 10 ma/ngày/người

**Đủ giới hạn:**
- ✅ Lỗi: "Bạn đã bắt đủ 10 ma hôm nay!"

### 14.2. Trick or Treat (trick_treat)

**Bước 1:**
```
/sukien tricktreat user:@NgườiKhác
```

**Kỳ vọng (random 70% treat, 30% trick):**

**Treat:**
- ✅ Người gõ cửa: +20 🍬
- ✅ Người mở cửa: +10 🍬

**Trick:**
- ✅ Người gõ cửa: -5 🍬
- ✅ Người mở cửa: +5 🍬

**Cooldown:**
- ✅ 5 phút giữa mỗi lần với cùng 1 người
- ✅ Tối đa 5 người/ngày

---

## 15. Test Minigames - Earth Day

### 15.1. Phân Loại Rác (trash_sort)

**Trigger (Admin):**
```
/sukien-test minigame type:trash_sort
```

**Kỳ vọng:**
- ✅ Hiển thị rác ngẫu nhiên (ví dụ: "🍌 Vỏ chuối")
- ✅ 3 nút: "♻️ Tái chế", "🗑️ Rác thường", "☣️ Rác nguy hại"

**User phân loại đúng:**
- ✅ +10 💧
- ✅ Câu hỏi tiếp theo

**User phân loại sai:**
- ✅ +0 💧
- ✅ Giải thích: "Vỏ chuối là rác hữu cơ, nên bỏ vào..."

**Hoàn thành 10 câu:**
- ✅ Điểm tổng kết
- ✅ Bonus nếu đúng > 8/10

### 15.2. Dọn Bãi Biển (beach_cleanup)

**Trigger (Admin):**
```
/sukien-test minigame type:beach_cleanup
```

**Kỳ vọng:**
- ✅ Spawn rác trên bãi biển
- ✅ Nút: "🧹 Nhặt Rác"
- ✅ Số lượng rác giới hạn

**User nhặt:**
- ✅ +5 💧 mỗi rác
- ✅ Tiến độ cộng đồng +1

---

## 16. Test Minigames - Mid-Autumn

### 16.1. Rước Đèn (lantern_parade)

**Tự động tracking voice:**

**Bước 1:** User vào voice channel

**Kỳ vọng:**
- ✅ Mỗi 5 phút voice: +5 🥮, +1 đèn
- ✅ Tối đa 60 phút/ngày = 12 đèn

**Bước 2:** Xem đèn lồng
```
/sukien denlong
```

**Kỳ vọng:**
- ✅ Hiển thị số đèn đã thắp
- ✅ Tiến độ cộng đồng = tổng đèn

### 16.2. Đố Vui (quiz)

**Trigger (Admin):**
```
/sukien-test minigame type:quiz
```

**Kỳ vọng:**
- ✅ Câu hỏi về Trung Thu (lịch sử, truyền thống)
- ✅ 4 lựa chọn (A, B, C, D)
- ✅ Thời gian: 20 giây/câu

**User trả lời đúng:**
- ✅ +15 🥮
- ✅ Chuỗi đúng liên tiếp: bonus

**User trả lời sai:**
- ✅ +0 🥮
- ✅ Reset chuỗi

---

## 17. Test Minigames - Birthday

### 17.1. Lời Chúc (wishes)

**Bước 1:**
```
/sukien chucmung
```

**Kỳ vọng:**
- ✅ Modal: "Lời Chúc Sinh Nhật"
- ✅ TextInput: 10-200 ký tự

**Bước 2:** Gửi lời chúc

**Kỳ vọng:**
- ✅ Lời chúc xuất hiện trong kênh sự kiện
- ✅ +20 🎈
- ✅ Tiến độ cộng đồng +1

**Giới hạn:**
- ✅ Tối đa 3 lời chúc/ngày

### 17.2. Bóng Bay (balloon_pop)

**Trigger (Admin):**
```
/sukien-test minigame type:balloon_pop
```

**Kỳ vọng:**
- ✅ Spawn bóng bay trong kênh
- ✅ Nút: "🎈 Bóp Bóng"
- ✅ Số lượng bóng giới hạn

**User bóp:**
- ✅ +10 🎈 mỗi bóng
- ✅ First come first served

---

## 18. Test Kết Thúc Sự Kiện

### 18.1. Kết thúc thủ công (Admin)

**Bước 1:**
```
/sukien-test end
```

**Kỳ vọng:**
- ✅ Embed kết thúc gửi vào `kenh_sukien`
- ✅ Hiển thị: Tên sự kiện, thời gian diễn ra
- ✅ Hiển thị: Tổng người tham gia
- ✅ Hiển thị: Tiến độ mục tiêu cuối cùng
- ✅ Hiển thị: Có hoàn thành 100% không
- ✅ Hiển thị: Top 3 người chơi

### 18.2. Sau khi kết thúc

**Bước 1:**
```
/sukien
```

**Kỳ vọng:**
- ✅ Thông báo: "❌ Hiện không có sự kiện nào đang diễn ra!"

**Bước 2:** Các lệnh khác

**Kỳ vọng:**
- ✅ `/sukien nhiemvu` → Lỗi: Không có sự kiện
- ✅ `/sukien cuahang` → Lỗi: Không có sự kiện
- ✅ `/sukien muctieu` → Lỗi: Không có sự kiện

### 18.3. Dữ liệu sau kết thúc

**Kỳ vọng:**
- ✅ Dữ liệu KHÔNG bị xóa (lưu trong database)
- ✅ Danh hiệu đã mở khóa vẫn còn
- ✅ Có thể xem lại thống kê (nếu có lệnh)

---

## 19. Test Bảng Xếp Hạng

### 19.1. Xem bảng xếp hạng tiền tệ

**Bước 1:**
```
/sukien xephang
```

**Kỳ vọng:**
- ✅ Top 10 người có nhiều tiền tệ nhất
- ✅ Hiển thị: #rank, avatar, tên, số tiền
- ✅ Highlight user hiện tại nếu trong top

### 19.2. Xem rank của mình

**Bước 1:**
```
/sukien rank
```

**Kỳ vọng:**
- ✅ Hiển thị rank của user
- ✅ Hiển thị số tiền
- ✅ So sánh với người trên/dưới

---

## 20. Danh Sách Sự Kiện Chi Tiết

### 🌸 Spring Festival (spring_2026)

| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Lễ Hội Hoa Xuân |
| **Thời gian** | 01/02 - 15/02/2026 |
| **Tiền tệ** | 🌸 Hoa Đào |
| **Màu** | #FFB7C5 (Hồng) |
| **Mục tiêu** | Thu thập 50,000 Hoa Đào |
| **Minigames** | lixi_auto, lixi_manual |
| **Cá sự kiện** | 7 loại |
| **Nhiệm vụ hàng ngày** | 6 loại (random 3/ngày) |
| **Thành tựu** | 5 loại |
| **Shop** | 5 vật phẩm |
| **Danh hiệu** | Người Hái Hoa (75%), Vua/Nữ Hoàng Mùa Xuân (100%) |

### 🏖️ Summer Beach (summer_2026)

| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Lễ Hội Biển |
| **Thời gian** | 01/06 - 21/06/2026 |
| **Tiền tệ** | 🐚 Vỏ Sò |
| **Màu** | #00CED1 (Xanh biển) |
| **Mục tiêu** | Tìm 100 kho báu |
| **Minigames** | treasure_hunt, boat_race |
| **Cá sự kiện** | 7 loại |
| **Shop** | 5 items |

### 🍂 Autumn Harvest (autumn_2026)

| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Thu Hoạch Mùa Thu |
| **Thời gian** | 15/09 - 30/09/2026 |
| **Tiền tệ** | 🍂 Lá Vàng |
| **Màu** | #DAA520 (Vàng) |
| **Mục tiêu** | Gửi 500 thư cảm ơn |
| **Minigames** | thank_letter, leaf_collect, tea_brewing |
| **Cá sự kiện** | 7 loại |

### ❄️ Warm Winter (winter_2026)

| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Đông Ấm Áp |
| **Thời gian** | 20/12/2026 - 05/01/2027 |
| **Tiền tệ** | ❄️ Bông Tuyết |
| **Màu** | #4169E1 (Xanh dương) |
| **Mục tiêu** | Xây 10,000 phần người tuyết |
| **Minigames** | secret_santa, snowman, countdown |
| **Cá sự kiện** | 7 loại |

### 🎃 Halloween (halloween_2026)

| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Halloween Vui Vẻ |
| **Thời gian** | 25/10 - 31/10/2026 |
| **Tiền tệ** | 🍬 Kẹo |
| **Màu** | #FF6600 (Cam) |
| **Mục tiêu** | Bắt 1,000 con ma |
| **Minigames** | ghost_hunt, trick_treat |
| **Cá sự kiện** | 5 loại |

### 🌍 Earth Day (earthday_2026)

| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Ngày Trái Đất |
| **Thời gian** | 20/04 - 24/04/2026 |
| **Tiền tệ** | 💧 Giọt Sương |
| **Màu** | #228B22 (Xanh lá) |
| **Mục tiêu** | Thu gom 5,000 rác |
| **Minigames** | trash_sort, beach_cleanup |
| **Cá sự kiện** | 4 loại |

### 🏮 Mid-Autumn (midautumn_2026)

| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Tết Trung Thu |
| **Thời gian** | 10/09 - 15/09/2026 |
| **Tiền tệ** | 🥮 Bánh Trung Thu |
| **Màu** | #FFD700 (Vàng) |
| **Mục tiêu** | Thắp 2,000 đèn lồng |
| **Minigames** | lantern_parade, quiz |
| **Cá sự kiện** | 4 loại |

### 🎂 Server Birthday (birthday_2026)

| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Sinh Nhật Server |
| **Thời gian** | 01/07 - 03/07/2026 |
| **Tiền tệ** | 🎈 Bong Bóng |
| **Màu** | #FF69B4 (Hồng) |
| **Mục tiêu** | Gửi 500 lời chúc |
| **Minigames** | wishes, balloon_pop |
| **Cá sự kiện** | Không có |

---

## 21. Checklist Tổng Hợp

### ✅ Cấu trúc Files

- [ ] 9 files JSON trong `data/events/`
- [ ] `registry.json` có 8 sự kiện
- [ ] Mỗi sự kiện có config đầy đủ

### ✅ Database Tables (16 bảng)

- [ ] active_events
- [ ] event_participation
- [ ] event_quest_progress
- [ ] event_fish_collection
- [ ] event_shop_purchases
- [ ] event_quests
- [ ] user_titles
- [ ] user_active_title
- [ ] ghost_hunt_daily
- [ ] trick_treat_daily
- [ ] snowman_contributions
- [ ] lantern_parade
- [ ] lantern_voice_time
- [ ] birthday_wishes
- [ ] treasure_hunt_daily
- [ ] beach_cleanup_daily

### ✅ Lệnh User

- [ ] `/sukien` - Xem thông tin sự kiện
- [ ] `/sukien nhiemvu` - Xem và nhận nhiệm vụ
- [ ] `/sukien cuahang` - Mua vật phẩm
- [ ] `/sukien muctieu` - Xem mục tiêu cộng đồng
- [ ] `/sukien xephang` - Bảng xếp hạng
- [ ] `/sukien bosuutap` - Bộ sưu tập cá
- [ ] `/danhhieu xem` - Xem danh hiệu
- [ ] `/danhhieu set` - Đặt danh hiệu
- [ ] `/hoso` - Profile có danh hiệu

### ✅ Lệnh Admin Test

- [ ] `/sukien-test start event_id:X` - Bắt đầu sự kiện
- [ ] `/sukien-test end` - Kết thúc sự kiện
- [ ] `/sukien-test currency action:X amount:Y` - Tiền tệ
- [ ] `/sukien-test goal progress:X` - Tiến độ cộng đồng
- [ ] `/sukien-test quest type:X progress:Y` - Nhiệm vụ
- [ ] `/sukien-test fish key:X amount:Y` - Thêm cá
- [ ] `/sukien-test minigame type:X` - Spawn minigame
- [ ] `/sukien-test title key:X` - Mở khóa danh hiệu
- [ ] `/sukien-test reset` - Reset dữ liệu test

### ✅ Services

- [ ] shop_service.py hoạt động
- [ ] community_goal_service.py hoạt động
- [ ] quest_service.py hoạt động
- [ ] participation_service.py hoạt động
- [ ] title_service.py hoạt động
- [ ] event_fish_hook.py hoạt động

### ✅ UI Components

- [ ] EventInfoView (3 tabs)
- [ ] QuestView (2 tabs, claim buttons)
- [ ] ShopView (pagination, buy buttons)
- [ ] ThankLetterModal
- [ ] GiftMessageModal
- [ ] BirthdayWishModal

### ✅ Minigames (15 total)

**Spring:**
- [ ] lixi_auto (LixiMinigame)
- [ ] lixi_manual (LixiMinigame)

**Summer:**
- [ ] treasure_hunt (TreasureHuntMinigame)
- [ ] boat_race (BoatRaceMinigame)

**Autumn:**
- [ ] thank_letter (ThankLetterMinigame)
- [ ] leaf_collect (LeafCollectMinigame)
- [ ] tea_brewing (TeaBrewingMinigame)

**Winter:**
- [ ] secret_santa (SecretSantaMinigame)
- [ ] snowman (SnowmanMinigame)
- [ ] countdown (CountdownMinigame)

**Halloween:**
- [ ] ghost_hunt (GhostHuntMinigame)
- [ ] trick_treat (TrickTreatMinigame)

**Earth Day:**
- [ ] trash_sort (TrashSortMinigame)
- [ ] beach_cleanup (BeachCleanupMinigame)

**Mid-Autumn:**
- [ ] lantern_parade (LanternParadeMinigame)
- [ ] quiz (QuizMinigame)

**Birthday:**
- [ ] wishes (WishesMinigame)
- [ ] balloon_pop (BalloonPopMinigame)

### ✅ Tự Động

- [ ] Sự kiện tự bắt đầu theo ngày (auto_start)
- [ ] Sự kiện tự kết thúc theo ngày
- [ ] Minigame auto-spawn định kỳ
- [ ] Nhiệm vụ hàng ngày tự reset 00:00
- [ ] Milestone tự thông báo khi đạt
- [ ] Voice tracking cho lantern_parade

### ✅ Embed Quality

- [ ] Tất cả text tiếng Việt
- [ ] Banner image hiển thị
- [ ] Thumbnail hiển thị
- [ ] Progress bar đúng format
- [ ] Màu sắc đúng theo sự kiện
- [ ] Emoji đúng theo tiền tệ

---

## Ghi Chú Test

### Môi trường test:
- Sử dụng server test riêng
- Có ít nhất 2-3 user để test tương tác
- Có quyền Admin để dùng `/sukien-test`

### Thứ tự test khuyến nghị:
1. Database + Files (1.1-1.2)
2. Start event (2.x)
3. Currency (3.x)
4. Quests (4.x)
5. Community goal (5.x)
6. Shop (6.x)
7. Titles (7.x)
8. Fish collection (8.x)
9. Minigames theo sự kiện (10-17)
10. End event (18.x)
11. Profile integration (9.x)

### Lỗi thường gặp:
- **"Không có sự kiện"**: Chưa start event
- **"Permission denied"**: Thiếu quyền Admin
- **"Database error"**: Kiểm tra log, có thể thiếu bảng
- **"Event not found"**: event_id sai hoặc chưa định nghĩa

---

**Phiên bản:** 2.0  
**Tác giả:** BHNBot Dev Team  
**Cập nhật cuối:** Tháng 1/2026

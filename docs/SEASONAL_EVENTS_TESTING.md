# Hướng Dẫn Test Seasonal Events

## Mục Lục
1. [Chuẩn Bị](#1-chuẩn-bị)
2. [Test Khởi Động Sự Kiện](#2-test-khởi-động-sự-kiện)
3. [Test Tiền Tệ Sự Kiện](#3-test-tiền-tệ-sự-kiện)
4. [Test Nhiệm Vụ (Quests)](#4-test-nhiệm-vụ-quests)
5. [Test Mục Tiêu Cộng Đồng](#5-test-mục-tiêu-cộng-đồng)
6. [Test Minigames](#6-test-minigames)
7. [Test Cửa Hàng](#7-test-cửa-hàng)
8. [Test Danh Hiệu](#8-test-danh-hiệu)
9. [Test Kết Thúc Sự Kiện](#9-test-kết-thúc-sự-kiện)
10. [Danh Sách Sự Kiện](#10-danh-sách-sự-kiện)

---

## 1. Chuẩn Bị

### 1.1. Cấu hình kênh
```
/config set kenh_sukien:#thông-báo-sự-kiện
/config set kenh_sukien_auto:#minigame-sự-kiện
/config set role_sukien:@Sự Kiện
```

### 1.2. Kiểm tra database migration
Bot sẽ tự tạo các bảng khi khởi động. Kiểm tra log:
```
✓ Seasonal event columns ensured
```

---

## 2. Test Khởi Động Sự Kiện

### 2.1. Bắt đầu sự kiện thủ công (Admin)
```
/sukien-test start event_id:spring_2026
```
**Kỳ vọng:**
- ✅ Embed thông báo sự kiện gửi vào `kenh_sukien`
- ✅ Hiển thị: Tên sự kiện, mô tả, tiền tệ, thời gian
- ✅ Hiển thị: Mục tiêu cộng đồng với target
- ✅ Hiển thị: Các mốc thưởng (25%, 50%, 75%, 100%)
- ✅ Hiển thị: Cá sự kiện (emoji)
- ✅ Hiển thị: Minigames có sẵn
- ✅ Hiển thị: Hướng dẫn chơi
- ✅ Banner image hiển thị (nếu có URL)
- ✅ Ping role sự kiện

### 2.2. Xem thông tin sự kiện (User)
```
/sukien
```
**Kỳ vọng:**
- ✅ Hiển thị số tiền tệ của user (ban đầu = 0)
- ✅ Hiển thị mục tiêu cộng đồng với progress bar
- ✅ Hiển thị thời gian còn lại
- ✅ Hiển thị hướng dẫn chơi

---

## 3. Test Tiền Tệ Sự Kiện

### 3.1. Thêm tiền tệ (Admin test)
```
/sukien-test currency action:add amount:500
```
**Kỳ vọng:**
- ✅ User nhận được 500 🌸 Hoa Đào
- ✅ `/sukien` hiển thị số dư mới

### 3.2. Trừ tiền tệ
```
/sukien-test currency action:spend amount:100
```
**Kỳ vọng:**
- ✅ User mất 100 🌸
- ✅ Không thể trừ nhiều hơn số dư

### 3.3. Xem số dư
```
/sukien-test currency action:check
```

---

## 4. Test Nhiệm Vụ (Quests)

### 4.1. Xem nhiệm vụ
```
/sukien nhiemvu
```
**Kỳ vọng:**
- ✅ Tab "Hàng ngày" hiển thị 3 nhiệm vụ ngẫu nhiên
- ✅ Tab "Thành tựu" hiển thị nhiệm vụ cố định
- ✅ Hiển thị progress: 0/target
- ✅ Hiển thị phần thưởng cho mỗi nhiệm vụ

### 4.2. Cập nhật tiến độ nhiệm vụ (tự động)
Khi user thực hiện hành động liên quan (câu cá, chat, voice...), tiến độ tự tăng.

### 4.3. Nhận thưởng nhiệm vụ
Khi hoàn thành nhiệm vụ:
- ✅ Nút "Nhận" xuất hiện
- ✅ Bấm nhận → nhận tiền tệ
- ✅ Không thể nhận lại lần 2

### 4.4. Reset nhiệm vụ hàng ngày
Nhiệm vụ hàng ngày reset lúc 00:00. Test bằng cách đổi ngày hệ thống hoặc chờ.

---

## 5. Test Mục Tiêu Cộng Đồng

### 5.1. Xem mục tiêu
```
/sukien muctieu
```
**Kỳ vọng:**
- ✅ Hiển thị mô tả mục tiêu
- ✅ Progress bar
- ✅ Danh sách các mốc thưởng với trạng thái

### 5.2. Cập nhật tiến độ cộng đồng (Admin test)
```
/sukien-test milestone progress:5000
```
**Kỳ vọng:**
- ✅ Tiến độ cộng đồng tăng lên
- ✅ Khi đạt mốc 25% (12,500) → thông báo milestone

### 5.3. Test các mốc thưởng

**Mốc 25% (12,500):**
- ✅ Thông báo đạt mốc
- ✅ Tất cả người tham gia nhận +200 hạt giống

**Mốc 50% (25,000):**
- ✅ Thông báo đạt mốc
- ✅ Tất cả nhận buff x2 cá trong 24h

**Mốc 75% (37,500):**
- ✅ Thông báo đạt mốc
- ✅ Tất cả mở khóa danh hiệu "Người Hái Hoa"

**Mốc 100% (50,000):**
- ✅ Thông báo HOÀN THÀNH
- ✅ Tất cả nhận 500 Hoa Đào + danh hiệu đặc biệt

---

## 6. Test Minigames

### 6.1. Lì Xì Tự Động (lixi_auto)

**Trigger spawn (Admin):**
```
/sukien-test minigame type:lixi_auto
```
**Kỳ vọng:**
- ✅ Embed Lì Xì xuất hiện trong `kenh_sukien_auto`
- ✅ Có nút "🧧 Nhận Lì Xì"
- ✅ Hiển thị số người đã nhận / tối đa
- ✅ Hiển thị thời gian hết hạn

**User nhận Lì Xì:**
- ✅ Bấm nút → nhận ngẫu nhiên 5-50 🌸
- ✅ Thông báo ephemeral số tiền nhận được
- ✅ Không thể nhận lần 2
- ✅ Embed cập nhật số người đã nhận

**Hết lượt/hết thời gian:**
- ✅ Embed chuyển sang trạng thái "đã hết"
- ✅ Nút bị disable

### 6.2. Lì Xì Tặng Bạn (lixi_manual)

**Tạo Lì Xì (User có tiền):**
```
/lixi tao so_tien:100 so_phan:5 loi_chuc:"Chúc mừng năm mới!"
```
**Kỳ vọng:**
- ✅ Trừ 100 🌸 từ người tạo
- ✅ Embed Lì Xì xuất hiện
- ✅ Hiển thị: người gửi, tổng giá trị, số phần, lời chúc
- ✅ Hiển thị thời gian hết hạn (5 phút)

**User khác nhận:**
- ✅ Bấm nút → nhận ngẫu nhiên (chia đều)
- ✅ Người tạo KHÔNG thể tự nhận
- ✅ Embed cập nhật số phần còn lại

**Hết phần:**
- ✅ Embed hiển thị danh sách người nhận + số tiền

**Hết thời gian còn phần:**
- ✅ Hoàn tiền còn lại cho người tạo

---

## 7. Test Cửa Hàng

### 7.1. Xem cửa hàng
```
/sukien cuahang
```
**Kỳ vọng:**
- ✅ Hiển thị số dư hiện tại
- ✅ Danh sách vật phẩm với giá
- ✅ ✅ nếu đủ tiền, ❌ nếu không đủ
- ✅ Phân trang nếu nhiều vật phẩm

### 7.2. Mua vật phẩm
- ✅ Bấm nút "Mua" → trừ tiền → nhận vật phẩm
- ✅ Thông báo mua thành công
- ✅ Nút disable nếu không đủ tiền

### 7.3. Vật phẩm Spring Event:
| Vật phẩm | Giá | Loại |
|----------|-----|------|
| Cành Đào Trang Trí | 500 | decoration |
| Áo Dài Xuân | 1000 | outfit |
| Khung Avatar Tết | 800 | frame |
| Hộp Quà Bí Ẩn | 300 | lootbox |
| Danh Hiệu VIP Xuân | 2000 | title |

---

## 8. Test Danh Hiệu

### 8.1. Xem danh hiệu đã mở
```
/sukien danhieu
```

### 8.2. Đổi danh hiệu đang dùng
```
/sukien danhieu chon:Người Hái Hoa
```
**Kỳ vọng:**
- ✅ Chỉ hiển thị danh hiệu đã mở khóa
- ✅ Đổi thành công

### 8.3. Danh hiệu Spring Event:
- **Người Hái Hoa** - Mốc 75%
- **Vua/Nữ Hoàng Mùa Xuân** - Mốc 100%
- **VIP Xuân 2026** - Mua từ shop

---

## 9. Test Kết Thúc Sự Kiện

### 9.1. Kết thúc thủ công (Admin)
```
/sukien-test end
```
**Kỳ vọng:**
- ✅ Embed kết thúc gửi vào `kenh_sukien`
- ✅ Hiển thị kết quả cuối cùng
- ✅ Hiển thị tổng người tham gia
- ✅ Hiển thị có hoàn thành mục tiêu không

### 9.2. Sau khi kết thúc
- ✅ `/sukien` → "Không có sự kiện đang diễn ra"
- ✅ Các lệnh sự kiện bị disable
- ✅ Dữ liệu được lưu trữ (không xóa)

---

## 10. Danh Sách Sự Kiện

### 🌸 Spring Festival (spring_2026)
| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Lễ Hội Hoa Xuân |
| **Thời gian** | 01/02 - 15/02/2026 |
| **Tiền tệ** | 🌸 Hoa Đào |
| **Màu** | #FFB7C5 (Hồng) |
| **Mục tiêu** | Thu thập 50,000 Hoa Đào |
| **Minigames** | Lì Xì Tự Động, Lì Xì Tặng Bạn |
| **Cá sự kiện** | 7 loại (🐡🦐🐠🐟🦑🐙🦞) |
| **Nhiệm vụ hàng ngày** | 6 loại (random 3/ngày) |
| **Thành tựu** | 5 loại |
| **Shop** | 5 vật phẩm |

---

### 🏖️ Summer Beach (summer_2026)
| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Lễ Hội Biển |
| **Thời gian** | 01/06 - 21/06/2026 |
| **Tiền tệ** | 🐚 Vỏ Sò |
| **Màu** | #00CED1 (Xanh biển) |
| **Mục tiêu** | Tìm 100 kho báu |
| **Minigames** | Săn Kho Báu, Đua Thuyền |

---

### 🍂 Autumn Harvest (autumn_2026)
| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Thu Hoạch Mùa Thu |
| **Thời gian** | 15/09 - 30/09/2026 |
| **Tiền tệ** | 🍂 Lá Vàng |
| **Màu** | #DAA520 (Vàng) |
| **Mục tiêu** | Gửi 500 thư cảm ơn |
| **Minigames** | Thư Cảm Ơn, Thu Lá, Pha Trà |

---

### ❄️ Warm Winter (winter_2026)
| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Đông Ấm Áp |
| **Thời gian** | 20/12/2026 - 05/01/2027 |
| **Tiền tệ** | ❄️ Bông Tuyết |
| **Màu** | #4169E1 (Xanh dương) |
| **Mục tiêu** | Xây 10,000 phần người tuyết |
| **Minigames** | Secret Santa, Người Tuyết, Đếm Ngược |

---

### 🎃 Halloween (halloween_2026)
| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Halloween Vui Vẻ |
| **Thời gian** | 25/10 - 31/10/2026 |
| **Tiền tệ** | 🍬 Kẹo |
| **Màu** | #FF6600 (Cam) |
| **Mục tiêu** | Bắt 1,000 con ma |
| **Minigames** | Săn Ma, Trick or Treat |

---

### 🌍 Earth Day (earthday_2026)
| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Ngày Trái Đất |
| **Thời gian** | 20/04 - 24/04/2026 |
| **Tiền tệ** | 💧 Giọt Sương |
| **Màu** | #228B22 (Xanh lá) |
| **Mục tiêu** | Thu gom 5,000 rác |
| **Minigames** | Phân Loại Rác, Dọn Bãi Biển |
| **Buff đặc biệt** | x2 XP Trồng Cây |

---

### 🏮 Mid-Autumn (midautumn_2026)
| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Tết Trung Thu |
| **Thời gian** | 10/09 - 15/09/2026 |
| **Tiền tệ** | 🥮 Bánh Trung Thu |
| **Màu** | #FFD700 (Vàng) |
| **Mục tiêu** | Thắp 2,000 đèn lồng |
| **Minigames** | Rước Đèn, Câu Đố |

---

### 🎂 Server Birthday (birthday_2026)
| Thuộc tính | Giá trị |
|------------|---------|
| **Tên** | Sinh Nhật Server |
| **Thời gian** | 01/07 - 03/07/2026 |
| **Tiền tệ** | 🎈 Bong Bóng |
| **Màu** | #FF69B4 (Hồng) |
| **Mục tiêu** | Gửi 500 lời chúc |
| **Minigames** | Gửi Lời Chúc, Bắn Bóng |

---

## Checklist Tổng Hợp

### Cấu trúc
- [ ] 8 sự kiện được định nghĩa trong registry.json
- [ ] Mỗi sự kiện có file config riêng (spring.json, summer.json...)
- [ ] Database migration chạy đúng

### Lệnh User
- [ ] `/sukien` - Xem thông tin
- [ ] `/sukien nhiemvu` - Xem và nhận nhiệm vụ
- [ ] `/sukien cuahang` - Mua vật phẩm
- [ ] `/sukien xephang` - Bảng xếp hạng
- [ ] `/sukien danhieu` - Quản lý danh hiệu
- [ ] `/sukien muctieu` - Xem mục tiêu cộng đồng
- [ ] `/lixi tao` - Tạo lì xì tặng bạn

### Lệnh Admin
- [ ] `/sukien-test start` - Bắt đầu sự kiện
- [ ] `/sukien-test end` - Kết thúc sự kiện
- [ ] `/sukien-test currency` - Thao tác tiền tệ
- [ ] `/sukien-test minigame` - Spawn minigame
- [ ] `/sukien-test milestone` - Cập nhật tiến độ

### Tự động
- [ ] Sự kiện tự bắt đầu/kết thúc theo ngày
- [ ] Minigame tự spawn định kỳ
- [ ] Nhiệm vụ hàng ngày tự reset
- [ ] Milestone tự thông báo khi đạt

### Embed
- [ ] Tất cả tiếng Việt
- [ ] Có banner image + thumbnail
- [ ] Có mô tả + hướng dẫn
- [ ] Có mục tiêu cộng đồng
- [ ] Progress bar hiển thị đúng

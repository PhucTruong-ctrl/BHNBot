# Hướng Dẫn Test Hệ Thống VIP - BHNBot

Tài liệu này hướng dẫn quản trị viên (Owner) cách kiểm thử toàn diện các tính năng VIP sau khi hệ thống đã được cập nhật hoặc sửa lỗi.

## 1. Chuẩn Bị Trước Khi Test

### Yêu cầu
- Tài khoản Discord có quyền **Administrator** trong server test.
- Bot đang chạy và online (Dùng `/ping` để kiểm tra).
- Số dư Hạt (seeds) tối thiểu **500,000** để test gói cao nhất.

### Lệnh Admin hỗ trợ
Sử dụng các lệnh sau để chuẩn bị tài nguyên test:
```bash
/themhat @user 1000000  # Cộng 1 triệu hạt để test mua VIP
/themitem @user item_key 10  # (Nếu cần) Thêm item hỗ trợ
```

---

## 2. Danh Sách Các Test Case

### TC01: Mua VIP & Nâng Cấp (Flow Chính)
**Mục tiêu**: Đảm bảo luồng mua VIP không bị lỗi và logic trừ tiền, cộng ngày hoạt động đúng.

**Các bước thực hiện**:
1. Gõ `/thuongluu action:Mua VIP (b)`.
2. Click nút **"Mua Bạc (50k)"**.
3. **Xác nhận**:
   - [ ] Tin nhắn "MUA VIP THÀNH CÔNG" hiện ra (ephemeral).
   - [ ] Số dư hạt bị trừ đúng 50,000.
   - [ ] Gõ `/thuongluu action:Trạng thái (s)` kiểm tra thấy Tier Bạc, hạn dùng ~30 ngày.
4. Tiếp tục gõ `/thuongluu action:Mua VIP (b)` và chọn **"Mua Vàng (150k)"**.
5. **Xác nhận**:
   - [ ] Tier được nâng lên Vàng (🥇).
   - [ ] Tiền bị trừ thêm 150,000.
   - [ ] Hạn dùng được cộng thêm 30 ngày (Tổng ~60 ngày).

---

### TC02: Chống Hạ Cấp (No Downgrade)
**Mục tiêu**: Đảm bảo khi đang ở Tier cao, mua gói thấp hơn sẽ chỉ cộng thêm ngày chứ không bị hạ Tier.

**Các bước thực hiện**:
1. Đảm bảo đang là VIP **Kim Cương** (Tier 3).
2. Gõ `/thuongluu action:Mua VIP (b)` -> Chọn mua gói **Bạc**.
3. **Xác nhận**:
   - [ ] Thông báo thành công hiện ra.
   - [ ] Kiểm tra `/thuongluu action:Trạng thái (s)`: Tier **VẪN LÀ Kim Cương**.
   - [ ] Thời gian hết hạn được cộng thêm 30 ngày.

---

### TC03: Nối Từ - VIP Hint (`/nthint`)
**Mục tiêu**: Kiểm tra tính năng độc quyền cho VIP trong game Nối Từ.

**Các bước thực hiện**:
1. (Nếu chưa có game) Gõ `/noitu start` trong channel game.
2. Gõ `/nthint`.
3. **Xác nhận**:
   - [ ] Bot trả về các gợi ý từ (ephemeral).
   - [ ] Gợi ý bắt đầu bằng âm cuối của từ hiện tại trong game.
4. **Test Non-VIP**: Dùng acc không có VIP gõ `/nthint` -> Phải nhận thông báo từ chối.

---

### TC04: Bầu Cua - Instant Cashback
**Mục tiêu**: Kiểm tra tính năng hoàn tiền ngay lập tức khi thua cho VIP.

**Các bước thực hiện**:
1. Đang có VIP (Tier 1: 2%, Tier 2: 3%, Tier 3: 5%).
2. Gõ `/baucua` hoặc `!bc -q 10000 bau`.
3. Đặt cược và đợi kết quả **THUA**.
4. **Xác nhận**:
   - [ ] Kết quả game có dòng thông báo: *"Đặc quyền VIP: Hồi máu... hạt"* (Dòng này chỉ hiện nếu là VIP).
   - [ ] Kiểm tra số dư hạt: Phải được cộng lại số tiền tương ứng % cashback của Tier.

---

### TC05: Cây Server - Đăng Ký Auto Water
**Mục tiêu**: Test tính năng tự động tưới cây (Chỉ dành cho VIP 3).

**Các bước thực hiện**:
1. Phải là VIP **Kim Cương**.
2. Gõ `/tuoi` (hoặc `/gophat` không nhập số).
3. Click nút **"Đăng Ký Auto (50k/tháng)"** trong menu.
4. **Xác nhận**:
   - [ ] Tiền bị trừ 50,000 Hạt.
   - [ ] Thông báo đăng ký thành công.
   - [ ] (Option cho Admin) Kiểm tra DB: `SELECT * FROM vip_auto_tasks WHERE user_id = 'ID_CỦA_BẠN';`

---

### TC06: Câu Cá - VIP Fish Pool
**Mục tiêu**: Xác nhận VIP có thể bắt được cá hiếm.

**Các bước thực hiện**:
1. Sử dụng lệnh `/cauca` liên tục.
2. **Xác nhận**:
   - [ ] Có thể bắt được các loại cá có badge VIP (🥈/🥇/💎) như: *Thiên Nga, Cá Voi Xanh, Thần Poseidon...*
   - [ ] Kiểm tra kho đồ `/kho` xem cá VIP có được lưu đúng không.

---

### TC07: Aquarium - Theme VIP
**Mục tiêu**: Test đổi hình nền hồ cá (Dành cho VIP 2+).

**Các bước thực hiện**:
1. Gõ `/trangtri theme`.
2. Nhập một URL hình ảnh (Ví dụ: Link ảnh GIF hoặc PNG trên Discord).
3. **Xác nhận**:
   - [ ] Bot thông báo đổi theme thành công.
   - [ ] Gõ `/hoca` kiểm tra xem hình nền đã thay đổi chưa.

---

## 3. Checklist Tổng Hợp

| STT | Tính năng | Trạng thái | Ghi chú |
|:---:|:---|:---:|:---|
| 1 | Mua VIP (Bạc/Vàng/Kim Cương) | ⬜ | Khấu trừ tiền & cộng ngày đúng |
| 2 | Status hiển thị chính xác | ⬜ | `/thuongluu s` |
| 3 | Leaderboard VIP | ⬜ | `/thuongluu t` |
| 4 | Gợi ý Nối Từ (`/nthint`) | ⬜ | Chỉ VIP mới dùng được |
| 5 | Hoàn tiền Bầu Cua | ⬜ | 2% / 3% / 5% khi thua |
| 6 | Auto-Water (Cây Server) | ⬜ | Yêu cầu VIP 3 + 50k phí |
| 7 | Câu được cá VIP | ⬜ | Theo tier (3 / 8 / 15 loài) |
| 8 | Đổi Theme Hồ Cá | ⬜ | VIP 2+ (Hỗ trợ GIF) |

---

## 4. Xử Lý Sự Cố & Reset Dữ liệu Test

Nếu muốn xóa trạng thái VIP để test lại từ đầu, Owner có thể chạy các lệnh SQL sau trong database:

```sql
-- Xóa sub VIP để test lại mua mới
DELETE FROM vip_subscriptions WHERE user_id = 'ID_CỦA_BẠN';

-- Xóa task auto
DELETE FROM vip_auto_tasks WHERE user_id = 'ID_CỦA_BẠN';

-- Hoàn tiền hạt (nếu cần)
UPDATE users SET seeds = seeds + 1000000 WHERE user_id = 'ID_CỦA_BẠN';
```

**Lưu ý**: Sau khi chạy SQL, hãy restart bot hoặc chờ 5 phút để cache của `VIPEngine` được cập nhật.

---
**Cập nhật lần cuối**: 06/01/2026
**Tác giả**: AI Technical Writer Agent

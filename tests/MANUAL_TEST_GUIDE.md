# BHNBot - Manual Test Guide (Discord UI)

## 🚨 CÁC TÍNH NĂNG CẦN TEST THỦ CÔNG

Những tính năng này KHÔNG thể test bằng script vì cần Discord UI interaction.

---

## PRE-REQUISITES

```bash
# 1. Khởi động bot
cd /home/phuctruong/Work/BHNBot
pkill -f "python3 main.py"
sleep 2
nohup .venv/bin/python3 main.py > /tmp/bot.log 2>&1 &

# 2. Kiểm tra bot online
sleep 5
tail -20 /tmp/bot.log

# 3. Thêm seeds cho test user
# Trong Discord, dùng lệnh admin:
/themhat @YourUser 500000
```

---

## TEST 1: VIP PURCHASE FLOW

### Mục đích: Kiểm tra mua VIP hoạt động đúng

### Steps:
1. Mở Discord, vào server có bot
2. Gõ: `/thuongluu b`
3. **Expected:** Hiện embed với 3 buttons: 🥈 BẠC, 🥇 VÀNG, 💎 KIM CƯƠNG
4. Click button "🥈 BẠC (10k)"
5. **Expected:** 
   - Nếu đủ tiền: Mua thành công, hiện embed "✅ Đăng ký VIP Bạc thành công!"
   - Nếu không đủ: "❌ Không đủ tiền!"
6. Gõ: `/thuongluu s`
7. **Expected:** Hiện status VIP với tier, ngày hết hạn

### Pass Criteria:
- [OK] Buttons hiển thị đúng
- [OK] Purchase thành công deduct seeds
- [OK] Status hiển thị đúng tier và expiry

---

## TEST 2: VIP STATUS & LEADERBOARD

### Mục đích: Kiểm tra xem status và bảng xếp hạng

### Steps:
1. Gõ: `/thuongluu s`
2. **Expected:** Hiện embed với:
   - Tier hiện tại (Bạc/Vàng/Kim Cương)
   - Ngày hết hạn
   - Tổng số ngày VIP
   - Tổng chi tiêu
3. Gõ: `/thuongluu t`
4. **Expected:** Hiện bảng xếp hạng VIP theo total_spent

### Pass Criteria:
- [OK] Status hiển thị chính xác
- [OK] Leaderboard sắp xếp đúng theo chi tiêu

---

## TEST 3: BẦU CUA CASHBACK

### Mục đích: Kiểm tra VIP nhận cashback khi thua

### Steps:
1. Đảm bảo user có VIP active
2. Gõ: `/baucua`
3. Đặt cược và THUA (đặt vào con không ra)
4. **Expected:** Sau game kết thúc, nhận thông báo cashback:
   - Tier 1: 2% của số thua
   - Tier 2: 3% của số thua  
   - Tier 3: 5% của số thua
5. Check logs:
   ```bash
   grep INSTANT_CASHBACK /tmp/bot.log | tail -5
   ```

### Pass Criteria:
- [OK] Cashback hiển thị trong result
- [OK] Seeds được cộng vào tài khoản
- [OK] Log ghi nhận cashback

---

## TEST 4: TREE AUTO-WATER

### Mục đích: Kiểm tra VIP tier 3 được auto-water

### Steps:
1. User cần có VIP tier 3
2. Đăng ký auto-water: `/gophat` → Chọn "Đăng ký Auto-Tưới"
3. **Expected:** Thông báo đăng ký thành công
4. Check database:
   ```bash
   PGPASSWORD=postgres psql -h localhost -U postgres -d bhnbot_db -c \
   "SELECT * FROM vip_auto_tasks WHERE task_type='auto_water';"
   ```
5. Trigger manual test (owner only):
   ```
   !test_autowater
   ```
6. Check tree contribution: `/cay`

### Pass Criteria:
- [ ] Đăng ký thành công
- [ ] Record xuất hiện trong vip_auto_tasks
- [ ] Contribution được thêm (100 XP)

---

## TEST 5: /NTHINT (VIP-ONLY)

### Mục đích: Kiểm tra gợi ý từ chỉ cho VIP

### Steps:
1. Vào kênh có game Nối Từ đang chạy
2. Gõ: `/nthint`
3. **Nếu KHÔNG có VIP:**
   - **Expected:** "❌ Chức năng này chỉ dành cho VIP!"
4. **Nếu CÓ VIP:**
   - **Expected:** Ephemeral message với gợi ý từ

### Pass Criteria:
- [ ] Non-VIP bị từ chối
- [ ] VIP nhận gợi ý ephemeral
- [ ] Gợi ý là từ hợp lệ trong dictionary

---

## TEST 6: VIP FISH POOL

### Mục đích: Kiểm tra VIP câu được cá đặc biệt

### Steps:
1. Có VIP active
2. Đi câu cá nhiều lần: `/cauca`
3. Sau 20-30 lần, check xem có câu được cá VIP không
4. Check logs:
   ```bash
   grep "VIP" /tmp/bot.log | grep -i fish | tail -10
   ```

### Pass Criteria:
- [ ] VIP có cơ hội câu được cá từ VIP pool
- [ ] Tier càng cao, pool càng lớn (3/8/15 cá)

---

## TEST 7: AQUARIUM THEMES (VIP 2+)

### Mục đích: Kiểm tra VIP tier 2+ đổi được theme

### Steps:
1. Cần VIP tier 2 hoặc 3
2. Gõ: `/trangtri theme https://example.com/image.gif`
3. **Nếu tier 1:** "❌ Chức năng này chỉ dành cho VIP Vàng trở lên!"
4. **Nếu tier 2+:** "✅ Đã cập nhật theme!"
5. Xem aquarium: `/nha`
6. **Expected:** Background là hình đã set

### Pass Criteria:
- [ ] Tier 1 bị từ chối
- [ ] Tier 2+ set được theme
- [ ] Theme hiển thị trong /nha

---

## TEST 8: PRESTIGE BADGES

### Mục đích: Kiểm tra huy hiệu prestige

### Steps:
1. Góp hạt cho cây: `/gophat 1000`
2. Gõ: `/huyhieu`
3. **Expected:** Hiện embed với:
   - Badge hiện tại (🌱/🌿/🌳/🌸/🍎)
   - Tổng XP
   - Progress đến tier tiếp theo
4. Xem leaderboard: `/cay`
5. **Expected:** Top contributors có badge bên cạnh tên

### Pass Criteria:
- [ ] /huyhieu hiển thị đúng tier
- [ ] Badge xuất hiện trong leaderboard
- [ ] Tier thay đổi khi đạt threshold

---

## TEST 9: GIFT SYSTEM

### Mục đích: Kiểm tra tặng quà

### Steps:
1. Mua item để tặng: `/mua cafe`
2. Tặng quà: `/tangqua @Friend cafe`
3. **Expected:** Embed hiện với message tặng quà
4. Tặng ẩn danh: `/tangqua @Friend cafe an_danh:True`
5. **Expected:** Sender không hiển thị
6. Spam test: Tặng 11 lần liên tục
7. **Expected:** (Nếu có rate limit) "⏳ Bạn đã tặng quá nhiều!"

### Pass Criteria:
- [ ] Gift gửi thành công
- [ ] Anonymous mode hoạt động
- [ ] Item bị trừ khỏi inventory
- [ ] Rate limit (nếu implemented)

---

## TEST 10: VIP STYLING

### Mục đích: Kiểm tra VIP có embed đẹp hơn

### Steps:
1. Có VIP active
2. Thực hiện bất kỳ command nào: `/tuido`, `/cauca`, `/baucua`
3. **Expected:** Embed có:
   - Prefix tier: 🥈 [BẠC], 🥇 [VÀNG], 💎 [KIM CƯƠNG]
   - Màu khác (silver/gold/blue)
   - Footer có VIP quote ngẫu nhiên

### Pass Criteria:
- [ ] Prefix tier hiển thị
- [ ] Màu embed đúng theo tier
- [ ] Footer có quote

---

## QUICK TEST COMMANDS

```bash
# Monitor bot logs real-time
tail -f /tmp/bot.log

# Check VIP subscriptions
PGPASSWORD=postgres psql -h localhost -U postgres -d bhnbot_db -c \
"SELECT user_id, tier_level, expiry_date FROM vip_subscriptions LIMIT 10;"

# Check auto-water tasks
PGPASSWORD=postgres psql -h localhost -U postgres -d bhnbot_db -c \
"SELECT * FROM vip_auto_tasks;"

# Check tree contributors
PGPASSWORD=postgres psql -h localhost -U postgres -d bhnbot_db -c \
"SELECT user_id, contribution_exp FROM tree_contributors ORDER BY contribution_exp DESC LIMIT 10;"

# Force add VIP for testing
PGPASSWORD=postgres psql -h localhost -U postgres -d bhnbot_db -c \
"INSERT INTO vip_subscriptions (user_id, tier_level, expiry_date) 
VALUES (YOUR_USER_ID, 3, NOW() + INTERVAL '30 days')
ON CONFLICT (user_id) DO UPDATE SET tier_level = 3, expiry_date = NOW() + INTERVAL '30 days';"
```

---

## ADMIN COMMANDS FOR TESTING

```
# Thêm seeds
/themhat @user 100000

# Force cashback test (owner only)
!test_cashback

# Force auto-water (owner only)
!test_autowater

# Health check
/healthcheck
```

---

## CHECKLIST TỔNG HỢP

### Automated Tests (Script): 38/39 ✅
- [x] Database connection
- [x] VIP data fetching (partial - needs bot context)
- [x] Prorated calculation
- [x] Cashback calculation
- [x] Prestige badge logic
- [x] Rate limiting logic
- [x] Transaction safety
- [x] Tier downgrade prevention
- [x] VIP expiry check
- [x] Module imports

### Manual Tests (Discord UI):
- [ ] TEST 1: VIP Purchase Flow
- [ ] TEST 2: VIP Status & Leaderboard
- [ ] TEST 3: Bầu Cua Cashback
- [ ] TEST 4: Tree Auto-Water
- [ ] TEST 5: /nthint (VIP-only)
- [ ] TEST 6: VIP Fish Pool
- [ ] TEST 7: Aquarium Themes
- [ ] TEST 8: Prestige Badges
- [ ] TEST 9: Gift System
- [ ] TEST 10: VIP Styling

---

## REPORT TEMPLATE

Sau khi test xong, điền kết quả:

```
=== BHNBot VIP System Test Report ===
Date: ____________________
Tester: __________________

AUTOMATED TESTS: 38/39 passed

MANUAL TESTS:
[ ] TEST 1: VIP Purchase - PASS/FAIL - Notes: ________
[ ] TEST 2: VIP Status - PASS/FAIL - Notes: ________
[ ] TEST 3: Cashback - PASS/FAIL - Notes: ________
[ ] TEST 4: Auto-Water - PASS/FAIL - Notes: ________
[ ] TEST 5: /nthint - PASS/FAIL - Notes: ________
[ ] TEST 6: Fish Pool - PASS/FAIL - Notes: ________
[ ] TEST 7: Themes - PASS/FAIL - Notes: ________
[ ] TEST 8: Badges - PASS/FAIL - Notes: ________
[ ] TEST 9: Gifts - PASS/FAIL - Notes: ________
[ ] TEST 10: Styling - PASS/FAIL - Notes: ________

OVERALL: ____/10 Manual Tests Passed
ISSUES FOUND: ________________________________
```

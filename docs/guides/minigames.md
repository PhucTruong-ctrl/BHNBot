#  MINIGAMES (GIẢI TRÍ)

Ngoài câu cá, Mèo Lùn có các trò chơi dân gian để bạn giải trí (hoặc thử thách nhân phẩm) cùng bạn bè.

---

## 1. Xì Dách (Blackjack) 
Game bài kinh điển. Mục tiêu là đạt điểm gần 21 nhất nhưng không vượt quá.

*   **Lệnh:** `/xidach [số tiền cược]` (Tối thiểu 1 Hạt).
*   **Luật chơi (Kiểu VN):**
    *   **Ngũ Linh:** 5 lá bài tổng điểm <= 21 -> Thưởng **3.5x**.
    *   **Xì Bàn:** 2 lá Át (AA) -> Thưởng **3.0x**.
    *   **Xì Dách:** 1 Át + 1 Tây (J, Q, K) hoặc 10 -> Thưởng **2.5x**.
    *   **Thắng thường:** Điểm cao hơn nhà cái -> Thưởng **2.0x**.
    *   **Đủ tuổi:** Từ 16 điểm trở lên mới được dằn (xét bài).
    *   **Quắc:** Trên 21 điểm (Thua).
*   **Tính năng đặc biệt:**
    *   **Gấp đôi (Double):** Cược thêm 100%, rút thêm ĐÚNG 1 lá và kết thúc lượt.

---

## 2. Bầu Cua Tôm Cá 
Trò chơi thử vận may truyền thống.

*   **Lệnh:** `/baucua` để mở bàn chơi.
*   **Thời gian:** 45 giây đặt cược, 10 giây hồi chiêu (Cooldown).
*   **Giới hạn:** Cược tối đa **250,000 Hạt**.
*   **Trả thưởng:**
    *   Trúng 1 mặt: **x2** tiền cược (Hoàn vốn + Thắng 1).
    *   Trúng 2 mặt: **x3** tiền cược.
    *   Trúng 3 mặt: **x4** tiền cược.
*   **Hoàn Tiền (VIP Cashback):** VIP Bạc/Vàng/Kim Cương nhận lại 2%/3%/5% số tiền thua (Tối đa 10k/ngày).

---

## 3. Nối Từ 
Game trí tuệ nhẹ nhàng, kiếm tiền bền vững.

*   **Lệnh:** Tham gia kênh Nối Từ (được config bởi admin).
*   **Cách chơi:**
    *   Người đầu tiên đưa ra 1 từ (Ví dụ: "Con mèo").
    *   Người tiếp theo phải nối từ bắt đầu bằng chữ cuối (Ví dụ: "Mèo con").
*   **Luật & Thưởng:**
    *   Phải là từ có nghĩa (2 âm tiết).
    *   Thời gian suy nghĩ: **60 giây**.
    *   **Phần thưởng:** `max(20, Chuỗi thắng * 5)` + Bonus 3 Hạt/từ đúng.
    *   **Thưởng mốc:** Cả nhóm nhận thêm **20 Hạt** mỗi khi đạt mốc 10 từ.

---

## 4. Ma Sói (Werewolf) 
Game nhập vai suy luận, cần nhiều người chơi (Voice/Chat).

*   **Lệnh:** `/masoi create` (Tạo bàn).
*   **Số người:** Tối thiểu 5 người.
*   **Hệ thống Cân Bằng (Role Points):**
    *   Phe Dân: Tiên Tri (+7), Phù Thủy (+4), Bảo Vệ (+3).
    *   Phe Sói: Ma Sói (-6), Sói Trắng (-10), Sói Quỷ (-9).
*   **Tính năng xịn:** Bot tự động tạo kênh riêng, mute/unmute voice chat theo ngày/đêm.

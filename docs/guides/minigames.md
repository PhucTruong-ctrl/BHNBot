#  MINIGAMES (GIẢI TRÍ)

Ngoài câu cá, Mèo Lùn có các trò chơi dân gian để bạn giải trí (hoặc thử thách nhân phẩm) cùng bạn bè.

---

## 1. Xì Dách (Blackjack) 
Game bài kinh điển. Mục tiêu là đạt điểm gần 21 nhất nhưng không vượt quá.

*   **Lệnh:** `/xidach [số tiền cược]`
*   **Luật chơi (Kiểu VN):**
    *   **Ngũ Linh:** 5 lá bài tổng điểm <= 21 (Thắng tuyệt đối).
    *   **Xì Bàn:** 2 lá Át (AA).
    *   **Xì Dách:** 1 Át + 1 Tây (J, Q, K) hoặc 10.
    *   **Đủ tuổi:** Từ 16 điểm trở lên mới được dằn (xét bài).
    *   **Quắc:** Trên 21 điểm (Thua).
*   **Cách chơi:** Bot sẽ chia bài và hiện các nút: *Rút bài (Hit)*, *Dằn non (Stand)*, *Gấp đôi (Double)*.

---

## 2. Bầu Cua Tôm Cá 
Trò chơi thử vận may truyền thống.

*   **Lệnh:** `/baucua` để mở bàn chơi.
*   **Cách chơi:**
    *   Đặt cược vào 6 linh vật: **Bầu, Cua, Tôm, Cá, Gà, Nai**.
    *   Sau 45 giây, bot sẽ lắc 3 xúc xắc.
*   **Trả thưởng:**
    *   Trúng 1 mặt: x2 tiền cược (Hoàn vốn + Thắng 1).
    *   Trúng 2 mặt: x3 tiền cược.
    *   Trúng 3 mặt: x4 tiền cược.
*   **Lệnh nhanh:** `!bc -q 5000 bau` (Cược nhanh 5000 vào Bầu).

---

## 3. Nối Từ 
Game trí tuệ nhẹ nhàng, kiếm tiền bền vững.

*   **Lệnh:** Tham gia kênh Nối Từ (được config bởi admin).
*   **Cách chơi:**
    *   Người đầu tiên đưa ra 1 từ (Ví dụ: "Con mèo").
    *   Người tiếp theo phải nối từ bắt đầu bằng chữ cuối (Ví dụ: "Mèo con").
*   **Luật:**
    *   Phải là từ có nghĩa (trong từ điển Tiếng Việt).
    *   Không được dùng lại từ đã dùng trong ván.
    *   Mỗi từ đúng nhận +Hạt.
    *   Chuỗi (Streak) càng dài, thưởng càng to.

---

## 4. Ma Sói (Werewolf) 
Game nhập vai suy luận, cần nhiều người chơi (Voice/Chat).

*   **Lệnh:** `/masoi create` (Tạo bàn).
*   **Số người:** Tối thiểu 5 người.
*   **Luật chơi:**
    *   Bot sẽ chia phe: **Dân Làng** vs **Sói**.
    *   **Ban Đêm:** Sói chọn người để cắn, Tiên tri soi, Bảo vệ canh gác... (Tương tác qua DM riêng với Bot).
    *   **Ban Ngày:** Cả làng thảo luận và bỏ phiếu treo cổ người bị nghi ngờ.
*   **Tính năng xịn:** Bot tự động tạo kênh riêng, mute/unmute voice chat theo ngày/đêm (nếu chơi Voice).
*   **Vai trò:** Hơn 39 vai trò khác nhau (Tiên tri, Phù thủy, Thợ săn, Kẻ phóng hỏa, Thổi sáo...).

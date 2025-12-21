---
trigger: always_on
---

ROLE: Bạn là một Senior Python Backend Engineer chuyên về phát triển Discord Bot sử dụng thư viện discord.py và aiosqlite. Nhiệm vụ của bạn là xây dựng (hoặc refactor) một bot game giải trí phức tạp tên là "Bên Hiên Nhà".

LANGUAGE: Bạn phải viết các logs, các comment bằng tiếng anh, còn giao diện game thuộc về phía người dùng nên buộc phải sử dụng ngôn ngữ tiếng việt. Còn các báo cáo bạn viết, buộc phải viết bằng tiếng việt, các thuật ngữ chuyên ngành giữ nguyên tiếng anh.

TƯ DUY CỐT LÕI (CORE PHILOSOPHY):

    Non-blocking I/O: Tuyệt đối không dùng code đồng bộ (blocking) trong các hàm async. Mọi tác vụ nặng (xử lý ảnh Pillow, request mạng) phải chạy trong run_in_executor.

    Data-Driven: Logic game (Python) phải tách biệt hoàn toàn với Dữ liệu game (JSON/Database). Cân bằng game bằng cách sửa JSON, không sửa code.

    Stateless & Persistence: Hạn chế lưu trạng thái game quan trọng trên RAM (self.variable). Phải có cơ chế lưu xuống SQLite hoặc File để bot restart không mất dữ liệu người chơi.

    Modular Architecture: Sử dụng Cogs để chia nhỏ tính năng. Không viết tất cả vào một file.

CẤU TRÚC DỰ ÁN (PROJECT STRUCTURE): Bạn phải tuân thủ cấu trúc thư mục này:
Plaintext

project/
├── configs/                 # CHỈ chứa cấu hình tĩnh
│   ├── settings.py          # TOKEN, PATHs, CONSTANTS
│   └── game_config.json     # ID Role, ID Channel (Map theo Server ID)
├── core/                    # Các module dùng chung (Core Engine)
│   ├── database.py          # Class DatabaseManager (Singleton, Connection Pool)
│   ├── achievement.py       # Hệ thống thành tựu tập trung
│   └── utils.py             # Hàm hỗ trợ (Format tiền, vẽ ảnh async)
├── data/                    # Dữ liệu JSON (Game Design)
│   ├── fishing/             # items.json, fish.json, events.json
│   └── werewolf/            # roles.json (nếu cần)
├── cogs/                    # Logic từng tính năng
│   ├── economy/             # shop.py, work.py
│   ├── fishing/             # engine.py, ui_views.py
│   ├── werewolf/            # engine.py, roles/, state.py (OOP nặng)
│   └── minigames/           # baucua.py, noitu.py
└── main.py                  # Entry point (chỉ load cogs và chạy)

QUY TẮC CODE (CODING STANDARDS):

    Quản lý Database:

        Không dùng get_db() rời rạc. Tạo class DatabaseManager quản lý connection pool.

        Sử dụng context manager (async with db.execute...) để đảm bảo đóng kết nối.

        Sử dụng Transaction (BEGIN...COMMIT) cho mọi giao dịch liên quan đến tiền tệ/item để tránh Race Condition (Dupe đồ).

    Xử lý Game Ma Sói (Werewolf):

        Sử dụng OOP & Polymorphism: Class Role là cha, các role con (Seer, Wolf) kế thừa và override hàm on_night, on_day.

        Không truy cập biến private (_variable) từ bên ngoài class. Sử dụng Getter/Setter hoặc Public Method.

        Tách biệt GameEngine (xử lý vòng lặp) và GameView (xử lý UI Discord).

    Hệ thống Achievement:

        Xây dựng AchievementManager tập trung.

        Các game con (Fishing, Werewolf) chỉ gọi check_unlock(user_id, 'stat_key'), không tự xử lý logic trao thưởng.

    Cấu hình (Decoupling):

        Không hardcode ID (Channel/Role) trong code Python.

        Lấy ID từ configs/game_config.json dựa trên guild_id.

QUY TRÌNH TRIỂN KHAI (WORKFLOW): Tôi sẽ yêu cầu bạn code từng module một. Với mỗi tính năng, bạn phải thực hiện theo quy trình:

    Phân tích: Giải thích ngắn gọn cách bạn sẽ code và database schema cần thiết.

    Coding: Viết code hoàn chỉnh, có Type Hinting và Docstring.

    Testing Checklist: Cung cấp danh sách các bước để tôi (người dùng) test tính năng đó thủ công (Vd: "Gõ lệnh A, sau đó tắt bot, bật lại xem tiền còn không").

BẮT ĐẦU: Hãy xác nhận bạn đã hiểu yêu cầu. Sau đó, hãy bắt đầu bằng việc thiết lập Module Core (configs, database.py) và file main.py chuẩn chỉnh trước.
🧠 PHÂN TÍCH CHI TIẾT: TẠI SAO LẠI VIẾT PROMPT NHƯ VẬY?

Tôi đã lồng ghép tất cả các vấn đề mà bot cũ của bạn gặp phải vào trong prompt này để "phòng bệnh hơn chữa bệnh".
1. Tại sao phải có "Tư duy cốt lõi"?

    Vấn đề cũ: Bot bị lag khi vẽ ảnh (blocking), mất dữ liệu khi restart (RAM state).

    Giải pháp trong prompt: Bắt buộc AI phải dùng run_in_executor cho việc vẽ ảnh và lưu dữ liệu xuống DB/File. AI sẽ tự động tránh dùng time.sleep hay urllib.

2. Cấu trúc thư mục (Architecture)

    Vấn đề cũ: File constants.py bị "circular import" (vòng lặp), logic lẫn lộn.

    Giải pháp: Tôi đã vẽ sẵn sơ đồ cho AI. Nó tách biệt configs (chỉ chứa biến) và core (chứa code xử lý). Điều này giúp code "sạch", dễ mở rộng.

3. Quy tắc code (Coding Standards)

    Vấn đề cũ: Dupe tiền (Race Condition), Hardcode ID role làm bot chết khi sang server khác.

    Giải pháp:

        Yêu cầu dùng Transaction: Đảm bảo tiền trừ xong mới cộng đồ.

        Yêu cầu Config JSON: Để ID role ra ngoài code.

4. Quy trình test (Testing Checklist)

    AI code xong thường có lỗi mà nó không biết.

    Yêu cầu AI viết ra "Checklist test" giúp bạn đóng vai QA (Tester). Bạn sẽ biết chính xác cần bấm gì để kiểm tra xem code có chạy đúng hay không.

🧪 VÍ DỤ: CÁCH AI SẼ TRẢ LỜI VÀ BẠN TEST (Sau khi gửi prompt trên)

Giả sử bạn bảo AI: "Hãy code module Database và Main.py trước."

AI sẽ trả lời (Ví dụ):

    Phân tích: Tôi sẽ tạo class DatabaseManager sử dụng aiosqlite. Tôi sẽ bật chế độ WAL để ghi dữ liệu nhanh hơn và tránh lock database.

    Code: (AI đưa code database.py và main.py)

    Testing Checklist (Bạn cần làm theo):

        [ ] Chạy python main.py. Bot phải online và in ra "Database connected".

        [ ] Thử tắt bot (Ctrl+C) và bật lại. Kiểm tra xem file data/database.db có được tạo ra không.

        [ ] Dùng lệnh !ping (nếu có) để xem độ trễ DB.

Giả sử bạn bảo AI: "Tiếp theo, hãy code module Fishing với tính năng vẽ ảnh profile."

AI sẽ trả lời:

    Lưu ý: Vì xử lý ảnh là tác vụ nặng, tôi sẽ viết hàm generate_image chạy trong executor để bot không bị đứng hình.

    Code: (AI đưa code fishing/ui.py có đoạn await loop.run_in_executor(...))

    Testing Checklist:

        [ ] Gõ lệnh /cauca.

        [ ] Ngay lập tức gõ lệnh /ping ở kênh khác.

        [ ] Kết quả mong đợi: Bot phải trả lời /ping NGAY LẬP TỨC dù ảnh câu cá chưa hiện ra xong. (Nếu bot đợi ảnh hiện xong mới rep ping -> Code sai, bắt AI sửa lại).
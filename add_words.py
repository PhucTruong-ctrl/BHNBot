import json
import os

TU_DIEN_PATH = "./data/tu_dien.txt"

def add_word_to_tu_dien(word: str):
    """Add word to tu_dien.txt file for persistence"""
    try:
        with open(TU_DIEN_PATH, "a", encoding="utf-8") as f:
            f.write(f'{{"text": "{word}", "source": ["user_added"]}}\n')
        print(f"[ADD_WORD] Added to tu_dien.txt: {word}")
    except Exception as e:
        print(f"[ADD_WORD] Error adding to tu_dien.txt: {e}")

# New words to add
new_words = {
"check": [
    "in",
    "out",
    "var",
    "map",
    "giá",
    "hàng"
  ],
  "book": [
    "vé",
    "lịch",
    "phòng",
    "xe",
    "bàn"
  ],
  "ship": [
    "hàng",
    "đồ",
    "per",
    "nhanh",
    "hoả"
  ],
  "fan": [
    "cứng",
    "cuồng",
    "guột",
    "page",
    "club"
  ],
  "anti": [
    "fan"
  ],
  "săn": [
    "sale",
    "mây",
    "đồ",
    "deal",
    "vé"
  ],
  "chốt": [
    "đơn",
    "kèo",
    "lời",
    "sổ",
    "hạ"
  ],
  "bùng": [
    "kèo",
    "hàng",
    "nổ",
    "lụa"
  ],
  "bom": [
    "hàng",
    "tấn",
    "xăng"
  ],
  "xả": [
    "kho",
    "hàng",
    "stress",
    "xuôi",
    "trận"
  ],
  "sống": [
    "ảo",
    "thật",
    "chất",
    "xanh",
    "sót"
  ],
  "câu": [
    "like",
    "view",
    "follow",
    "chuyện",
    "giờ"
  ],
  "bão": [
    "like",
    "đơn",
    "mạng",
    "giá"
  ],
  "thả": [
    "tim",
    "thính",
    "haha",
    "sad",
    "thương",
    "phẫn"
  ],
  "quẹt": [
    "thẻ",
    "phải",
    "trái",
    "tinder"
  ],
  "quét": [
    "qr",
    "mã",
    "vôi",
    "nhà"
  ],
  "chuyển": [
    "khoản",
    "đổi",
    "hướng",
    "nhượng"
  ],
  "tiền": [
    "ảo",
    "số",
    "điện",
    "mặt",
    "đô"
  ],
  "ví": [
    "điện",
    "momo",
    "zalo",
    "da",
    "tiền"
  ],
  "cà": [
    "khịa",
    "phê",
    "nhắc",
    "tưng",
    "muối"
  ],
  "gạ": [
    "kèo",
    "tình",
    "gẫm",
    "đòn"
  ],
  "bóc": [
    "phốt",
    "tem",
    "lịch",
    "bánh"
  ],
  "toang": [
    "hoác",
    "rồi",
    "luôn"
  ],
  "xu": [
    "cà",
    "hướng",
    "thế",
    "nịnh"
  ],
  "trẻ": [
    "trâu",
    "nghé",
    "ranh",
    "thơ"
  ],
  "anh": [
    "hùng",
    "phím",
    "trai",
    "em"
  ],
  "phím": [
    "cơ",
    "chiến",
    "hàng",
    "chuột"
  ],
  "leo": [
    "rank",
    "lề",
    "thang",
    "cây"
  ],
  "gánh": [
    "team",
    "tạ",
    "hàng",
    "vác"
  ],
  "full": [
    "top",
    "option",
    "hd",
    "size"
  ],
  "top": [
    "trending",
    "server",
    "một"
  ],
  "trà": [
    "sữa",
    "chanh",
    "tắc",
    "đào",
    "vải",
    "dâu",
    "bí",
    "xanh",
    "đen",
    "đá",
    "tấm",
    "mót"
  ],
  "bún": [
    "đậu",
    "mắm",
    "chả",
    "thịt",
    "nướng",
    "bò",
    "riêu",
    "ốc",
    "quậy"
  ],
  "bánh": [
    "tráng",
    "mì",
    "trộn",
    "nướng",
    "cuốn",
    "xèo",
    "khọt",
    "căn",
    "bèo",
    "lọc",
    "nậm",
    "gai",
    "ít",
    "pía",
    "đa",
    "đúc"
  ],
  "phô": [
    "mai",
    "trương",
    "diễn"
  ],
  "trân": [
    "châu",
    "trọng",
    "quý"
  ],
  "sương": [
    "sáo",
    "sâm",
    "mai",
    "mù"
  ],
  "tà": [
    "tưa",
    "tà",
    "dâm",
    "đạo"
  ],
  "siêu": [
    "to",
    "khổng",
    "phẩm",
    "xe",
    "nhân",
    "thị",
    "cấp"
  ],
  "lẩu": [
    "thái",
    "nấm",
    "dê",
    "bò",
    "gà",
    "cá",
    "mắm",
    "riêu",
    "hải",
    "sản"
  ],
  "nướng": [
    "ngói",
    "mọi",
    "lu",
    "giấy",
    "bạc",
    "bơ",
    "mỡ",
    "hành"
  ],
  "chân": [
    "gà",
    "ái",
    "lý",
    "trời",
    "tình",
    "dung"
  ],
  "cánh": [
    "gà",
    "cụt",
    "tay",
    "chim",
    "buồm"
  ],
  "nem": [
    "chua",
    "nướng",
    "lụi",
    "rán",
    "cuốn"
  ],
  "gỏi": [
    "cuốn",
    "khô",
    "bò",
    "gà",
    "cá",
    "xoài",
    "đu"
  ],
  "xoài": [
    "lắc",
    "chấm",
    "xanh",
    "tượng",
    "cát"
  ],
  "cóc": [
    "lắc",
    "bao",
    "tử",
    "ghẻ",
    "nhái"
  ],
  "me": [
    "đá",
    "ngâm",
    "chua",
    "tây"
  ],
  "mận": [
    "hà",
    "nội",
    "cơm",
    "đỏ"
  ],
  "ảo": [
    "tưởng",
    "giác",
    "ảnh",
    "thuật",
    "mộng",
    "lòi",
    "ma"
  ],
  "ngáo": [
    "đá",
    "ngơ",
    "ộp",
    "nháo"
  ],
  "gắt": [
    "gỏng",
    "củ",
    "kiệu",
    "gao"
  ],
  "trầm": [
    "cảm",
    "hương",
    "trọng",
    "lắng",
    "mặc"
  ],
  "tự": [
    "kỷ",
    "sướng",
    "tin",
    "trọng",
    "giác",
    "tử",
    "do"
  ],
  "khởi": [
    "nghiệp",
    "động",
    "sắc",
    "tố",
    "nguyên"
  ],
  "kết": [
    "nối",
    "bạn",
    "hôn",
    "thúc",
    "cấu",
    "tinh"
  ],
  "chia": [
    "sẻ",
    "tay",
    "li",
    "rẽ",
    "chác"
  ],
  "cảm": [
    "nắng",
    "lạnh",
    "xúc",
    "giác",
    "thấy"
  ],
  "áp": [
    "lực",
    "đảo",
    "dụng",
    "chế",
    "tải"
  ],
  "tải": [
    "trọng",
    "app",
    "game",
    "về",
    "lên"
  ],
  "đăng": [
    "xuất",
    "nhập",
    "ký",
    "tải",
    "quang",
    "cai"
  ],
  "deadline": [
    "dí",
    "ngập",
    "gấp",
    "trễ"
  ],
  "chạy": [
    "số",
    "deadline",
    "ads",
    "việc",
    "án",
    "bàn",
    "pin"
  ],
  "nhảy": [
    "việc",
    "số",
    "cóc",
    "dù",
    "múa",
    "cầu"
  ],
  "dự": [
    "án",
    "thảo",
    "đoán",
    "báo",
    "tính",
    "phòng"
  ],
  "hợp": [
    "đồng",
    "tác",
    "lý",
    "tình",
    "thức",
    "cạ"
  ],
  "phỏng": [
    "vấn",
    "đoán",
    "dựng"
  ],
  "thất": [
    "nghiệp",
    "bại",
    "thu",
    "tình",
    "bát",
    "lạc",
    "vọng"
  ],
  "tăng": [
    "ca",
    "lương",
    "trưởng",
    "tốc",
    "cường",
    "động"
  ],
  "giảm": [
    "biên",
    "chế",
    "cân",
    "tải",
    "sóc",
    "giá"
  ],
  "đầu": [
    "tư",
    "cơ",
    "nậu",
    "têu",
    "tàu",
    "gấu"
  ],
  "chứng": [
    "khoán",
    "chỉ",
    "cớ",
    "nhận",
    "tỏ"
  ],
  "cổ": [
    "phiếu",
    "đông",
    "cồn",
    "cánh",
    "tích",
    "đại"
  ],
  "thanh": [
    "khoản",
    "toán",
    "lý",
    "trừng",
    "lọc",
    "niên"
  ],
  "giải": [
    "ngân",
    "trình",
    "quyết",
    "tỏa",
    "ngố",
    "trí"
  ],
  "đáo": [
    "hạn",
    "để",
    "tụng"
  ],
  "vay": [
    "vốn",
    "nóng",
    "lãi",
    "mượn"
  ],
  "nợ": [
    "xấu",
    "công",
    "nần",
    "đọng",
    "duyên"
  ],
  "lãi": [
    "suất",
    "kép",
    "ròng",
    "nhãi",
    "lời"
  ],
  "báo": [
    "cáo",
    "giá",
    "động",
    "thức",
    "chốt",
    "cô",
    "hiếu"
  ],
  "cắm": [
    "sừng",
    "trại",
    "chốt",
    "cọc",
    "rễ",
    "đầu"
  ],
  "đổ": [
    "vỏ",
    "bê",
    "nát",
    "đốn",
    "thừa",
    "bộ"
  ],
  "tiểu": [
    "tam",
    "thư",
    "nhân",
    "xảo",
    "học",
    "tiên"
  ],
  "chính": [
    "thất",
    "chuyên",
    "trực",
    "xác",
    "đáng"
  ],
  "phi": [
    "công",
    "hành",
    "vụ",
    "pháp",
    "thường",
    "tần"
  ],
  "máy": [
    "bay",
    "móc",
    "lạnh",
    "bơm",
    "chém"
  ],
  "nóc": [
    "nhà",
    "tủ",
    "hầm"
  ],
  "bạch": [
    "liên",
    "nguyệt",
    "kim",
    "tạng",
    "cầu",
    "đằng"
  ],
  "lật": [
    "mặt",
    "kèo",
    "bàn",
    "đật",
    "tẩy",
    "ngửa"
  ],
  "quay": [
    "xe",
    "lưng",
    "phim",
    "cuồng",
    "vòng",
    "tắt"
  ],
  "giả": [
    "trân",
    "tạo",
    "dối",
    "vờ",
    "nai",
    "danh",
    "định"
  ],
  "cẩu": [
    "lương",
    "thả",
    "xập"
  ],
  "cơm": [
    "chó",
    "tró",
    "nhà",
    "bụi",
    "hộp",
    "tấm",
    "lam"
  ],
  "tương": [
    "tác",
    "tư",
    "lai",
    "thích",
    "đồng",
    "khắc",
    "bần"
  ],
  "bơ": [
    "đẹp",
    "nhau",
    "vơ",
    "lác"
  ],
  "lờ": [
    "đi",
    "tịt",
    "đờ"
  ],
  "người": [
    "lạ",
    "cũ",
    "dưng",
    "âm",
    "nhện",
    "mẫu"
  ],
  "hack": [
    "tuổi",
    "dáng",
    "não",
    "game"
  ],
  "bắt": [
    "trend",
    "sóng",
    "bẻ",
    "kèo",
    "lỗi"
  ],
  "đu": [
    "idol",
    "trend",
    "dây",
    "đưa",
    "bám"
  ],
  "tấm": [
    "chiếu",
    "lòng",
    "thân",
    "cám",
    "mẳn"
  ],
  "luật": [
    "hoa",
    "sư",
    "pháp",
    "lệ",
    "rừng",
    "nhân"
  ],
  "nghiệp": [
    "quật",
    "vụ",
    "chướng",
    "dư",
    "tụ"
  ],
  "gáy": [
    "to",
    "sớm",
    "bẩn",
    "ngọ"
  ],
  "khẩu": [
    "chiến",
    "nghiệp",
    "trang",
    "hiệu",
    "cung",
    "độ"
  ],
  "hóng": [
    "biến",
    "hớt",
    "gió",
    "chuyện"
  ],
  "phốt": [
    "to",
    "nhỏ"
  ],
  "trò": [
    "đùa",
    "cười",
    "trống",
    "chơi",
    "mèo"
  ],
  "tấu": [
    "hài",
    "sớ",
    "khúc"
  ],
  "diễn": [
    "sâu",
    "giả",
    "viên",
    "biến",
    "thuyết"
  ],
  "chiếm": [
    "sóng",
    "đoạt",
    "hữu",
    "đóng"
  ],
  "lên": [
    "xu",
    "thớt",
    "hương",
    "đồ",
    "lớp",
    "mặt"
  ],
  "xuống": [
    "lỗ",
    "xác",
    "nước",
    "cấp",
    "tay"
  ],
  "bay": [
    "màu",
    "lắc",
    "phòng",
    "nhảy"
  ],
  "mất": [
    "gốc",
    "nết",
    "mạng",
    "mặt",
    "lượt",
    "ngủ"
  ],
  "xỉu": [
    "ngang",
    "up",
    "down"
  ],
  "còn": [
    "cái",
    "nịt",
    "thở",
    "nguyên"
  ],
  "cách": [
    "ly",
    "biệt",
    "trở",
    "lòng",
    "điệu",
    "tân",
    "mạng"
  ],
  "xét": [
    "nghiệm",
    "duyệt",
    "nét",
    "hỏi",
    "xử",
    "soi"
  ],
  "khẩu": [
    "trang",
    "hiệu",
    "ngữ",
    "khí",
    "phần",
    "vị"
  ],
  "dương": [
    "tính",
    "lịch",
    "cầm",
    "liễu",
    "quang",
    "gian"
  ],
  "âm": [
    "tính",
    "lịch",
    "nhạc",
    "thầm",
    "mưu",
    "hộ",
    "ti"
  ],
  "tiêm": [
    "chủng",
    "phòng",
    "kích",
    "thuốc",
    "má"
  ],
  "dao": [
    "kéo",
    "động",
    "búa",
    "sắc",
    "găm",
    "dịch"
  ],
  "thẩm": [
    "mỹ",
    "quyền",
    "phán",
    "định",
    "thấu",
    "du"
  ],
  "phẫu": [
    "thuật",
    "diện"
  ],
  "liệu": [
    "trình",
    "pháp",
    "cơm",
    "lĩnh",
    "hồn"
  ],
  "spa": [
    "thú",
    "mẹ",
    "bé"
  ],
  "giãn": [
    "cách",
    "cơ",
    "nở",
    "dòng"
  ],
  "f": [
    "không",
    "một",
    "a"
  ],
  "khám": [
    "phá",
    "nghiệm",
    "xét",
    "bệnh",
    "thờ"
  ],
  "học": [
    "bạ",
    "kỳ",
    "phần",
    "lại",
    "bổng",
    "đường",
    "trưởng",
    "thuyết",
    "hỏi"
  ],
  "tín": [
    "chỉ",
    "dụng",
    "nhiệm",
    "ngưỡng",
    "hiệu",
    "chấp"
  ],
  "thi": [
    "lại",
    "rớt",
    "đậu",
    "thố",
    "hành",
    "đua",
    "công"
  ],
  "trượt": [
    "môn",
    "vỏ",
    "giá",
    "tuyết",
    "chân",
    "dài"
  ],
  "bảo": [
    "lưu",
    "vệ",
    "kê",
    "bối",
    "hiểm",
    "đảm",
    "mật"
  ],
  "luận": [
    "văn",
    "án",
    "điểm",
    "bàn",
    "tội",
    "lý"
  ],
  "đúp": [
    "lớp",
    "bê"
  ],
  "hạnh": [
    "kiểm",
    "phúc",
    "ngộ",
    "diện"
  ],
  "tốt": [
    "nghiệp",
    "bụng",
    "lành",
    "đẹp",
    "số",
    "ngày"
  ],
  "chuyên": [
    "cần",
    "đề",
    "ngành",
    "môn",
    "sâu",
    "chở",
    "tu"
  ],
  "dạy": [
    "thêm",
    "kèm",
    "bảo",
    "dỗ",
    "nghề",
    "đời"
  ],
  "soạn": [
    "bài",
    "thảo",
    "giả"
  ],
  "điểm": [
    "danh",
    "số",
    "chuẩn",
    "sàn",
    "tựa",
    "tâm",
    "hẹn"
  ],
  "tan": [
    "trường",
    "ca",
    "học",
    "nát",
    "tành",
    "chảy",
    "biến"
  ],
  "phượt": [
    "thủ",
    "bụi",
    "gia"
  ],
  "du": [
    "lịch",
    "hí",
    "khách",
    "canh",
    "nhập",
    "côn",
    "ngoạn"
  ],
  "nghỉ": [
    "dưỡng",
    "mát",
    "phép",
    "hưu",
    "lễ",
    "ngơi",
    "việc"
  ],
  "check": [
    "in",
    "out",
    "list"
  ],
  "homestay": [
    "đẹp",
    "rẻ"
  ],
  "resort": [
    "biển",
    "núi"
  ],
  "đà": [
    "lạt",
    "nẵng",
    "điểu",
    "đao"
  ],
  "hạ": [
    "long",
    "tầng",
    "cánh",
    "hỏa",
    "bệ",
    "màn",
    "gục"
  ],
  "vũng": [
    "tàu",
    "lầy",
    "nước",
    "trâu",
    "áng"
  ],
  "phú": [
    "quốc",
    "quý",
    "yên",
    "thọ",
    "hào",
    "ông",
    "bà"
  ],
  "cần": [
    "thơ",
    "giờ",
    "lao",
    "cù",
    "thiết",
    "trục",
    "câu"
  ],
  "nha": [
    "trang",
    "khoa",
    "chu",
    "sĩ",
    "môn"
  ],
  "hội": [
    "an",
    "nghị",
    "họp",
    "nhập",
    "tụ",
    "chợ",
    "hè"
  ],
  "sài": [
    "gòn",
    "đẹn",
    "khao"
  ],
  "hà": [
    "nội",
    "giang",
    "tĩnh",
    "nam",
    "bá",
    "khắc",
    "hơi"
  ],
  "tây": [
    "ninh",
    "nguyên",
    "bắc",
    "nam",
    "thiên",
    "du"
  ],
  "tam": [
    "đảo",
    "giác",
    "quốc",
    "tai",
    "cấp",
    "thế"
  ],
  "biển": [
    "đảo",
    "khơi",
    "cả",
    "hồ",
    "thước",
    "lận"
  ],
  "rừng": [
    "rú",
    "xanh",
    "già",
    "thiêng",
    "cấm"
  ],
  "nồi": [
    "cơm",
    "áp",
    "chiên",
    "lẩu",
    "đất",
    "hơi",
    "da",
    "niêu"
  ],
  "chảo": [
    "chống",
    "dính",
    "lửa",
    "chớp",
    "gang"
  ],
  "bát": [
    "đĩa",
    "đũa",
    "hương",
    "ngát",
    "phố",
    "nháo",
    "âm",
    "quái"
  ],
  "đũa": [
    "thần",
    "mốc",
    "lệch",
    "cả",
    "son"
  ],
  "chiếu": [
    "trúc",
    "manh",
    "cói",
    "trải",
    "tướng",
    "lệ",
    "phim",
    "bóng"
  ],
  "chăn": [
    "ga",
    "gối",
    "đệm",
    "bông",
    "nuôi",
    "dắt",
    "trâu",
    "ấm"
  ],
  "màn": [
    "hình",
    "thầu",
    "gió",
    "trời",
    "đêm",
    "kịch",
    "ảnh",
    "nhung"
  ],
  "gối": [
    "đầu",
    "ôm",
    "sóng",
    "lưng",
    "mộng",
    "vụ",
    "kê"
  ],
  "kệ": [
    "sách",
    "tủ",
    "xác",
    "nệ",
    "chúng",
    "đời"
  ],
  "bếp": [
    "từ",
    "ga",
    "núc",
    "trưởng",
    "lửa",
    "hồng",
    "hoàng"
  ],
  "khăn": [
    "tắm",
    "mặt",
    "trải",
    "giấy",
    "quàng",
    "gói",
    "áo",
    "tang"
  ],
  "thảm": [
    "trải",
    "đỏ",
    "họa",
    "khốc",
    "sát",
    "bại",
    "thương"
  ],
  "gương": [
    "soi",
    "mặt",
    "cầu",
    "mẫu",
    "chiếu",
    "lược",
    "kính"
  ],
  "vui": [
    "vẻ",
    "mừng",
    "sướng",
    "tươi",
    "nhộn",
    "tính",
    "mắt",
    "tai"
  ],
  "buồn": [
    "bã",
    "rầu",
    "thiu",
    "ngủ",
    "cười",
    "nôn",
    "tình",
    "phiền"
  ],
  "giận": [
    "dỗi",
    "hờn",
    "cá",
    "tím",
    "lẫy",
    "dữ"
  ],
  "hờn": [
    "dỗi",
    "ghen",
    "mát",
    "tủi",
    "trách"
  ],
  "lo": [
    "lắng",
    "âu",
    "sợ",
    "liệu",
    "toan",
    "nghĩ",
    "lót",
    "xa"
  ],
  "sợ": [
    "sệt",
    "hãi",
    "ma",
    "sấm",
    "cám",
    "chết",
    "xanh"
  ],
  "ngại": [
    "ngùng",
    "ngần",
    "miệng",
    "khó",
    "vật",
    "ngùng"
  ],
  "chán": [
    "nản",
    "chường",
    "phèo",
    "ngắt",
    "đời",
    "chê",
    "ngấy"
  ],
  "mệt": [
    "mỏi",
    "nhoài",
    "lử",
    "rã",
    "nhọc",
    "xỉu",
    "nghỉ"
  ],
  "lười": [
    "biếng",
    "nhác",
    "nhát",
    "chảy",
    "lĩnh"
  ],
  "siêng": [
    "năng"
  ],
  "chăm": [
    "chỉ",
    "sóc",
    "bẵm",
    "chút",
    "chắm",
    "học",
    "làm"
  ],
  "khôn": [
    "lỏi",
    "ngoan",
    "lớn",
    "khéo",
    "nhà",
    "dại",
    "hồn"
  ],
  "dại": [
    "dột",
    "khờ",
    "trai",
    "gái",
    "khôn",
    "miệng"
  ],
  "ngoằn": [
    "ngoèo"
  ],
  "khúc": [
    "khuỷu",
    "khích",
    "mắc",
    "xạ",
    "chiết",
    "ca",
    "hát",
    "gỗ"
  ],
  "khuỷu": [
    "tay"
  ],
  "lấp": [
    "liếm",
    "lánh",
    "lửng",
    "loáng",
    "đầy",
    "ló",
    "vùi"
  ],
  "bâng": [
    "khuâng",
    "quơ"
  ],
  "chập": [
    "choạng",
    "chững",
    "cheng",
    "chờn",
    "mạch",
    "tối"
  ],
  "đỏng": [
    "đảnh"
  ],
  "thấp": [
    "thoáng",
    "thỏm",
    "bé",
    "kém",
    "hèn",
    "cơ",
    "khớp"
  ],
  "lom": [
    "khom",
    "dom"
  ],
  "lổm": [
    "ngổm"
  ],
  "lồm": [
    "cồm"
  ],
  "nhấp": [
    "nhô",
    "nhổm",
    "nháy",
    "nhá",
    "môi"
  ],
  "thơm": [
    "tho",
    "phức",
    "lừng",
    "ngát",
    "lây",
    "ngon"
  ],
  "hôi": [
    "nách",
    "hám",
    "thối",
    "của",
    "bia",
    "miệng"
  ],
  "thối": [
    "tha",
    "nát",
    "rữa",
    "hoắc",
    "tiền",
    "chí",
    "tai"
  ],
  "nhão": [
    "nhoét",
    "nhẹt"
  ],
  "nhầy": [
    "nhụa"
  ],
  "cá": [
    "sấu",
    "mập",
    "voi",
    "heo",
    "chép",
    "rô",
    "lóc",
    "trê",
    "tra",
    "ngừ",
    "thu",
    "cơm",
    "nục",
    "cược",
    "độ",
    "biệt",
    "nhân",
    "tính",
    "tháng"
  ],
  "chim": [
    "sẻ",
    "sâu",
    "chích",
    "bồ",
    "câu",
    "én",
    "yến",
    "ưng",
    "cụt",
    "lợn",
    "chóc",
    "chuột",
    "mồi",
    "bao"
  ],
  "chó": [
    "mực",
    "vàng",
    "đốm",
    "phốc",
    "cỏ",
    "sói",
    "nghiệp",
    "má",
    "săn",
    "chết",
    "ngáp"
  ],
  "mèo": [
    "mướp",
    "tam",
    "đen",
    "hoang",
    "rừng",
    "mả",
    "cào",
    "già"
  ],
  "hổ": [
    "mang",
    "báo",
    "cốt",
    "phách",
    "lửa",
    "thẹn",
    "tướng",
    "dữ",
    "đói"
  ],
  "bò": [
    "tót",
    "sữa",
    "sát",
    "cạp",
    "húc",
    "đội",
    "né",
    "lăn",
    "lê",
    "cười"
  ],
  "gà": [
    "trống",
    "mái",
    "nòi",
    "chọi",
    "tây",
    "ta",
    "ác",
    "đồng",
    "mờ",
    "gật",
    "công",
    "nghiệp",
    "rù"
  ],
  "khỉ": [
    "gió",
    "khô",
    "ho",
    "đột",
    "thật"
  ],
  "ngựa": [
    "vằn",
    "ô",
    "thồ",
    "đua",
    "non",
    "chứng",
    "người",
    "xe"
  ],
  "trâu": [
    "bò",
    "nước",
    "mộng",
    "cày",
    "chấu",
    "giật",
    "chậm"
  ],
  "voi": [
    "ma",
    "rừng",
    "bản",
    "giày"
  ],
  "chuột": [
    "đồng",
    "cống",
    "túi",
    "bạch",
    "rút",
    "lắt",
    "sa",
    "quang",
    "nhắt"
  ],
  "mưa": [
    "rào",
    "phùn",
    "dầm",
    "đá",
    "lũ",
    "ngâu",
    "móc",
    "sa",
    "bão",
    "giông",
    "tuôn",
    "rơi",
    "bay"
  ],
  "gió": [
    "mùa",
    "bấc",
    "lào",
    "heo",
    "máy",
    "lốc",
    "chướng",
    "nồm",
    "thổi",
    "chiều",
    "trăng",
    "bụi"
  ],
  "bão": [
    "táp",
    "bùng",
    "tố",
    "giá",
    "lụt",
    "mạng",
    "cát",
    "đạn"
  ],
  "nắng": [
    "nôi",
    "chói",
    "chang",
    "gắt",
    "lửa",
    "hạ",
    "quái",
    "cực",
    "chiều",
    "sớm"
  ],
  "sấm": [
    "sét",
    "chớp",
    "rền",
    "động",
    "truyền",
    "trạng"
  ],
  "núi": [
    "non",
    "cao",
    "đồi",
    "lửa",
    "rừng",
    "đá",
    "sông",
    "đôi"
  ],
  "sông": [
    "hồ",
    "ngòi",
    "suối",
    "nước",
    "cầu",
    "núi",
    "đà",
    "hồng",
    "hương",
    "cửu"
  ],
  "biển": [
    "cả",
    "đông",
    "hồ",
    "khơi",
    "đảo",
    "lận",
    "thủ",
    "báo",
    "hiệu",
    "số"
  ],
  "trăng": [
    "sao",
    "non",
    "tròn",
    "khuyết",
    "lưỡi",
    "liềm",
    "mật",
    "hoa",
    "gió"
  ],
  "sao": [
    "hỏa",
    "kim",
    "chổi",
    "băng",
    "biển",
    "chép",
    "y",
    "đâu",
    "vậy",
    "nhãng"
  ],
  "đất": [
    "đai",
    "cát",
    "đá",
    "nước",
    "trời",
    "khách",
    "lành",
    "mẹ",
    "hứa"
  ],
  "trời": [
    "đất",
    "cao",
    "xanh",
    "mây",
    "phú",
    "cho",
    "sinh",
    "ơi"
  ],
  "đấm": [
    "đá",
    "bốc",
    "lưng",
    "mõm",
    "ngực",
    "phát",
    "cú"
  ],
  "đá": [
    "bóng",
    "cầu",
    "gà",
    "đểu",
    "xoáy",
    "quý",
    "lửa",
    "tảng",
    "hoa",
    "mài",
    "thúng"
  ],
  "chạy": [
    "bộ",
    "đua",
    "trốn",
    "thoát",
    "án",
    "chọt",
    "vạy",
    "làng",
    "giặc",
    "pin",
    "chương"
  ],
  "nhảy": [
    "dây",
    "cóc",
    "dù",
    "múa",
    "nhót",
    "lầu",
    "cầu",
    "bậc",
    "việc",
    "dựng",
    "ổ"
  ],
  "bơi": [
    "lội",
    "sải",
    "ngửa",
    "bướm",
    "ếch",
    "chải",
    "xuồng",
    "thuyền"
  ],
  "cười": [
    "đùa",
    "cợt",
    "duyên",
    "trừ",
    "gượng",
    "khẩy",
    "bò",
    "lăn",
    "lóc",
    "nụ",
    "vỡ"
  ],
  "khóc": [
    "lóc",
    "thét",
    "than",
    "ròng",
    "mướt",
    "thầm",
    "nhè",
    "thuê",
    "òa"
  ],
  "hát": [
    "hò",
    "ca",
    "xướng",
    "rong",
    "dạo",
    "hay",
    "chèo",
    "bội"
  ],
  "múa": [
    "may",
    "lân",
    "rối",
    "bụng",
    "cột",
    "lửa",
    "rìu",
    "tay"
  ],
  "vẽ": [
    "tranh",
    "vời",
    "chuyện",
    "đường",
    "bùa",
    "hình"
  ],
  "viết": [
    "lách",
    "bài",
    "tay",
    "thư",
    "báo",
    "văn",
    "tắt",
    "hoa"
  ],
  "đọc": [
    "sách",
    "báo",
    "hiểu",
    "lệnh",
    "vị",
    "thầm",
    "nhẩm"
  ],
  "nghe": [
    "ngóng",
    "nhìn",
    "lén",
    "thấy",
    "lời",
    "đồn",
    "nhạc"
  ],
  "xanh": [
    "lá",
    "dương",
    "da",
    "trời",
    "lè",
    "xao",
    "rờn",
    "biếc",
    "ngắt",
    "mượt",
    "non",
    "mặt",
    "cỏ",
    "chín"
  ],
  "đỏ": [
    "tươi",
    "thắm",
    "rực",
    "chót",
    "hỏn",
    "lòm",
    "đen",
    "mặt",
    "lửa",
    "âu",
    "đỏng",
    "đảnh"
  ],
  "vàng": [
    "ươm",
    "khè",
    "anh",
    "son",
    "mã",
    "tâm",
    "ngọc",
    "hương",
    "khe"
  ],
  "trắng": [
    "tinh",
    "bóc",
    "phau",
    "xóa",
    "tay",
    "án",
    "trẻo",
    "bệch",
    "lốp"
  ],
  "đen": [
    "sì",
    "thui",
    "đủi",
    "tối",
    "bạc",
    "ngòm",
    "nhẻm",
    "đúa"
  ],
  "tím": [
    "lịm",
    "ngắt",
    "than",
    "mộng",
    "mơ",
    "tái",
    "bầm"
  ],
  "hồng": [
    "hào",
    "nhan",
    "ngoại",
    "phúc",
    "hoang",
    "thủy",
    "cầu",
    "tâm"
  ],
  "nghệ": [
    "thuật",
    "nhân",
    "danh",
    "sĩ",
    "tinh",
    "an"
  ],
  "tranh": [
    "ảnh",
    "vẽ",
    "chấp",
    "đấu",
    "giành",
    "cử",
    "cãi",
    "luận",
    "thủ",
    "bá"
  ],
  "cây": [
    "cối",
    "xanh",
    "đa",
    "đề",
    "cảnh",
    "xăng",
    "số",
    "viết",
    "gậy",
    "trồng",
    "ngay"
  ],
  "hoa": [
    "hồng",
    "huệ",
    "lan",
    "cúc",
    "sen",
    "súng",
    "nhài",
    "hậu",
    "khôi",
    "lệ",
    "mắt",
    "tay",
    "giấy",
    "đá"
  ],
  "lá": [
    "lốt",
    "cờ",
    "cải",
    "chắn",
    "lách",
    "gan",
    "phổi",
    "thư",
    "phiếu",
    "bài",
    "đa",
    "ngón"
  ],
  "quả": [
    "báo",
    "đất",
    "bom",
    "tạ",
    "cam",
    "đấm",
    "tang",
    "quyết",
    "cảm",
    "lắc",
    "bóng"
  ],
  "trái": [
    "cây",
    "tim",
    "phải",
    "ngang",
    "phép",
    "đất",
    "khoáy",
    "phiếu",
    "chủ"
  ],
  "sen": [
    "đá",
    "hồng",
    "trắng",
    "bách",
    "đầm",
    "vòi",
    "tắm",
    "cạn"
  ],
  "trúc": [
    "xinh",
    "quân",
    "trắc",
    "bạch",
    "đào",
    "chỉ"
  ],
  "mai": [
    "vàng",
    "mối",
    "sau",
    "phục",
    "táng",
    "một",
    "mái",
    "dịch"
  ],
  "ngày": [
    "tháng",
    "giờ",
    "xưa",
    "nay",
    "mai",
    "kia",
    "công",
    "lễ",
    "nghỉ",
    "đêm",
    "mốt",
    "xửa"
  ],
  "tháng": [
    "năm",
    "chạp",
    "giêng",
    "đẻ",
    "tám",
    "củ",
    "mật",
    "ngày"
  ],
  "năm": [
    "tháng",
    "xưa",
    "ngoái",
    "học",
    "mới",
    "cũ",
    "sinh",
    "cam",
    "canh"
  ],
  "giờ": [
    "giấc",
    "dây",
    "cao",
    "g",
    "phút",
    "thiêng",
    "hồn",
    "trò",
    "địa"
  ],
  "phút": [
    "chốc",
    "giây",
    "mốt",
    "cuối",
    "bù",
    "trình"
  ],
  "cân": [
    "não",
    "bằng",
    "đối",
    "xứng",
    "nhắc",
    "đai",
    "tiểu",
    "kí",
    "thận",
    "sức"
  ],
  "thước": [
    "kẻ",
    "đo",
    "bảng",
    "tấc",
    "ngắm",
    "phim",
    "tha"
  ],
  "lạng": [
    "lách",
    "ta",
    "vàng",
    "thịt"
  ],
  "lít": [
    "nhít",
    "đít"
  ],
  "mét": [
    "vuông",
    "khối",
    "tây"
  ],
  "ma": [
    "quỷ",
    "ma",
    "trơi",
    "cà",
    "mãnh",
    "sát",
    "mị",
    "thuật",
    "túy",
    "đạo",
    "chơi",
    "kết",
    "da"
  ],
  "quỷ": [
    "sứ",
    "quyệt",
    "dữ",
    "thần",
    "khóc",
    "ám",
    "kế",
    "vương",
    "dạ",
    "cốc"
  ],
  "thần": [
    "tiên",
    "thánh",
    "tượng",
    "kinh",
    "bí",
    "dược",
    "chú",
    "thông",
    "tốc",
    "bài",
    "khí",
    "sắc"
  ],
  "thánh": [
    "thần",
    "chỉ",
    "thiện",
    "chiến",
    "ca",
    "giá",
    "sống",
    "nữ",
    "mẫu"
  ],
  "phật": [
    "tổ",
    "giáo",
    "đài",
    "tử",
    "lòng",
    "ý",
    "thủ",
    "pháp"
  ],
  "chùa": [
    "chiền",
    "bà",
    "hương",
    "thầy",
    "một",
    "cột",
    "ăn"
  ],
  "hương": [
    "khói",
    "thơm",
    "hoa",
    "vị",
    "sắc",
    "đồng",
    "hỏa",
    "lửa",
    "tóc"
  ],
  "âm": [
    "dương",
    "phủ",
    "ti",
    "hồn",
    "mưu",
    "lịch",
    "thầm",
    "vang",
    "sắc",
    "thanh"
  ],
  "hồn": [
    "ma",
    "vía",
    "nhiên",
    "hậu",
    "phách",
    "xiêu",
    "bay",
    "thơ"
  ],
  "vía": [
    "hè",
    "bà",
    "ông",
    "thần",
    "nặng",
    "nhẹ"
  ],
  "cúng": [
    "bái",
    "dường",
    "tế",
    "cụ",
    "viếng",
    "cùi"
  ],
  "bói": [
    "toán",
    "cá",
    "ra",
    "xem",
    "quẻ"
  ],
  "đàn": [
    "ông",
    "bà",
    "bầu",
    "tranh",
    "nhị",
    "áp",
    "hồi",
    "ca",
    "em",
    "anh",
    "gảy",
    "chim"
  ],
  "sáo": [
    "rỗng",
    "trúc",
    "ngữ",
    "trộn",
    "xào",
    "diều"
  ],
  "trống": [
    "cơm",
    "trơn",
    "rỗng",
    "đánh",
    "dong",
    "mái",
    "trải",
    "lảng",
    "ngực"
  ],
  "kèn": [
    "trống",
    "cựa",
    "cò",
    "tây",
    "hồng",
    "thổi"
  ],
  "nhạc": [
    "cụ",
    "sĩ",
    "viện",
    "kịch",
    "dạo",
    "trưởng",
    "hoa",
    "chế",
    "vàng",
    "trẻ",
    "đỏ"
  ],
  "ca": [
    "sĩ",
    "hát",
    "kịch",
    "trù",
    "dao",
    "tụng",
    "thán",
    "cẩm",
    "mổ"
  ],
  "phách": [
    "lạc",
    "lối",
    "nhịp",
    "làm"
  ],
  "nhịp": [
    "điệu",
    "nhàng",
    "cầu",
    "tim",
    "đập",
    "phách",
    "sống"
  ],
  "lời": [
    "bài",
    "ca",
    "nói",
    "lãi",
    "hứa",
    "thề",
    "giải",
    "khuyên",
    "nguyền"
  ],
  "giai": [
    "điệu",
    "nhân",
    "cấp",
    "đoạn",
    "phẩm",
    "thoại",
    "gái"
  ],
  "súng": [
    "ống",
    "lục",
    "trường",
    "đạn",
    "kíp",
    "hơi",
    "nước",
    "sơn",
    "phun"
  ],
  "đạn": [
    "dược",
    "đạo",
    "pháo",
    "lửa",
    "bọc",
    "lạc"
  ],
  "bom": [
    "mìn",
    "đạn",
    "tấn",
    "thư",
    "hàng",
    "xăng",
    "nguyên"
  ],
  "mìn": [
    "bẫy",
    "nổ"
  ],
  "pháo": [
    "binh",
    "thủ",
    "hoa",
    "bông",
    "kích",
    "đài",
    "cối",
    "hôi",
    "sáng",
    "giàn"
  ],
  "chiến": [
    "tranh",
    "đấu",
    "sĩ",
    "thuật",
    "lược",
    "dịch",
    "trường",
    "công",
    "thắng",
    "hạm",
    "bào"
  ],
  "đấu": [
    "tranh",
    "đá",
    "thầu",
    "giá",
    "sĩ",
    "trường",
    "võ",
    "trí",
    "khẩu",
    "tố"
  ],
  "binh": [
    "lính",
    "sĩ",
    "đoàn",
    "chủng",
    "pháp",
    "bất",
    "biến",
    "thường",
    "vực",
    "tôm"
  ],
  "tướng": [
    "tá",
    "lĩnh",
    "sĩ",
    "số",
    "mạo",
    "cướp",
    "quân"
  ],
  "lính": [
    "tráng",
    "thủy",
    "đánh",
    "bắn",
    "lác",
    "canh",
    "ngự"
  ],
  "quân": [
    "đội",
    "sự",
    "nhân",
    "sư",
    "tử",
    "khu",
    "hàm",
    "chủ",
    "cờ",
    "quần"
  ],
  "hạm": [
    "đội",
    "tàu",
    "trưởng"
  ],
  "xe": [
    "tăng",
    "bọc",
    "thép",
    "pháo",
    "tải",
    "khách",
    "đạp",
    "máy",
    "ôm",
    "hoa",
    "tang",
    "cộ",
    "hơi"
  ],
  "luật": [
    "sư",
    "pháp",
    "lệ",
    "rừng",
    "gia",
    "học",
    "định",
    "khoa",
    "tạng",
    "hành"
  ],
  "pháp": [
    "luật",
    "lý",
    "chế",
    "đình",
    "sư",
    "danh",
    "nhân",
    "trường",
    "thuật",
    "lệnh",
    "quyền"
  ],
  "kiện": [
    "tụng",
    "cáo",
    "toàn",
    "tướng",
    "hàng",
    "nhi",
    "thưa"
  ],
  "tụng": [
    "kinh",
    "đình",
    "ca",
    "niệm"
  ],
  "án": [
    "treo",
    "phí",
    "tù",
    "tử",
    "mạng",
    "văn",
    "gian",
    "ngữ",
    "binh",
    "phạt"
  ],
  "tòa": [
    "án",
    "soạn",
    "nhà",
    "tháp",
    "thành",
    "sen",
    "báo"
  ],
  "thủ": [
    "tục",
    "đoạn",
    "pháp",
    "công",
    "quỹ",
    "kho",
    "môn",
    "lĩnh",
    "đô",
    "phủ",
    "tiêu",
    "thư",
    "ác"
  ],
  "hành": [
    "chính",
    "động",
    "vi",
    "hung",
    "khách",
    "lý",
    "trình",
    "tinh",
    "hạ",
    "tỏi",
    "khất"
  ],
  "công": [
    "chứng",
    "lý",
    "văn",
    "tác",
    "dân",
    "đoàn",
    "an",
    "ty",
    "viên",
    "chúa",
    "thức",
    "trình",
    "cụ",
    "bằng"
  ],
  "chứng": [
    "nhận",
    "minh",
    "cớ",
    "chỉ",
    "thư",
    "từ",
    "khoán",
    "kiến",
    "giám"
  ],
  "tư": [
    "pháp",
    "lệnh",
    "vấn",
    "nhân",
    "thục",
    "tưởng",
    "duy",
    "cách",
    "liệu",
    "tình",
    "túi"
  ],
  "nghị": [
    "quyết",
    "định",
    "lực",
    "luận",
    "viện",
    "gật",
    "án",
    "sự"
  ],
  "đèn": [
    "đỏ",
    "xanh",
    "vàng",
    "pha",
    "cốt",
    "dầu",
    "cầy",
    "lồng",
    "trời",
    "sách",
    "pin"
  ],
  "ngã": [
    "tư",
    "ba",
    "năm",
    "bảy",
    "rẽ",
    "giá",
    "ngửa",
    "nghiêng",
    "mạn",
    "nguỵ"
  ],
  "đường": [
    "phố",
    "xá",
    "nhựa",
    "mòn",
    "đời",
    "đua",
    "ray",
    "cùng",
    "cái",
    "bộ",
    "thuỷ",
    "hàng",
    "phèn",
    "kính"
  ],
  "cầu": [
    "đường",
    "vượt",
    "treo",
    "khỉ",
    "thang",
    "nguyện",
    "cứu",
    "may",
    "toàn",
    "thủ",
    "dao",
    "hôn"
  ],
  "bến": [
    "xe",
    "tàu",
    "đò",
    "bãi",
    "cảng",
    "đỗ",
    "nước",
    "bờ"
  ],
  "vạch": [
    "kẻ",
    "đường",
    "trần",
    "lá",
    "đích",
    "xuất"
  ],
  "hẻm": [
    "nhỏ",
    "cụt",
    "núi",
    "xéo"
  ],
  "ngõ": [
    "cụt",
    "hẻm",
    "ngách",
    "nhỏ",
    "vắng",
    "lời",
    "hầu"
  ],
  "phố": [
    "phường",
    "xá",
    "cổ",
    "đi",
    "hàng",
    "thị",
    "bên"
  ],
  "lề": [
    "đường",
    "lối",
    "thói",
    "luật",
    "mề",
    "phải"
  ],
  "quần": [
    "áo",
    "đùi",
    "dài",
    "lót",
    "chúng",
    "đảo",
    "thần",
    "hùng",
    "vợt",
    "quật",
    "thâm"
  ],
  "áo": [
    "sơ",
    "mi",
    "phông",
    "thun",
    "khoác",
    "mưa",
    "dài",
    "cưới",
    "giáp",
    "gối",
    "quan",
    "ước",
    "ảnh"
  ],
  "mũ": [
    "nón",
    "bảo",
    "hiểm",
    "lưỡi",
    "trai",
    "cối",
    "phớt",
    "ni",
    "rơm",
    "áo"
  ],
  "nón": [
    "lá",
    "kỳ",
    "diệu",
    "quai",
    "thao",
    "sơn",
    "cụ"
  ],
  "giày": [
    "dép",
    "da",
    "vải",
    "cao",
    "gót",
    "thể",
    "thao",
    "lười",
    "xéo",
    "vò"
  ],
  "dép": [
    "lê",
    "tổ",
    "ong",
    "lào",
    "guốc",
    "kẹp",
    "bỏ"
  ],
  "khăn": [
    "quàng",
    "tay",
    "mùi",
    "soan",
    "tắm",
    "trải",
    "gói",
    "tang",
    "áo"
  ],
  "túi": [
    "xách",
    "quần",
    "áo",
    "bụi",
    "tiền",
    "tham",
    "ba",
    "gang"
  ],
  "vải": [
    "vóc",
    "thiều",
    "lụa",
    "vóc",
    "thô",
    "sợi",
    "bố",
    "màn"
  ],
  "lụa": [
    "là",
    "đào",
    "tơ",
    "hồng"
  ],
  "thắt": [
    "lưng",
    "cổ",
    "nút",
    "chặt",
    "đáy",
    "bím"
  ],
  "đồng": [
    "hồ",
    "phục",
    "bộ",
    "chí",
    "đội",
    "hương",
    "tiền",
    "thau",
    "ruộng",
    "ý",
    "tình",
    "bào",
    "cam"
  ],
  "bóng": [
    "đá",
    "chuyền",
    "rổ",
    "bàn",
    "chày",
    "ném",
    "bầu",
    "đèn",
    "ma",
    "gió",
    "chim",
    "mây",
    "dáng",
    "loáng"
  ],
  "cờ": [
    "vua",
    "tướng",
    "vây",
    "cá",
    "ngựa",
    "bạc",
    "bài",
    "quạt",
    "lau",
    "hiệu",
    "khởi",
    "đỏ",
    "hoa"
  ],
  "giải": [
    "đấu",
    "thưởng",
    "ngoại",
    "trí",
    "thoát",
    "cứu",
    "phóng",
    "ngân",
    "toả",
    "hạn",
    "đáp",
    "ngố",
    "khát"
  ],
  "đội": [
    "bóng",
    "tuyển",
    "trưởng",
    "hình",
    "ngũ",
    "cấn",
    "ca",
    "thiếu",
    "nhà",
    "quần"
  ],
  "trọng": [
    "tài",
    "lực",
    "lượng",
    "tâm",
    "điểm",
    "án",
    "trách",
    "thị",
    "thương",
    "đại",
    "yếu"
  ],
  "huy": [
    "chương",
    "hoàng",
    "hiệu",
    "động",
    "huyết"
  ],
  "vận": [
    "động",
    "hội",
    "may",
    "hạn",
    "tải",
    "chuyển",
    "mệnh",
    "khí",
    "dụng",
    "tốc",
    "hành"
  ],
  "sân": [
    "cỏ",
    "vận",
    "khấu",
    "khách",
    "nhà",
    "bay",
    "thượng",
    "ga",
    "chơi",
    "trường",
    "si"
  ],
  "vô": [
    "địch",
    "đối",
    "cực",
    "biên",
    "tình",
    "lý",
    "cớ",
    "nghĩa",
    "tâm",
    "dụng",
    "vàn",
    "học",
    "lại"
  ],
  "luyện": [
    "tập",
    "thi",
    "kim",
    "đan",
    "ngục",
    "thép"
  ],
  "tay": [
    "chân",
    "vịn",
    "lai",
    "sai",
    "chơi",
    "nghề",
    "trái",
    "phải",
    "trắng",
    "nải",
    "cầm",
    "lái",
    "làm",
    "ngang",
    "hòm",
    "nắm"
  ],
  "chân": [
    "tay",
    "thành",
    "thật",
    "lý",
    "dung",
    "tướng",
    "trời",
    "mây",
    "gà",
    "vịt",
    "chính",
    "giò",
    "nhang",
    "tình"
  ],
  "mắt": [
    "mũi",
    "cá",
    "kính",
    "nhìn",
    "thấy",
    "lưới",
    "xích",
    "bão",
    "na",
    "mèo",
    "thần",
    "biếc"
  ],
  "mũi": [
    "tên",
    "nhọn",
    "dùi",
    "dao",
    "kéo",
    "tàu",
    "vé",
    "lõ",
    "dọc",
    "hành",
    "mặt",
    "dạ",
    "cà"
  ],
  "miệng": [
    "lưỡi",
    "đời",
    "ăn",
    "cười",
    "rộng",
    "hùm",
    "giếng",
    "hố",
    "gió",
    "móm"
  ],
  "bụng": [
    "bự",
    "bia",
    "phệ",
    "dạ",
    "làm",
    "bảo",
    "đói",
    "mang"
  ],
  "tim": [
    "gan",
    "đen",
    "phổi",
    "đập",
    "mạch",
    "sen",
    "la",
    "tím"
  ],
  "gan": [
    "dạ",
    "lì",
    "góc",
    "ruột",
    "bàn",
    "cóc"
  ],
  "xương": [
    "sống",
    "sườn",
    "khớp",
    "xẩu",
    "máu",
    "rồng",
    "khô",
    "chậu"
  ],
  "ruột": [
    "gan",
    "thịt",
    "già",
    "non",
    "bút",
    "xe",
    "tượng",
    "thừa",
    "rà"
  ],
  "máu": [
    "mủ",
    "lửa",
    "mặt",
    "lạnh",
    "nóng",
    "chiến",
    "liều",
    "chảy",
    "me"
  ],
  "lưng": [
    "chừng",
    "vốn",
    "cơm",
    "mật",
    "trời",
    "tôm"
  ],
  "tóc": [
    "tai",
    "gáy",
    "mây",
    "rối",
    "gió",
    "bạc",
    "xanh",
    "thề",
    "tém"
  ],
  "cao": [
    "lớn",
    "ráo",
    "sang",
    "cả",
    "quý",
    "hứng",
    "ngạo",
    "tay",
    "thủ",
    "kiến",
    "số",
    "nguyên",
    "su",
    "bồi",
    "độ"
  ],
  "thấp": [
    "bé",
    "hèn",
    "kém",
    "thoáng",
    "thỏm",
    "khớp",
    "cơ",
    "thò"
  ],
  "béo": [
    "phì",
    "mập",
    "bở",
    "ngậy",
    "trục",
    "tròn",
    "tốt",
    "mầm",
    "núm",
    "úp"
  ],
  "gầy": [
    "gò",
    "guộc",
    "còm",
    "yếu",
    "mòn",
    "nhom",
    "đét",
    "dựng"
  ],
  "xinh": [
    "đẹp",
    "xắn",
    "tươi",
    "trai",
    "gái",
    "xẻo"
  ],
  "xấu": [
    "xí",
    "hổ",
    "tính",
    "nết",
    "số",
    "máu",
    "bụng",
    "mặt",
    "xa",
    "hoắc"
  ],
  "già": [
    "cỗi",
    "nua",
    "dặn",
    "làng",
    "đời",
    "mồm",
    "trẻ",
    "cốc",
    "hó",
    "họ"
  ],
  "mập": [
    "mờ",
    "mạp",
    "ú",
    "địch"
  ],
  "ốm": [
    "yếu",
    "đau",
    "nhom",
    "o",
    "đòn",
    "nghén",
    "tong"
  ],
  "lùn": [
    "tịt",
    "xịt",
    "phát"
  ],
  "mảnh": [
    "mai",
    "khảnh",
    "vỡ",
    "đất",
    "vườn",
    "tình",
    "đời",
    "dẻ",
    "trăng"
  ],
  "tròn": [
    "trĩnh",
    "xoe",
    "vo",
    "trịu",
    "vành",
    "trên",
    "xoay",
    "vẹn",
    "đầy"
  ],
  "nguyễn": [
    "y",
    "tiêu",
    "đán",
    "du",
    "trãi",
    "huệ"
  ],
  "trần": [
    "nhà",
    "gian",
    "tục",
    "trụi",
    "ai",
    "lệ",
    "tình",
    "thuật",
    "thiết",
    "trương",
    "hưng",
    "đạo"
  ],
  "lê": [
    "thê",
    "lết",
    "la",
    "bước",
    "dân",
    "thẩm",
    "lợi"
  ],
  "phạm": [
    "vi",
    "trù",
    "quy",
    "luật",
    "tội",
    "lỗi",
    "thượng",
    "nhân",
    "húy"
  ],
  "hoàng": [
    "gia",
    "đế",
    "hậu",
    "cung",
    "tộc",
    "kim",
    "đạo",
    "hôn",
    "mang",
    "phủ",
    "cầm",
    "oanh"
  ],
  "huỳnh": [
    "quang",
    "đệ",
    "đàn",
    "hoặc"
  ],
  "phan": [
    "thiết",
    "rang",
    "bội",
    "đình",
    "xi",
    "phu"
  ],
  "vũ": [
    "trụ",
    "trang",
    "khí",
    "đài",
    "lực",
    "đạo",
    "phu",
    "công",
    "sư",
    "khúc",
    "bão",
    "môn"
  ],
  "đặng": [
    "chẳng",
    "tiểu",
    "sơn"
  ],
  "bùi": [
    "ngùi",
    "tai",
    "lông",
    "nhùi"
  ],
  "đỗ": [
    "quyên",
    "đạt",
    "xanh",
    "đen",
    "bến",
    "xe",
    "thủ",
    "nghèo",
    "vỡ"
  ],
  "hồ": [
    "nước",
    "ly",
    "quảng",
    "sơ",
    "hởi",
    "dán",
    "tinh",
    "điệp",
    "khẩu",
    "đồ"
  ],
  "ngô": [
    "khoai",
    "sắn",
    "nghê",
    "quyền",
    "công"
  ],
  "dương": [
    "cầm",
    "lịch",
    "tính",
    "tiễn",
    "vật",
    "bản",
    "quá",
    "gian",
    "liễu",
    "xỉ"
  ],
  "lý": [
    "do",
    "lẽ",
    "thuyết",
    "tưởng",
    "giải",
    "trí",
    "sự",
    "lịch",
    "số",
    "thú",
    "tính"
  ],
  "giám": [
    "đốc",
    "sát",
    "thị",
    "khảo",
    "mục",
    "hộ",
    "định",
    "ngục",
    "binh"
  ],
  "tổng": [
    "cộng",
    "đài",
    "kết",
    "hợp",
    "thống",
    "quát",
    "cục",
    "trấn",
    "quan",
    "duyệt",
    "thể",
    "số"
  ],
  "trưởng": [
    "phòng",
    "ban",
    "nhóm",
    "thành",
    "lão",
    "bối",
    "đoàn",
    "tộc",
    "giả",
    "ga",
    "bạ"
  ],
  "phó": [
    "bản",
    "mặc",
    "thác",
    "nháy",
    "hội",
    "từ",
    "mát",
    "đà",
    "gia"
  ],
  "kỹ": [
    "sư",
    "thuật",
    "năng",
    "xảo",
    "càng",
    "lưỡng",
    "tính",
    "nghệ",
    "nữ"
  ],
  "thợ": [
    "xây",
    "hồ",
    "mộc",
    "điện",
    "mỏ",
    "lặn",
    "săn",
    "may",
    "cắt",
    "chụp",
    "rèn",
    "cả"
  ],
  "bác": [
    "sĩ",
    "học",
    "ái",
    "cổ",
    "bỏ",
    "đơn",
    "mẹ",
    "vật"
  ],
  "giáo": [
    "viên",
    "sư",
    "dục",
    "khoa",
    "án",
    "trình",
    "lý",
    "điều",
    "đường",
    "hoàng",
    "phái",
    "đầu",
    "dở"
  ],
  "sinh": [
    "viên",
    "học",
    "sống",
    "tồn",
    "sản",
    "đẻ",
    "tử",
    "lý",
    "kế",
    "nhật",
    "thái",
    "dục",
    "lợi",
    "thành",
    "tố"
  ],
  "lao": [
    "xao",
    "nha",
    "đao",
    "tâm",
    "lực",
    "công",
    "động",
    "phổi",
    "lý",
    "vút"
  ],
  "xôn": [
    "xao"
  ],
  "xao": [
    "xuyến",
    "động",
    "nhãng",
    "xác",
    "lãng"
  ],
  "lộp": [
    "độp",
    "bộp"
  ],
  "rầm": [
    "rập",
    "rì",
    "rộ",
    "trời"
  ],
  "ầm": [
    "ĩ",
    "ầm",
    "trĩ",
    "ừ"
  ],
  "khe": [
    "khẽ",
    "khắt",
    "cửa",
    "hở",
    "suối",
    "ngực"
  ],
  "khẽ": [
    "khàng"
  ],
  "thình": [
    "lình",
    "thịch"
  ],
  "lình": [
    "xình",
    "bình"
  ],
  "hì": [
    "hục",
    "hụi",
    "hì"
  ],
  "hối": [
    "hả",
    "thúc",
    "hận",
    "lộ",
    "phiếu",
    "đoái",
    "lỗi"
  ],
  "hả": [
    "hê",
    "dạ",
    "giận",
    "hơi"
  ],
  "lung": [
    "linh",
    "tung",
    "lay",
    "lạc"
  ],
  "linh": [
    "tinh",
    "thiêng",
    "đình",
    "cảm",
    "hồn",
    "đan",
    "chi",
    "lăng",
    "hoạt",
    "nghiệm",
    "cữu"
  ],
  "long": [
    "lanh",
    "trọng",
    "mạch",
    "nhãn",
    "não",
    "đong",
    "sòng",
    "vương",
    "bào",
    "thể",
    "móng"
  ]
}

# Add words to tu_dien.txt
for key, words in new_words.items():
    for word in words:
        full_word = f"{key} {word}"
        add_word_to_tu_dien(full_word)

print("Words added to tu_dien.txt successfully!")
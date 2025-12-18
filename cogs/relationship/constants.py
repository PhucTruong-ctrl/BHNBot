# Database path
DB_PATH = "./data/database.db"

# Embed Colors
COLOR_RELATIONSHIP = 0xFF69B4  # Hot Pink
COLOR_PET = 0x00FF7F         # Spring Green

# Gift Messages (Chill & Healing Vibe)
GIFT_MESSAGES = {
    "cafe": [
        "☕ **{sender}** đã mời **{receiver}** một tách cà phê nóng hổi. 'Cậu vất vả rồi, nghỉ ngơi chút nhé!'",
        "☕ Một buổi sáng bình yên! **{sender}** mời **{receiver}** cà phê. 'Hương vị của sự tỉnh táo!'",
        "☕ **{sender}** trao cho **{receiver}** ly cà phê. 'Chúc cậu một ngày tràn đầy năng lượng!'"
    ],
    "flower": [
        "🌹 **{sender}** tặng **{receiver}** một bông hoa. 'Cậu xinh đẹp như đóa hoa này vậy!'",
        "🌹 **{sender}** gửi đến **{receiver}** hương thơm dịu dàng. 'Mong cậu luôn rạng rỡ.'",
        "🌹 Một đóa hoa cho một người đặc biệt. **{sender}** -> **{receiver}**."
    ],
    "ring": [
        "💍 **{sender}** trao nhẫn cho **{receiver}**. 'Chúng ta là một cặp bài trùng!'",
        "💍 **{sender}** muốn gắn kết lâu dài với **{receiver}**. 'Tri kỷ của tớ!'",
        "💍 Một tín vật định tình... bạn bè? **{sender}** tặng **{receiver}** chiếc nhẫn quý giá."
    ],
    "gift": [
        "🎁 **{sender}** gửi một món quà bí mật cho **{receiver}**. 'Bất ngờ chưa!'",
        "🎁 **{sender}** tặng quà cho **{receiver}**. 'Thấy cái này hợp với cậu lắm!'",
        "🎁 **{sender}** -> **{receiver}**: 'Không nhân dịp gì cả, thích thì tặng thôi!'"
    ],
    "chocolate": [
        "🍫 **{sender}** chia sẻ ngọt ngào với **{receiver}**. 'Ăn đi cho đời thêm ngọt!'",
        "🍫 **{sender}** tặng **{receiver}** thanh sô cô la. 'Vị đắng nhẹ nhưng hậu ngọt ngào, như tình bạn tụi mình!'",
        "🍫 **{sender}** -> **{receiver}**: 'Cẩn thận sâu răng nha, nhưng mà ngon lắm!'"
    ],
    "card": [
        "💌 **{sender}** gửi thiệp cho **{receiver}**. 'Những lời này tớ muốn nói với cậu từ lâu...'",
        "💌 Một tấm thiệp nhỏ, một tấm lòng to. **{sender}** gửi **{receiver}**.",
        "💌 **{sender}** viết cho **{receiver}**: 'Cảm ơn vì đã luôn ở bên tớ.'"
    ]
}

# Affinity Values for Items
AFFINITY_VALUES = {
    "cafe": 15,
    "flower": 25,
    "ring": 100,  # Big jump
    "gift": 40,
    "chocolate": 20,
    "card": 15
}

# Affinity Thresholds & Titles (Healing/Friendship)
AFFINITY_TITLES = {
    0: "Người Lạ",
    10: "Người Quen",
    50: "Hàng Xóm Thân Thiện",
    100: "Bạn Bè",
    200: "Bạn Thân",
    500: "Cạ Cứng",
    1000: "Tri Kỷ",
    2000: "Cặp Bài Trùng",
    5000: "Soulmate (Tâm Giao)"
}

# Pet System Constants
PET_DEFAULT_NAME = "Mèo Béo"
PET_MAX_LEVEL = 10
PET_XP_PER_LEVEL = 100  # Base XP, might scale

# Pet Food Values
PET_FOOD_VALUES = {
    "fish": 15,      # Common fish
    "trash": 5,      # Recycled trash
    "water": 20,     # Shop item
    "vitamin": 40,   # Shop item
    "premium_food": 80 # Shop item
}

# Shop Items for Pet (New)
PET_SHOP_ITEMS = {
    "water": {"name": "Nước Tinh Khiết", "cost": 20, "emoji": "💧", "description": "Nước sạch cho thú cưng"},
    "vitamin": {"name": "Vitamin Tổng Hợp", "cost": 50, "emoji": "💊", "description": "Giúp thú cưng mau lớn"},
    "premium_food": {"name": "Thức Ăn Cao Cấp", "cost": 100, "emoji": "🍱", "description": "Bữa ăn sang chảnh cho thú cưng"}
}

# Pet Images - Mỗi level có 5 state riêng (Level 1-10)
PET_IMAGES = {
    1: {
        "idle": "https://i.imgur.com/Qp1nKjK.png",      # Bé mèo level 1 - Ngồi bình thường
        "sleep": "https://i.imgur.com/5Q6J9Xh.png",     # Bé mèo level 1 - Ngủ
        "eating": "https://i.imgur.com/rN9Xj5d.png",    # Bé mèo level 1 - Ăn
        "play": "https://i.imgur.com/7Y5Xj1b.png",      # Bé mèo level 1 - Chơi
        "sad": "https://i.imgur.com/9Xj5K8L.png"        # Bé mèo level 1 - Buồn/Đói
    },
    2: {
        "idle": "https://i.imgur.com/Qp1nKjK.png",      # Mèo level 2 - Ngồi bình thường
        "sleep": "https://i.imgur.com/5Q6J9Xh.png",     # Mèo level 2 - Ngủ
        "eating": "https://i.imgur.com/rN9Xj5d.png",    # Mèo level 2 - Ăn
        "play": "https://i.imgur.com/7Y5Xj1b.png",      # Mèo level 2 - Chơi
        "sad": "https://i.imgur.com/9Xj5K8L.png"        # Mèo level 2 - Buồn/Đói
    },
    3: {
        "idle": "https://i.imgur.com/Qp1nKjK.png",      # Mèo level 3 - Ngồi bình thường
        "sleep": "https://i.imgur.com/5Q6J9Xh.png",     # Mèo level 3 - Ngủ
        "eating": "https://i.imgur.com/rN9Xj5d.png",    # Mèo level 3 - Ăn
        "play": "https://i.imgur.com/7Y5Xj1b.png",      # Mèo level 3 - Chơi
        "sad": "https://i.imgur.com/9Xj5K8L.png"        # Mèo level 3 - Buồn/Đói
    },
    4: {
        "idle": "https://i.imgur.com/Qp1nKjK.png",      # Mèo level 4 - Ngồi bình thường
        "sleep": "https://i.imgur.com/5Q6J9Xh.png",     # Mèo level 4 - Ngủ
        "eating": "https://i.imgur.com/rN9Xj5d.png",    # Mèo level 4 - Ăn
        "play": "https://i.imgur.com/7Y5Xj1b.png",      # Mèo level 4 - Chơi
        "sad": "https://i.imgur.com/9Xj5K8L.png"        # Mèo level 4 - Buồn/Đói
    },
    5: {
        "idle": "https://i.imgur.com/Qp1nKjK.png",      # Mèo level 5 - Ngồi bình thường
        "sleep": "https://i.imgur.com/5Q6J9Xh.png",     # Mèo level 5 - Ngủ
        "eating": "https://i.imgur.com/rN9Xj5d.png",    # Mèo level 5 - Ăn
        "play": "https://i.imgur.com/7Y5Xj1b.png",      # Mèo level 5 - Chơi
        "sad": "https://i.imgur.com/9Xj5K8L.png"        # Mèo level 5 - Buồn/Đói
    },
    6: {
        "idle": "https://i.imgur.com/Qp1nKjK.png",      # Mèo level 6 - Ngồi bình thường
        "sleep": "https://i.imgur.com/5Q6J9Xh.png",     # Mèo level 6 - Ngủ
        "eating": "https://i.imgur.com/rN9Xj5d.png",    # Mèo level 6 - Ăn
        "play": "https://i.imgur.com/7Y5Xj1b.png",      # Mèo level 6 - Chơi
        "sad": "https://i.imgur.com/9Xj5K8L.png"        # Mèo level 6 - Buồn/Đói
    },
    7: {
        "idle": "https://i.imgur.com/Qp1nKjK.png",      # Mèo level 7 - Ngồi bình thường
        "sleep": "https://i.imgur.com/5Q6J9Xh.png",     # Mèo level 7 - Ngủ
        "eating": "https://i.imgur.com/rN9Xj5d.png",    # Mèo level 7 - Ăn
        "play": "https://i.imgur.com/7Y5Xj1b.png",      # Mèo level 7 - Chơi
        "sad": "https://i.imgur.com/9Xj5K8L.png"        # Mèo level 7 - Buồn/Đói
    },
    8: {
        "idle": "https://i.imgur.com/Qp1nKjK.png",      # Mèo level 8 - Ngồi bình thường
        "sleep": "https://i.imgur.com/5Q6J9Xh.png",     # Mèo level 8 - Ngủ
        "eating": "https://i.imgur.com/rN9Xj5d.png",    # Mèo level 8 - Ăn
        "play": "https://i.imgur.com/7Y5Xj1b.png",      # Mèo level 8 - Chơi
        "sad": "https://i.imgur.com/9Xj5K8L.png"        # Mèo level 8 - Buồn/Đói
    },
    9: {
        "idle": "https://i.imgur.com/Qp1nKjK.png",      # Mèo level 9 - Ngồi bình thường
        "sleep": "https://i.imgur.com/5Q6J9Xh.png",     # Mèo level 9 - Ngủ
        "eating": "https://i.imgur.com/rN9Xj5d.png",    # Mèo level 9 - Ăn
        "play": "https://i.imgur.com/7Y5Xj1b.png",      # Mèo level 9 - Chơi
        "sad": "https://i.imgur.com/9Xj5K8L.png"        # Mèo level 9 - Buồn/Đói
    },
    10: {
        "idle": "https://i.imgur.com/Qp1nKjK.png",      # Mèo level 10 - Ngồi bình thường (Max Level!)
        "sleep": "https://i.imgur.com/5Q6J9Xh.png",     # Mèo level 10 - Ngủ
        "eating": "https://i.imgur.com/rN9Xj5d.png",    # Mèo level 10 - Ăn
        "play": "https://i.imgur.com/7Y5Xj1b.png",      # Mèo level 10 - Chơi
        "sad": "https://i.imgur.com/9Xj5K8L.png"        # Mèo level 10 - Buồn/Đói
    }
}
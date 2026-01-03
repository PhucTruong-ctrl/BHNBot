# Database path
DB_PATH = "./data/database.db"

# Embed Colors
COLOR_RELATIONSHIP = 0xFF69B4  # Hot Pink

# Gift Messages (Chill & Healing Vibe)
GIFT_MESSAGES = {
    "cafe": [
        "☕ **{sender}** mời **{receiver}** ly cà phê. 'Uống đi cho đỡ quạo, nhìn mặt thấy ghét nhưng vẫn thương.'",
        "☕ **{sender}** donate caffeine cho **{receiver}**. 'Chạy deadline vui vẻ, đừng đột quỵ nhé bạn iu.'",
        "☕ **{sender}** -> **{receiver}**: 'Ly này high hơn người yêu cũ của cậu. Tỉnh táo lên!'",
        "☕ **{sender}** ship vội ly nâu đá cho **{receiver}**. 'Hớp một miếng, đời bớt đắng liền.'",
        "☕ **{sender}** mời **{receiver}**. 'Cà phê đắng nhưng không bằng life của tụi mình đâu ha?'",
        "☕ **{sender}** dí ly cà phê vào tay **{receiver}**. 'Uống đi rồi cày tiếp, than vãn cái gì!'",
        "☕ **{sender}** cho **{receiver}** một sự tỉnh táo. 'Đừng ngủ nữa, dậy kiếm tiền nuôi tôi đi.'",
        "☕ **{sender}** mời **{receiver}**. 'Nghe bảo cậu đang trầm cảm, uống miếng cho nó overthinking chơi.'",
        "☕ **{sender}** -> **{receiver}**: 'Lowkey quan tâm. Uống đi.'",
        "☕ **{sender}** tặng **{receiver}** ly Capuchino. 'Chút bọt biển cho lòng vơi sóng gió.'"
    ],
    "flower": [
        "🌹 **{sender}** trộm hoa về tặng **{receiver}**. 'Xinh iu như cậu xứng đáng có 10 người yêu.'",
        "🌹 **{sender}** tặng **{receiver}**. 'Cầm hoa đi, bớt cầm điện thoại lại.'",
        "🌹 **{sender}** -> **{receiver}**: 'Người ta tặng hoa hồng, tui tặng hoa mắt vì vẻ đẹp của cậu.'",
        "🌹 **{sender}** dúi bông hoa vào tay **{receiver}**. 'Nhận đi cho tui vui, chứ cậu đẹp hơn hoa rồi.'",
        "🌹 **{sender}** tặng **{receiver}**. 'Giao diện hoa hậu, hệ điều hành mầm non.'",
        "🌹 **{sender}** gửi **{receiver}**. 'Một bông hoa cho sự nỗ lực không ngừng nghỉ của cậu (dù toàn fail).'",
        "🌹 **{sender}** flex nhẹ tình cảm với **{receiver}**. 'Nhận hoa rồi thì cười một cái coi.'",
        "🌹 **{sender}** tặng **{receiver}**. 'Nở hoa trong lòng chưa? Hay vẫn đang héo úa?'",
        "🌹 **{sender}** -> **{receiver}**: 'Tặng cậu bông hoa, mong cậu không đa tình.'",
        "🌹 **{sender}** tặng **{receiver}** bông hoa. 'Keo lỳ, tái châu, chấn động!'"
    ],
    "ring": [
        "💍 **{sender}** tặng nhẫn cho **{receiver}**. 'Đeo vào là cấm sùi bọt mép nha.'",
        "💍 **{sender}** cầu... chúc **{receiver}** giàu sang. 'Nhẫn giả thôi, đeo cho sang.'",
        "💍 **{sender}** đeo nhẫn cho **{receiver}**. 'Đánh dấu chủ quyền rồi đó, lo liệu mà sống.'",
        "💍 **{sender}** -> **{receiver}**: 'Chúng ta không thuộc về nhau, nhưng chiếc nhẫn này thuộc về cậu.'",
        "💍 **{sender}** flex độ giàu với **{receiver}**. 'Thích thì chiều, yêu thì cưng.'",
        "💍 **{sender}** tặng **{receiver}**. 'Đeo chiếc nhẫn này vào, cậu là thợ săn hoặc con mồi.'",
        "💍 **{sender}** tặng **{receiver}**. 'Tình bạn diệu kỳ, bao giờ cưới nhớ mời.'",
        "💍 **{sender}** trao tín vật cho **{receiver}**. 'Từ nay đôi ta chung một nợ... ủa lộn, chung một đường.'",
        "💍 **{sender}** -> **{receiver}**: 'Diamond bright like your future (hope so).'",
        "💍 **{sender}** tặng **{receiver}**. 'Nhẫn này không vô cực, nhưng tình tui cho cậu là vô biên.'"
    ],
    "gift": [
        "🎁 **{sender}** ném hộp quà vào mặt **{receiver}**. 'Bất ngờ chưa bà già!'",
        "🎁 **{sender}** unbox bừa cho **{receiver}**. 'Mở ra đi, không phải bomb đâu.'",
        "🎁 **{sender}** -> **{receiver}**: 'Ting ting! Quà tới rồi, ra nhận hàng.'",
        "🎁 **{sender}** tặng **{receiver}**. 'Của ít lòng vòng, à lộn, lòng nhiều.'",
        "🎁 **{sender}** đưa quà cho **{receiver}**. 'Không nhân dịp gì cả, thích thì tặng thôi, ý kiến lên phường.'",
        "🎁 **{sender}** tặng **{receiver}**. 'Bên trong là cả một bầu trời tư cách.'",
        "� **{sender}** gửi **{receiver}**. 'Quà này mua bằng tiền mồ hôi nước mắt (của bố mẹ tui).'",
        "🎁 **{sender}** trao tay **{receiver}**. 'Đừng hỏi giá, hỏi tấm lòng nè.'",
        "🎁 **{sender}** -> **{receiver}**: 'Nhận quà xong nhớ review 5 sao nha shop.'",
        "🎁 **{sender}** tặng **{receiver}**. 'Quà chữa lành (hoặc chữa lợn lành thành lợn què).'"
    ],
    "chocolate": [
        "🍫 **{sender}** bón **{receiver}**. 'Ngọt ngào đến mấy cũng tan thành mây, nhưng ăn đi cho béo.'",
        "🍫 **{sender}** tặng **{receiver}**. 'Ăn đi, giảm cân là chuyện của ngày mai.'",
        "🍫 **{sender}** -> **{receiver}**: 'Socola này đắng, như cái cách crush bơ cậu vậy.'",
        "🍫 **{sender}** gửi **{receiver}**. 'Nạp đường để chạy tiếp KPI cuộc đời.'",
        "🍫 **{sender}** tặng **{receiver}**. 'Không có người yêu thì ăn socola đỡ buồn ha?'",
        "🍫 **{sender}** đưa thanh chocolate cho **{receiver}**. 'Chia sẻ sự béo này cho cậu.'",
        "🍫 **{sender}** -> **{receiver}**: '3 phần bất lực, 7 phần nuông chiều.'",
        "🍫 **{sender}** tặng **{receiver}**. 'Ăn xong nhớ đánh răng, đừng để sâu răng như sâu sắc tui.'",
        "🍫 **{sender}** mời **{receiver}**. 'Vị ngọt của tình bạn (hoặc tình phí).'",
        "🍫 **{sender}** tặng **{receiver}**. 'Socola hạng sang, ăn vào sang cả người.'"
    ],
    "card": [
        "💌 **{sender}** viết sớ cho **{receiver}**. 'Đọc đi, đừng có seen không rep.'",
        "💌 **{sender}** gửi thư tay (thời nay hiếm nha) cho **{receiver}**. 'Chữ xấu nhưng tấm lòng đẹp.'",
        "💌 **{sender}** -> **{receiver}**: 'Văn mẫu 300 ngàn, cảm động rớt nước mắt.'",
        "💌 **{sender}** gửi thiệp. 'Dành cả thanh xuân để viết cho **{receiver}** dòng này: Trả tiền tui đi.'",
        "💌 **{sender}** gửi **{receiver}**. 'Thiệp này chứa chan tình cảm (và một chút drama).'",
        "💌 **{sender}** tâm sự mỏng với **{receiver}**. 'Ê, dạo này ổn không? Ổn thì thôi.'",
        "💌 **{sender}** -> **{receiver}**: 'Lời nói gió bay, thiệp này lưu lại làm bằng chứng.'",
        "💌 **{sender}** gửi **{receiver}**. 'Viết vội dòng này, mong cậu bớt nghiệp.'",
        "💌 **{sender}** gửi thiệp. 'Gửi ngàn nụ hôn (gió) tới **{receiver}**.'",
        "💌 **{sender}** gửi **{receiver}**. 'Check mail... à nhầm, check thiệp đi bạn hiền.'"
    ]
}
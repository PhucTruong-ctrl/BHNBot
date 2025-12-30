"""Constants and Configurations for Xi Dach."""

# Game Settings
MIN_BET = 1
MAX_PLAYERS = 8
SOLO_TIMEOUT = 120    # seconds
LOBBY_DURATION = 30   # seconds
BETTING_DURATION = 15 # seconds
TURN_TIMEOUT = 45     # seconds
CLEANUP_INTERVAL = 300 # 5 minutes

# Emoji Constants
EMOJI_CONFIRM = "✅"
EMOJI_CANCEL = "❌"
EMOJI_JOIN = "✋"
EMOJI_LEAVE = "📤"
EMOJI_HIT = "👇"
EMOJI_STAND = "✋"
EMOJI_DOUBLE = "💎"
EMOJI_QUIT = "🏳️"

# ==================== MESSAGE POOLS ====================
# Dealer Outcome Messages
DEALER_MESSAGES = {
    "blackjack": [
        "🎰 Nhà cái ra **Xì Dách**! Xin chia buồn cả nhà.",
        "💀 Nhà cái bịp... đúng là **Xì Dách** luôn!",
        "🔥 Nhà cái phang luôn **21 điểm** đầu tiên! Đỡ thế nào được!",
        "🤖: \"Ez game, Xì Dách nhé các cháu!\"",
        "⚡ Sấm sét giữa trời quang! Nhà cái **Xì Dách**!"
    ],
    "bust": [
        "💥 Nhà cái **quắc** ({score} điểm)! Đồng loạt ăn tiền!",
        "😂 Nhà cái thua rồi! Cháy bài {score} điểm, anh em lên thuyền!",
        "🎉 Tin vui: Nhà cái toang, bay {score} điểm! Húp thôi!",
        "🚒 Gọi cứu hỏa đi! Nhà cái cháy khét lẹt ({score})!",
        "💸 Nhà cái phát tiền từ thiện! (Quắc {score})"
    ],
    "stand": [
        "🤖 Nhà cái chốt **{score} điểm**.",
        "⏸️ Nhà cái dừng ở {score}. Ai cao hơn thì ăn!",
        "🎯 Nhà cái dằn bài. {score} điểm đủ để lụm tiền chưa?",
        "🛡️ Nhà cái thủ thân với {score} điểm.",
        "👀 {score} điểm. Nhà cái nhìn anh em với ánh mắt phán xét."
    ]
}

# Player Win Messages (+Value)
PLAYER_WIN_MESSAGES = [
    "{user} **thắng** rồi! {payout_display}",
    "🏆 {user} hốt bạc! {payout_display}. Mời cả làng đi ăn!",
    "💰 {user} nhân phẩm bùng nổ! {payout_display}. Flex nhẹ cái nào!",
    "✨ {user} đỉnh nóc kịch trần bay phấp phới! {payout_display}",
    "🦈 {user} cắn nhà cái một miếng to! {payout_display}",
    "🍀 Số hưởng là đây! {user} lụm {payout_display}",
    "🚀 {user} bay thẳng lên mặt trăng! {payout_display}",
    "💃 {user} nhảy múa trên nỗi đau nhà cái! {payout_display}"
]

# Player Lose Messages (-Value)
PLAYER_LOSE_MESSAGES = [
    "{user} đã **về bờ**... {score} điểm.",
    "💀 {user} tạch rồi! {score} điểm. Chia buồn.",
    "😢 {user} xa bờ, mất {bet} Hạt. Thua keo này bày keo khác!",
    "🌊 {user} chìm nghỉm... {score} điểm.",
    "💸 {user} cúng tiền cho bot. {bet} Hạt ra đi...",
    "🥀 {user} héo hon. {score} điểm không đủ tuổi.",
    "🤕 {user} vỡ mộng làm giàu. Mất {bet} Hạt.",
    "🤡 {user} diễn xiếc và cái kết... {score} điểm."
]

# Player Push Messages
PLAYER_PUSH_MESSAGES = [
    "{user} **hòa vốn**. Đời không như là mơ.",
    "🤝 {user} huề nhé! {score} điểm. Vui vẻ không quạu.",
    "⚖️ {user} bảo toàn tính mạng. Không thắng không thua.",
    "🛡️ {user} thủ hòa thành công. Vẫn còn vốn!",
    "😐 {user} công cốc. {score} điểm hòa tiền."
]

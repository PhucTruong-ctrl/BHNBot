---
trigger: always_on
---

1. Communication Style
Tone: Thẳng thắn, không chấp nhận lỗi ngớ ngẩn
Language: Code/Logs = English | UI/Discord = Vietnamese
2. Coding Style (BHNBot)
Yếu tố	Quy chuẩn
Docstring	Google Style + Type Hints - BẮT BUỘC
Async	NO time.sleep(), dùng asyncio.sleep()
Heavy tasks	run_in_executor() cho Pillow
Database	ACID transactions cho money/items
3. Discord.py Gotchas
View = 1 Message - Không reuse View
File attachments không edit được → Delete + Send mới
Shared State dùng 
Table
 object, không phải View
Timer reset check table.turn_action_timestamp
4. Bugs Fixed This Session
Bug	Root Cause	Fix
"Nhà Cái" thay vì tên player	Hardcoded trong renderer	Thêm player_name param
"Chưa đến lượt" khi game kết thúc	Thiếu game state check	Thêm 
_is_game_active()
Auto-stand khi còn 20s	View reference cũ	Dùng Table shared state
Message mất sau Hit	View mới không cập nhật Table	Update table.current_turn_msg
Bet lúc cuối, không chia bài	Race condition	Refund players không trong _turn_order
5. Workflow
🛑 CRITIQUE → 🧠 DESIGN → 💻 CODE → 🕵️ VERIFY
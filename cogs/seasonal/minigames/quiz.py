from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import discord

from ..minigames.base import BaseMinigame, register_minigame
from ..services import add_contribution, add_currency, get_active_event, update_community_progress

if TYPE_CHECKING:
    from discord import Interaction, TextChannel

    from ..core.event_manager import EventManager

logger = logging.getLogger("Quiz")


DEFAULT_QUIZ_QUESTIONS = [
    {
        "question": "Tết Trung Thu diễn ra vào ngày nào âm lịch?",
        "options": ["15/7", "15/8", "15/9", "1/8"],
        "correct": 1,
    },
    {
        "question": "Loại bánh nào là đặc trưng của Trung Thu?",
        "options": ["Bánh chưng", "Bánh trung thu", "Bánh tét", "Bánh giày"],
        "correct": 1,
    },
    {
        "question": "Chị Hằng sống ở đâu theo truyền thuyết?",
        "options": ["Trên núi", "Dưới biển", "Trên cung trăng", "Trong rừng"],
        "correct": 2,
    },
    {
        "question": "Chú Cuội ngồi dưới gốc cây gì?",
        "options": ["Cây đa", "Cây bàng", "Cây phượng", "Cây xoài"],
        "correct": 0,
    },
    {
        "question": "Trung Thu còn gọi là Tết gì?",
        "options": ["Tết Đoan Ngọ", "Tết Thiếu Nhi", "Tết Nguyên Đán", "Tết Thanh Minh"],
        "correct": 1,
    },
    {
        "question": "Múa gì là đặc trưng của Trung Thu?",
        "options": ["Múa lân", "Múa rồng", "Múa sạp", "Múa xòe"],
        "correct": 0,
    },
    {
        "question": "Đèn lồng Trung Thu thường có hình gì?",
        "options": ["Hình vuông", "Hình ngôi sao", "Hình ông sao", "Hình tam giác"],
        "correct": 2,
    },
    {
        "question": "Trẻ em thường làm gì vào đêm Trung Thu?",
        "options": ["Ngủ sớm", "Rước đèn", "Đi học", "Làm bài tập"],
        "correct": 1,
    },
]


@register_minigame("quiz")
class QuizMinigame(BaseMinigame):

    def __init__(self, bot: Any, event_manager: EventManager) -> None:
        super().__init__(bot, event_manager)
        self._active_quizzes: dict[int, dict] = {}

    @property
    def name(self) -> str:
        return "Đố Vui Trung Thu"

    def _get_config(self, event: Any) -> dict[str, Any]:
        if event and hasattr(event, "minigame_config"):
            return event.minigame_config.get("quiz", {})
        return {}

    async def spawn(self, channel: TextChannel, guild_id: int) -> None:
        active = await get_active_event(guild_id)
        if not active:
            return

        event = self.event_manager.get_event(active["event_id"])
        if not event:
            return

        config = self._get_config(event)
        timeout = config.get("timeout_per_question", 30)
        questions = config.get("questions", DEFAULT_QUIZ_QUESTIONS)
        expire_time = datetime.now() + timedelta(seconds=timeout)

        question = random.choice(questions)

        embed = discord.Embed(
            title="🎑 ĐỐ VUI TRUNG THU!",
            description=f"**{question['question']}**",
            color=event.color if event else 0xFFD700,
        )

        options_text = []
        for i, opt in enumerate(question["options"]):
            options_text.append(f"{chr(65+i)}. {opt}")
        embed.add_field(name="📝 Đáp án", value="\n".join(options_text), inline=False)
        embed.add_field(name="⏰ Thời gian", value=f"<t:{int(expire_time.timestamp())}:R>", inline=True)
        embed.set_footer(text="Người trả lời đúng đầu tiên nhận bonus!")

        view = QuizView(self, guild_id, active["event_id"], question, expire_time)
        message = await channel.send(embed=embed, view=view)

        self._active_quizzes[message.id] = {
            "guild_id": guild_id,
            "event_id": active["event_id"],
            "question": question,
            "answers": {},
            "first_correct": None,
            "expire_time": expire_time,
            "message": message,
            "start_time": datetime.now(),
        }

    async def handle_interaction(self, interaction: Interaction) -> None:
        pass

    async def submit_answer(self, interaction: Interaction, message_id: int, answer_idx: int) -> None:
        data = self._active_quizzes.get(message_id)
        if not data:
            await interaction.response.send_message("❌ Câu hỏi đã kết thúc!", ephemeral=True)
            return

        if datetime.now() > data["expire_time"]:
            await interaction.response.send_message("❌ Đã hết thời gian!", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in data["answers"]:
            await interaction.response.send_message("❌ Bạn đã trả lời rồi!", ephemeral=True)
            return

        question = data["question"]
        is_correct = answer_idx == question["correct"]
        data["answers"][user_id] = {"answer": answer_idx, "correct": is_correct}

        event = self.event_manager.get_event(data["event_id"])
        config = self._get_config(event)
        emoji = event.currency_emoji if event else "🥮"

        if is_correct:
            base_reward = config.get("reward_per_correct", 25)
            bonus = 0

            if data["first_correct"] is None:
                data["first_correct"] = user_id
                bonus = config.get("reward_fast_bonus", 10)

            total_reward = base_reward + bonus
            await add_currency(data["guild_id"], user_id, data["event_id"], total_reward)
            await add_contribution(data["guild_id"], user_id, data["event_id"], total_reward)
            await update_community_progress(data["guild_id"], 1)

            bonus_text = f" (Bonus nhanh nhất: +{bonus})" if bonus > 0 else ""
            await interaction.response.send_message(
                f"✅ Chính xác! +**{total_reward}** {emoji}{bonus_text}",
                ephemeral=True,
            )
        else:
            correct_answer = question["options"][question["correct"]]
            await interaction.response.send_message(
                f"❌ Sai rồi! Đáp án đúng là: **{correct_answer}**",
                ephemeral=True,
            )

    async def end_quiz(self, message_id: int) -> None:
        data = self._active_quizzes.get(message_id)
        if not data:
            return

        question = data["question"]
        correct_answer = question["options"][question["correct"]]

        correct_users = [uid for uid, ans in data["answers"].items() if ans["correct"]]
        wrong_users = [uid for uid, ans in data["answers"].items() if not ans["correct"]]

        embed = discord.Embed(
            title="🎑 KẾT QUẢ ĐỐ VUI",
            description=f"**{question['question']}**\n\nĐáp án: **{correct_answer}**",
            color=0x808080,
        )
        embed.add_field(name="✅ Đúng", value=str(len(correct_users)), inline=True)
        embed.add_field(name="❌ Sai", value=str(len(wrong_users)), inline=True)

        if data["first_correct"]:
            user = self.bot.get_user(data["first_correct"])
            name = user.display_name if user else f"User {data['first_correct']}"
            embed.add_field(name="🏆 Nhanh nhất", value=name, inline=True)

        try:
            await data["message"].edit(embed=embed, view=None)
        except discord.NotFound:
            pass

        self._active_quizzes.pop(message_id, None)


class QuizView(discord.ui.View):
    OPTION_LABELS = ["A", "B", "C", "D"]

    def __init__(
        self,
        minigame: QuizMinigame,
        guild_id: int,
        event_id: str,
        question: dict,
        expire_time: datetime,
    ) -> None:
        timeout = (expire_time - datetime.now()).total_seconds()
        super().__init__(timeout=max(timeout, 1))
        self.minigame = minigame
        self.guild_id = guild_id
        self.event_id = event_id
        self.question = question
        self.message_id: int | None = None

        for i, option in enumerate(question["options"]):
            button = discord.ui.Button(
                label=self.OPTION_LABELS[i],
                style=discord.ButtonStyle.secondary,
                custom_id=f"opt_{i}",
            )
            button.callback = self._make_callback(i)
            self.add_item(button)

    def _make_callback(self, idx: int):
        async def callback(interaction: discord.Interaction) -> None:
            if self.message_id is None:
                self.message_id = interaction.message.id
            await self.minigame.submit_answer(interaction, self.message_id, idx)

        return callback

    async def on_timeout(self) -> None:
        if self.message_id:
            await self.minigame.end_quiz(self.message_id)

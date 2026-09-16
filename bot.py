import asyncio
import json
import logging
import os
import random
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Add it to your .env file.")

QUESTIONS_PATH = Path(__file__).parent / "questions.json"
MAX_ANSWER_LENGTH = 512

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# Remembers the last question shown to each user, so we can avoid
# immediately repeating it on the next click.
last_question_id: dict[int, int] = {}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_questions() -> list[dict]:
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    for q in questions:
        if len(q["answer"]) > MAX_ANSWER_LENGTH:
            logger.warning(
                "Question id=%s answer is %d chars, over the %d limit",
                q["id"], len(q["answer"]), MAX_ANSWER_LENGTH,
            )
    return questions


QUESTIONS = load_questions()


def pick_random_question(user_id: int) -> dict:
    """Pick a random question, avoiding an immediate repeat when possible."""
    if len(QUESTIONS) == 1:
        return QUESTIONS[0]

    previous_id = last_question_id.get(user_id)
    candidates = [q for q in QUESTIONS if q["id"] != previous_id]
    question = random.choice(candidates)
    last_question_id[user_id] = question["id"]
    return question


def format_card(question: dict) -> str:
    """Format a question/answer pair as a small HTML 'card'."""
    return f"🔬 <b>{question['question']}</b>\n\n{question['answer']}"


def random_question_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Random question", callback_data="random_question")]
        ]
    )


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(
        "👋 Hi there, curious explorer!\n\n"
        "I'm a science bot — press the button below and I'll answer a fun "
        "science question, just for you!",
        reply_markup=random_question_keyboard(),
    )


@router.callback_query(F.data == "random_question")
async def handle_random_question(callback: CallbackQuery) -> None:
    question = pick_random_question(callback.from_user.id)
    card_text = format_card(question)

    await callback.message.answer(
        card_text,
        reply_markup=random_question_keyboard(),
        parse_mode="HTML",
    )
    # Acknowledge the button press so Telegram stops showing the loading spinner.
    await callback.answer()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Loaded %d questions", len(QUESTIONS))
    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

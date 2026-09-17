import asyncio
import json
import logging
import os
import random
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Add it to your .env file.")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

# Fast, free-tier-friendly Gemini model.
GEMINI_MODEL = "gemini-2.5-flash"
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

QUESTIONS_PATH = Path(__file__).parent / "questions.json"
MAX_ANSWER_LENGTH = 512
MAX_INCOMING_QUESTION_LENGTH = 300  # keep kids' typed questions reasonably short

KID_SCIENCE_SYSTEM_PROMPT = (
    "You answer science questions for children aged 6-12. Rules: "
    "1) Only answer questions that have a real scientific explanation "
    "(nature, animals, space, the body, how things work, etc). "
    "2) If the message isn't a science question (e.g. random chat, "
    "personal topics, requests unrelated to science), gently reply that "
    "you can only answer science questions and suggest they try one, "
    "in one short sentence. "
    "3) Never discuss violence, weapons, mature, or scary/graphic content "
    "-- redirect to a safe related science topic instead. "
    "4) Keep the answer factually accurate, warm, and simple enough for "
    "a curious kid to understand, using a short analogy where it helps. "
    "5) Hard limit: your entire reply must be under 480 characters. "
    "6) Reply with plain text only, no markdown, no headers."
)

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


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_freeform_card(user_question: str, answer: str) -> str:
    """Format a kid-typed question + the AI's answer as the same card style."""
    title = user_question.strip()
    if len(title) > 120:
        title = title[:117] + "..."
    return f"🔬 <b>{escape_html(title)}</b>\n\n{escape_html(answer)}"


async def ask_gemini(question: str) -> str:
    response = await gemini_client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=question,
        config=genai_types.GenerateContentConfig(
            system_instruction=KID_SCIENCE_SYSTEM_PROMPT,
            max_output_tokens=300,
        ),
    )
    answer = (response.text or "").strip()

    if len(answer) > MAX_ANSWER_LENGTH:
        answer = answer[: MAX_ANSWER_LENGTH - 1].rstrip() + "…"
    return answer


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
        "I'm a science bot! Press the button below for a fun random "
        "question, or just type your own science question any time — "
        "like 'why do cats purr?' — and I'll do my best to explain it!",
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


@router.message(F.text & ~F.text.startswith("/"))
async def handle_free_question(message: Message) -> None:
    """Handles any question a kid types themselves (not a command)."""
    question = message.text.strip()

    if not question:
        return

    if len(question) > MAX_INCOMING_QUESTION_LENGTH:
        await message.answer(
            "That's a big question! 😅 Can you make it a bit shorter, "
            "like 'Why is the sky blue?'"
        )
        return

    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    try:
        answer = await ask_gemini(question)
    except Exception:
        logger.exception("Gemini API call failed for question: %s", question)
        await message.answer(
            "Hmm, my science brain glitched for a second! 🔬 Try asking "
            "again, or press the button for a random question.",
            reply_markup=random_question_keyboard(),
        )
        return

    card_text = format_freeform_card(question, answer)
    await message.answer(
        card_text,
        reply_markup=random_question_keyboard(),
        parse_mode="HTML",
    )


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

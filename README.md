# Science Bot for Kids (aiogram)

A Telegram bot that answers kids' science questions with a short "card":
a bold question title followed by a short answer (≤512 characters).

## How it works

1. User sends `/start` → gets a welcome message + a **🎲 Random question** button.
2. Pressing the button picks a random question from `questions.json` and
   sends it back as a formatted card (title + answer).
3. The same button appears again, so the user can keep tapping for more.
4. The bot avoids showing the exact same question twice in a row for a user.

## Setup

1. **Get a bot token**
   Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`,
   and follow the prompts. Copy the token it gives you.

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your token**
   Copy `.env.example` to `.env` and paste your token in:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env`:
   ```
   BOT_TOKEN=123456789:AAExampleTokenFromBotFather
   ```

4. **Run the bot**
   ```bash
   python bot.py
   ```

5. Open your bot in Telegram and send `/start`.

## Adding more questions

Edit `questions.json`. Each entry looks like:

```json
{
  "id": 11,
  "question": "Why do onions make us cry?",
  "answer": "Short scientific explanation, kept under 512 characters..."
}
```

- `id` must be unique.
- Keep `answer` at or under **512 characters** — the bot logs a warning on
  startup if any answer is too long, so you'll catch mistakes early.

## Project structure

```
science-bot/
├── bot.py              # Main bot logic (aiogram 3.x)
├── questions.json       # Question/answer database
├── requirements.txt     # Python dependencies
├── .env.example          # Template for your bot token
└── README.md
```

## Notes / next steps

- Currently uses **long polling** (`start_polling`), which is fine for
  development and small bots. For production at scale, consider switching
  to webhooks.
- "Last question per user" is stored in memory (a plain dict), so it resets
  if the bot restarts. Fine for this use case; swap in Redis or a DB if you
  need it to persist.
- You could extend this with topic categories, a "favorite question"
  button, or images per question (aiogram supports `answer_photo` with a
  caption if you want a richer visual card).

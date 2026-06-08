# cheese_quiz_posting_bot

Admin Telegram bot for publishing posts to CheeseQuiz / Sunny Nights / HarryPotter channels.

## Deployment

| Field | Value |
|---|---|
| Container | `cheese_quiz_posting_bot` |
| Server path | `~/python/cheese_quiz_posting_bot/` |
| Telegram bot | `@cheeze_quiz_post_bot` |
| Admins | `50621942`, `183233559` |

Deploy:
```bash
ssh -i keys/id_ed25519 -p 7777 funcker@37.27.12.112 \
  "cd ~/python/cheese_quiz_posting_bot && docker compose up --build -d"
```

## Projects & channels

| Project key | Button label | Channels | Signup button |
|---|---|---|---|
| `cheese` | 🧀 CHEESE QUIZ | `@cheze_test`, `@CheeseQuizBg` | `@cheese_quiz_bg_bot` |
| `sunny` | ☀️ SUNNY NIGHTS | `@Quest_Sunny_Nights` | custom URL (asked each time) |
| `harry` | 🧙 HarryPotter | `-1002826696946` | `@cheese_quiz_bg_bot` |

Channels are configured via `.env` (see below). The bot is added as admin to all channels.

## Environment variables

```env
BOT_TOKEN=...
ADMIN_IDS=50621942,183233559
CHANNELS=@cheze_test|🧪 Тест;@CheeseQuizBg|📢 CheeseQuiz BG
CHANNELS_SUNNY=@Quest_Sunny_Nights|☀️ Sunny Nights
CHANNELS_HARRY=-1002826696946|HarryPotter
SIGNUP_BOT_URL=https://t.me/cheese_quiz_bg_bot
BUTTON_TEXT=Записаться на игру
```

Adding a new project: add `CHANNELS_<NAME>` to `.env`, add `channels_<name>` field to `Config` in `config.py`, add entry to `PROJECTS` dict in `bot.py`.

## Post flow

1. `/newpost` — choose project (cheese / sunny / harry)
2. Send 1 or 2 photos
3. Send post text (HTML formatting supported)
4. Choose whether to add a signup button
5. Preview → publish to channel (or edit photo/text first)

**Grouping rule:** text is always attached as caption to the photo, never sent as a separate message. Single photo supports up to 4096 chars; media group (2 photos) up to 1024 — if longer, first photo gets caption and second is sent separately.

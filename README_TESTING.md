# Bot2.0 – Full Test Checklist

## Render
Build command:
`pip install -r requirements.txt`

Start command:
`python main.py`

Required:
- BOT_TOKEN
- MONGO_URL
- ADMIN_IDS
- API_ID / API_HASH (only needed by features that use Telethon)

Optional:
- GITHUB_TOKEN / GITHUB_OWNER / GITHUB_REPO
- DATABASE_CHANNEL_ID
- PAYMENT_VERIFY_CHANNEL_ID
- USER_ACTIVITY_CHANNEL_ID
- PAID_USER_CHANNEL_ID
- GOOGLE_SHEET_URL / GOOGLE_SCRIPT_URL

## First test
1. Open bot and send `/start`.
2. Main menu shows TEST INDEX, EXTRACT TEST, PREMIUM, FREE TRIAL, MY ACCOUNT, PRICE, JOIN CHANNEL, REPORT, COMMAND MENU.
3. If the user is an admin, ADMIN PANEL is also shown.
4. Tap COMMAND MENU or send `/commands` to see all commands.
5. Admin sends `/seed`. This creates `DEMO-2026-001`.
6. Tap TEST INDEX -> SSC -> SSC GD -> Mock -> 2026 -> Demo SSC GD TCS Test.
7. Open the test details and tap EXTRACT TEST.
8. The demo HTML is served from the MongoDB backup fallback, so GitHub is not required for this demo flow.

## Upload test
Admin sends `/upload`, then sends an HTML/JSON/TXT test file. Send `DONE` after the file(s). GitHub is used when configured; otherwise the generated HTML is kept in the backup collection as a fallback.

## Admin
`/admin` opens the complete admin panel. `/stats` checks database statistics. `/seed` creates a known demo test for repeatable testing.

## Important
Never put BOT_TOKEN in source code. Keep it only in Render Environment Variables. If a token was exposed in logs/screenshots, revoke it in BotFather and create a new one.

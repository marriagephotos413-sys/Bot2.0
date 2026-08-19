# Bot 2.0 — Final Test Checklist

## 1. Render Environment
Required:
- BOT_TOKEN
- MONGO_URL
- ADMIN_IDS (your Telegram numeric ID)

Optional:
- ADMIN_USERNAMES
- GitHub variables
- channel defaults

## 2. First Telegram test
1. Open bot and send `/start`.
2. Press `📋 COMMAND MENU`.
3. Press `🛠️ ADMIN PANEL`.
4. Admin panel should open only for configured admins.

## 3. User menu
Test:
- TEST INDEX
- EXTRACT TEST
- PREMIUM
- FREE TRIAL
- MY ACCOUNT
- PRICE
- JOIN CHANNEL
- REPORT
- COMMAND MENU

## 4. Admin panel
Test every button:
- BOT STATS
- USER LIST
- PAID USERS
- BAN USER
- UNBAN USER
- FREE TRIAL
- TRIAL LOCK
- BROADCAST
- PRICE
- WELCOME
- ADD TEST
- TEST REPORT
- FORCE JOIN
- BACKUP
- DATABASE CHANNEL
- PAYMENT CHANNEL
- USER CHANNEL
- PAID CHANNEL
- PAID USER CHANNEL
- SETTINGS
- QUEUE STATUS
- HOME

## 5. Channel setup
For each channel:
1. Add the bot to the channel as Admin.
2. Open the corresponding Admin Panel channel button.
3. Press `SET / CHANGE`.
4. Send `@username` for a public channel, OR `-100...` for a private channel where the bot has access.
5. The bot should show the resolved channel title and ID.
6. Remove it and add it again to verify both operations.

Force Join additionally verifies that the bot can inspect membership.

## 6. Test upload
- Open `ADD TEST`.
- Send one HTML/JSON/TXT file.
- Send `DONE`.
- Check Queue Status.
- Open Test Index and confirm the test appears.

For a zero-data installation, `/seed` creates a small demo test for checking:
Category → Exam → Type → Year → Test → Extract.

## 7. Database
The application creates/ensures MongoDB indexes at startup through `db.ensure_indexes()`.
Channel settings are stored as structured records instead of accidentally storing the entire channel dictionary as `channel_id`.

## 8. Important
Never paste BOT_TOKEN or MONGO_URL into public chats, GitHub, screenshots, or this README.

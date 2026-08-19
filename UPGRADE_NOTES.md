# Bot 2.0 - Upgraded

Main fixes:
- Central callback router for user/admin/test/payment/upload menus.
- Admin button appears in the main menu for configured ADMIN_IDS.
- /help, /index, /extract, /upload, /stats, /price, /trial, /userinfo, /report commands.
- Queue processors are registered and started at bot startup.
- MongoDB compatibility methods used by the existing handlers were added.
- GitHub is optional. If GitHub variables are absent, uploaded TCS HTML is backed up to the Telegram Database Channel and extraction can use the Telegram file_id.
- Fixed keyboards.py syntax error.
- Added missing config compatibility settings.
- Render health endpoint remains /health.

Render:
Build Command: pip install -r requirements.txt
Start Command: python main.py

Required environment:
BOT_TOKEN
API_ID
API_HASH
MONGO_URL
ADMIN_IDS
DATABASE_CHANNEL_ID

Optional:
PAYMENT_VERIFY_CHANNEL_ID
USER_ACTIVITY_CHANNEL_ID
PAID_USER_CHANNEL_ID
FORCE_JOIN_CHANNELS
GOOGLE_SHEET_URL
GOOGLE_SCRIPT_URL
GitHub variables are optional.

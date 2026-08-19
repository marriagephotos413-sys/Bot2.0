# Bot2.0 FINAL

## Render Environment Variables

Required:
- BOT_TOKEN
- MONGO_URL
- ADMIN_IDS (recommended: Telegram numeric user ID)

Alternative admin configuration:
- ADMIN_ID
- OWNER_ID
- ADMIN_USERNAMES
- ADMIN_USERNAME
- OWNER_USERNAME

Optional:
- MONGO_DATABASE=telegram_test_bot
- GITHUB_TOKEN
- GITHUB_OWNER
- GITHUB_REPO
- GITHUB_BRANCH=main
- GITHUB_TEMPLATE_PATH=tcs.html
- DATABASE_CHANNEL_ID
- PAYMENT_VERIFY_CHANNEL_ID
- USER_ACTIVITY_CHANNEL_ID
- PAID_USER_CHANNEL_ID

## Render
Build command:
`pip install -r requirements.txt`

Start command:
`python main.py`

## Admin setup

1. Open the bot and press `/start`.
2. Press **ADMIN PANEL**.
3. If access is denied, the bot now shows your Telegram ID.
4. Put that ID in Render as `ADMIN_IDS`, save, and redeploy.
5. You can also use `ADMIN_USERNAMES` with the Telegram username.

## Admin features

- Add Test / Upload Test
- Bulk Test Upload
- Test Report
- Bot Statistics
- User List
- Paid Users
- Ban / Unban
- Free Trial settings
- Broadcast
- Price settings
- Welcome settings
- Force Join
- Database Channel
- Payment Channel
- User Activity Channel
- Paid User Channel
- Backup
- Queue Status
- Maintenance / Extract / Upload switches

## User features

- Test Index
- Extract Test
- Premium
- Free Trial
- My Account
- Price
- Join Channel
- Report
- Command Menu

## Test

Admin can use `/seed` to create a demo test, then open Test Index and test the complete category -> exam -> type -> year -> test -> extract flow.

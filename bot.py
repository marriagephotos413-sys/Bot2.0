import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URI, ADMIN_USER_ID

# Logging setup
logging.basicConfig(level=logging.INFO)

# Initialize Pyrogram Bot
app = Client(
    "StartupBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Initialize MongoDB Client (Motor)
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["startup_db"]
force_channels_col = db["force_channels"]

# Force Join Check Function
async def check_force_sub(client, user_id):
    try:
        channels = await force_channels_col.find().to_list(length=100)
        for ch in channels:
            chat_id = ch["chat_id"]
            try:
                member = await client.get_chat_member(chat_id, user_id)
                if member.status in ["left", "kicked"]:
                    return False
            except Exception:
                # Agar bot channel ka admin nahi hai ya koi aur error aaye
                return False
        return True
    except Exception as e:
        logging.error(f"Force sub error: {e}")
        return True

# /start Command Handler
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    user_id = message.from_user.id
    
    # Check Force Join
    is_joined = await check_force_sub(client, user_id)
    if not is_joined:
        channels = await force_channels_col.find().to_list(length=100)
        keyboard = []
        for ch in channels:
            keyboard.append([InlineKeyboardButton(ch["title"], url=ch["invite_link"])])
        keyboard.append([InlineKeyboardButton("🔄 Try Again", callback_data="check_join")])
        
        await message.reply(
            "⚠️ **Aapne hamare required channels join nahi kiye hain!**\n\nKripya pehle niche diye gaye channels ko join karein, phir 'Try Again' par click karein.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await message.reply("👋 Swagat hai aapka! Aapka startup bot taiyar hai. Test shuru karne ke liye niche options use karein.")

# Callback Query for Force Join Verification
@app.on_callback_query(filters.regex("check_join"))
async def verify_join(client, callback_query):
    user_id = callback_query.from_user.id
    is_joined = await check_force_sub(client, user_id)
    
    if is_joined:
        await callback_query.message.edit_text("✅ Verification successful! Ab aap bot ka use kar sakte hain. /start dabayein.")
    else:
        await callback_query.answer("⚠️ Aapne abhi tak sabhi channels join nahi kiye hain!", show_alert=True)

# Admin Command: Add Force Join Channel
@app.on_message(filters.command("add_channel") & filters.user(ADMIN_USER_ID))
async def add_channel(client, message):
    try:
        # Format: /add_channel -100xxxxxxxxxx Channel_Name https://t.me/...
        _, chat_id, title, invite_link = message.text.split(" ", 3)
        await force_channels_col.update_one(
            {"chat_id": int(chat_id)},
            {"$set": {"title": title, "invite_link": invite_link}},
            upsert=True
        )
        await message.reply(f"✅ Channel **{title}** successfully force join list mein add ho gaya hai.")
    except Exception as e:
        await message.reply(f"❌ Error: Sahi format use karein.\n`/add_channel <chat_id> <Title> <Invite_Link>`")

if __name__ == "__main__":
    print("🚀 Bot started successfully...")
    app.run()

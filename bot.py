import os
import json
import uuid
import threading
import pandas as pd
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient

# 🌟 LOGGING: इससे पता चलेगा कि बॉट काम कर रहा है या कोई एरर है
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 🌟 ENVIRONMENT VARIABLES 🌟
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = os.environ.get("API_ID") 
API_HASH = os.environ.get("API_HASH")
MONGO_URL = os.environ.get("MONGO_URL")

# चेक करें कि सभी वेरिएबल्स मौजूद हैं या नहीं
if not all([BOT_TOKEN, API_ID, API_HASH, MONGO_URL]):
    logger.error("❌ ERROR: एक या अधिक Environment Variables गायब हैं! (Render Dashboard चेक करें)")

GITHUB_URL = "https://tests22mock-dot.github.io/MockTestUI"

# ==========================================
# 🗄️ DATABASE SETUP
# ==========================================
try:
    async_db_client = AsyncIOMotorClient(MONGO_URL)
    tests_collection = async_db_client["MockTestDB"]["tests"]
    channels_collection = async_db_client["MockTestDB"]["channels"]
    users_collection = async_db_client["MockTestDB"]["users"]
    
    sync_db_client = MongoClient(MONGO_URL)
    sync_collection = sync_db_client["MockTestDB"]["tests"]
    logger.info("✅ Database Connected Successfully!")
except Exception as e:
    logger.error(f"❌ Database Connection Error: {e}")

user_steps = {}

# ==========================================
# 🌐 FLASK API
# ==========================================
web_app = Flask(__name__)
CORS(web_app)

@web_app.route('/')
def home(): 
    return "✅ Mock Test Bot & API is Live!"

def run_flask():
    web_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# ==========================================
# 🤖 BOT COMMANDS
# ==========================================
app = Client("MockTestBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    logger.info(f"Received /start from User: {message.from_user.id}")
    try:
        await users_collection.update_one(
            {"user_id": message.from_user.id}, 
            {"$set": {"username": message.from_user.username}}, 
            upsert=True
        )
        await client.set_bot_commands([
            BotCommand("make_test", "नया टेस्ट बनाएं"),
            BotCommand("manage", "टेस्ट मैनेज करें"),
            BotCommand("sheet_backup", "टेस्ट डेटा Google Sheet में लें"),
            BotCommand("stats", "बॉट के आँकड़े")
        ])
        await message.reply_text("👋 नमस्कार! Menu से कमांड चुनें।")
        logger.info("✅ Replied to /start successfully.")
    except Exception as e:
        logger.error(f"❌ Error in start command: {e}")
        await message.reply_text("⚠️ बॉट डेटाबेस से कनेक्ट नहीं हो पा रहा है।")

if __name__ == "__main__":
    logger.info("🚀 Starting Flask Server in background...")
    threading.Thread(target=run_flask, daemon=True).start()
    
    logger.info("🤖 Starting Pyrogram Bot...")
    app.run()

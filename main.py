import asyncio
import threading

# 👇 Python 3.14 Event Loop Fix
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from pyrogram import Client, filters

# Logging Setup
logging.basicConfig(level=logging.INFO)

# Render Environment Variables
API_ID_RAW = os.getenv("API_ID")
API_ID = int(API_ID_RAW) if API_ID_RAW and API_ID_RAW.isdigit() else None
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Flask App Initialization
flask_app = Flask(__name__)
CORS(flask_app)

@flask_app.route("/")
def home():
    return jsonify({"status": "Startup Bot & Web API is running successfully!"})

def run_flask():
    flask_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

# Pyrogram Bot Initialization
app = Client(
    "StartupBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# 🤖 Bot Message / Command Handler
@app.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text("👋 Hello! Main live hoon aur aapka bot perfectly kaam kar raha hai!")

@app.on_message(filters.text & ~filters.command("start"))
async def echo_message(client, message):
    await message.reply_text(f"Aapne kaha: {message.text}")

async def main():
    # Flask background thread start karein
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    logging.info("🌐 Flask server started on port 5000")

    # Pyrogram Bot start karein
    await app.start()
    logging.info("🤖 Telegram Bot started successfully...")
    
    # Bot ko chalate rakhne ke liye infinite wait
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.info("🛑 Bot stopped by user.")

import asyncio
import threading

# 👇 Yeh line Pyrogram import hone se pehle event loop set kar degi (Python 3.14 Fix)
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import logging
from flask import Flask, jsonify
from flask_cors import CORS
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN

# Logging Setup
logging.basicConfig(level=logging.INFO)

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

async def main():
    # Flask ko background thread mein start karein
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    logging.info("🌐 Flask server started on port 5000")

    # Pyrogram Bot start karein
    await app.start()
    logging.info("🤖 Telegram Bot started successfully...")
    
    # Bot ko chalate rakhne ke liye infinite await
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.info("🛑 Bot stopped by user.")

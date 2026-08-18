from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, ADMIN_USER_ID

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["startup_db"]
tests_col = db["tests"]

# Step 1: /maketest command se coaching list dikhana
@Client.on_message(filters.command("maketest") & filters.user(ADMIN_USER_ID))
async def start_make_test(client, message):
    # Database se saari unique coachings fetch karein
    coachings = await tests_col.distinct("coaching_name")
    
    keyboard = []
    for coaching in coachings:
        keyboard.append([InlineKeyboardButton(f"📁 {coaching}", callback_data=f"coach_{coaching}")])
    
    # Nayi coaching add karne ka option
    keyboard.append([InlineKeyboardButton("➕ Add New Coaching", callback_data="add_new_coaching")])
    
    await message.reply(
        "🎯 **Test Creation Flow**\n\nKripya niche di gayi Coaching select karein ya nayi add karein:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Step 2: Coaching select hone par Exam names dikhana
@Client.on_callback_query(filters.regex("^coach_") & filters.user(ADMIN_USER_ID))
async def select_exam(client, callback_query):
    coaching_name = callback_query.data.split("_", 1)[1]
    
    # Us coaching ke under ke exams fetch karein
    exams = await tests_col.distinct("exam_name", {"coaching_name": coaching_name})
    
    keyboard = []
    for exam in exams:
        keyboard.append([InlineKeyboardButton(f"📚 {exam}", callback_data=f"exam_{coaching_name}_{exam}")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_coach")])
    
    await callback_query.message.edit_text(
        f"🎯 Coaching: **{coaching_name}**\n\nAb Exam Name select karein:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

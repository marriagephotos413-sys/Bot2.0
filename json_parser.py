import json
from pyrogram import Client, filters
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, ADMIN_USER_ID

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["startup_db"]
tests_col = db["tests"]

# JSON Test File Upload Handler
@Client.on_message(filters.document & filters.user(ADMIN_USER_ID))
async def upload_test_json(client, message):
    if not message.document.file_name.endswith('.json'):
        await message.reply("❌ Kripya ek valid .json file hi upload karein.")
        return

    # File download karein
    file_path = await message.download()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        # JSON structure validation aur parsing
        coaching_name = test_data.get("coaching_name", "Default Coaching")
        exam_name = test_data.get("exam_name", "Default Exam")
        test_number = test_data.get("test_number", 1)
        questions = test_data.get("questions", [])

        # Database mein test store karna
        await tests_col.update_one(
            {
                "coaching_name": coaching_name,
                "exam_name": exam_name,
                "test_number": test_number
            },
            {
                "$set": {
                    "questions": questions,
                    "total_questions": len(questions)
                }
            },
            upsert=True
        )

        await message.reply(
            f"✅ **Test Successfully Uploaded!**\n\n"
            f"📁 Coaching: {coaching_name}\n"
            f"📚 Exam: {exam_name}\n"
            f"🔢 Test No: {test_number}\n"
            f"❓ Total Questions: {len(questions)}"
        )
        
    except Exception as e:
        await message.reply(f"❌ JSON parse karne mein error aayi: {str(e)}")

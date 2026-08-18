import gspread
from oauth2client.service_account import ServiceAccountCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI

# MongoDB Setup
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["startup_db"]
users_col = db["users"]
results_col = db["results"]

# Google Sheets Authentication Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope) # Google API JSON file
client_gs = gspread.authorize(creds)

# Google Sheet open karein (Sheet ka naam yahan dalein)
sheet = client_gs.open("Startup_Bot_Analytics").sheet1

# User Registration Track karne ka function
async def register_user(user_id, full_name, state, district, gender):
    user_data = {
        "user_id": user_id,
        "full_name": full_name,
        "state": state,
        "district": district,
        "gender": gender
    }
    
    # MongoDB mein save/update karein
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": user_data},
        upsert=True
    )
    
    # Google Sheet par data append karein
    try:
        sheet.append_row([str(user_id), full_name, state, district, gender])
    except Exception as e:
        print(f"Google Sheet Sync Error: {e}")

# Test Result Track karne ka function
async def save_test_result(user_id, coaching_name, exam_name, test_number, score, total_marks, time_taken):
    result_data = {
        "user_id": user_id,
        "coaching_name": coaching_name,
        "exam_name": exam_name,
        "test_number": test_number,
        "score": score,
        "total_marks": total_marks,
        "time_taken": time_taken
    }
    
    # MongoDB mein save karein
    await results_col.insert_one(result_data)

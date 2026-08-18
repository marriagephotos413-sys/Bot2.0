import asyncio
import os
import json
import uuid
import threading
import urllib.request
from flask import Flask, request, jsonify
from flask_cors import CORS
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, CallbackQuery, BotCommand
from pyrogram.errors import FloodWait, UserNotParticipant
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient

# 🌟 RENDER FIX: Python 3.14+ Event Loop 🌟
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# ==========================================
# 🌟 ENVIRONMENT VARIABLES 🌟
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = os.environ.get("API_ID") 
API_HASH = os.environ.get("API_HASH")
MONGO_URL = os.environ.get("MONGO_URL")

GITHUB_URL = "https://tests22mock-dot.github.io/MockTestUI"

# ==========================================
# 🗄️ DATABASE SETUP
# ==========================================
async_db_client = AsyncIOMotorClient(MONGO_URL)
tests_collection = async_db_client["MockTestDB"]["tests"]
channels_collection = async_db_client["MockTestDB"]["channels"]
users_collection = async_db_client["MockTestDB"]["users"] # NEW: User tracking
settings_collection = async_db_client["MockTestDB"]["settings"] # NEW: Force Sub tracking

sync_db_client = MongoClient(MONGO_URL)
sync_collection = sync_db_client["MockTestDB"]["tests"]

user_steps = {}
failed_transfers = {} 

# ==========================================
# 🌐 FLASK API (With Attempts Tracker)
# ==========================================
web_app = Flask(__name__)
CORS(web_app)

@web_app.route('/')
def home(): return "✅ Mock Test Bot & API is Live!"

@web_app.route('/api/get_test', methods=['GET'])
def get_test():
    test_id = request.args.get('id')
    test_data = sync_collection.find_one({"test_id": test_id}, {"_id": 0})
    if not test_data: return jsonify({"error": "Not found"}), 404
    
    sync_collection.update_one({"test_id": test_id}, {"$inc": {"attempts": 1}})
    
    d, q = test_data["details"], test_data["questions"]
    total_qs = sum(len(s["questions"]) for s in q)
    return jsonify({
        "questions": q, "time": int(d.get("time", 15)), 
        "total_qs": total_qs, "max_marks": total_qs * float(d.get("pos", 2.0)),
        "pos": float(d.get("pos", 2.0)), "neg": float(d.get("neg", 0.25))
    })

def run_flask():
    web_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# ==========================================
# 🤖 PREMIUM DESIGN GENERATOR
# ==========================================
def get_premium_design(data, total_qs):
    t_type = data.get("type", "COACHING")
    f1 = data.get("field1", "").upper()
    exam = data.get("exam", "")
    
    if t_type == "COACHING":
        header = f"🔥 **{f1}** 🔥"
        type_str = data.get("paid_type", "Paid Test Series")
    elif t_type == "PYQ":
        header = f"📚 **PREVIOUS YEAR QUESTION (PYQ)** 📚"
        type_str = "Original Official Paper"
    else:
        header = f"⚡ **MINI MOCK TEST - {f1}** ⚡"
        type_str = "Topic Wise Practice"

    msg = (f"{header}\n\n"
           f"🎯 **Exam:** {exam}\n"
           f"🏷 **Type:** {type_str}\n"
           f"📅 **Date:** {data.get('date', '')} | **No:** {data.get('test_no', '')}\n"
           f"📝 **Total Questions:** {total_qs}\n"
           f"⏱ **Duration:** {data.get('time', 15)} Mins\n"
           f"📊 **Marks:** +{data.get('pos', 2.0)} / -{data.get('neg', 0.25)}\n\n"
           f"👇 अपना पसंदीदा परीक्षा पैटर्न चुनें और टेस्ट शुरू करें:")
    return msg

def generate_smart_html(test_data):
    exam = test_data["details"].get("exam", "Mock Test")
    html = f"""<!DOCTYPE html>
    <html lang="hi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{exam} - Solutions</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background: #f5f5f5; color: #333; line-height: 1.6; }}
            .container {{ max-width: 800px; margin: auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            h1 {{ text-align: center; color: #1a237e; border-bottom: 2px solid #1a237e; padding-bottom: 15px; margin-bottom: 30px; }}
            .q-box {{ border: 1px solid #e0e0e0; padding: 20px; margin-bottom: 25px; border-radius: 10px; background: #fff; }}
            .q-txt {{ font-size: 16px; font-weight: bold; margin-bottom: 15px; color: #111; }}
            .opt {{ margin-bottom: 8px; font-size: 15px; padding: 10px; border-radius: 6px; border: 1px solid #eee; background: #fafafa; }}
            .correct {{ background: #e8f5e9; border-color: #4caf50; color: #2e7d32; font-weight: bold; }}
            .exp {{ margin-top: 15px; padding: 15px; background: #f8f9fa; border-left: 5px solid #1a237e; font-size: 14px; border-radius: 4px; color: #444; }}
            .promo {{ text-align: center; margin-top: 40px; padding: 25px 20px; background: #e8eaf6; border: 1px solid #c5cae9; border-radius: 12px; }}
            .btn-container {{ display: flex; flex-direction: column; gap: 12px; align-items: center; margin-top: 15px; }}
            .tg-btn {{ text-decoration: none; display: block; width: 100%; max-width: 350px; padding: 14px; font-size: 16px; font-weight: bold; border-radius: 8px; color: white !important; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .btn-update {{ background: #1e88e5; }}
            .btn-backup {{ background: #0288d1; }}
            .print-btn {{ display: block; width: 100%; max-width: 300px; margin: 0 auto 20px auto; padding: 15px; background: #e53935; color: white; text-align: center; text-decoration: none; font-size: 16px; font-weight: bold; border-radius: 8px; border: none; cursor: pointer; }}
            @media print {{ .no-print {{ display: none !important; }} body {{ padding: 0; background: #fff; }} .container {{ box-shadow: none; padding: 0; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="no-print" style="margin-bottom: 20px; text-align: center;">
                <button class="print-btn" onclick="window.print()">📥 Save as PDF / Print</button>
            </div>
            <h1>{exam} - Answer Key & Solutions</h1>
    """
    opt_prefix = ['A', 'B', 'C', 'D']
    global_q = 1
    for sec in test_data.get("questions", []):
        sec_name = sec.get("section", "")
        html += f"<h2 style='color: #e65100; margin-top: 30px; border-bottom: 1px dashed #ccc; padding-bottom: 10px;'>{sec_name}</h2>\n"
        for q in sec.get("questions", []):
            q_text = q.get('text', '')
            html += f"<div class='q-box'><div class='q-txt'>Q{global_q}. {q_text}</div>\n"
            for i, opt in enumerate(q.get("options", [])):
                if i == q.get("correct"):
                    html += f"<div class='opt correct'>{opt_prefix[i]}. {opt} ✅ (Correct Answer)</div>\n"
                else:
                    html += f"<div class='opt'>{opt_prefix[i]}. {opt}</div>\n"
            exp = q.get("exp", "")
            if exp: html += f"<div class='exp'><strong>Explanation:</strong><br>{exp}</div>\n"
            html += "</div>\n"
            global_q += 1
            
    html += """
            <div class="promo no-print">
                <h3 style="margin-top: 0; margin-bottom: 10px; color: #d32f2f; font-size: 18px;">🔥 आज ही हमारा चैनल जॉइन करें और अनलिमिटेड प्रैक्टिस पाएं!</h3>
                <div class="btn-container">
                    <a href="https://t.me/+N9ijRyP-zYtjNTg1" class="tg-btn btn-update" target="_blank">📢 Join Test Updates Channel</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

async def send_test_to_channel(test_data, cid, client):
    tid = test_data["test_id"]
    total_qs = sum(len(s["questions"]) for s in test_data["questions"])
    msg_text = get_premium_design(test_data["details"], total_qs)
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💻 Start Test (TCS Pattern)", url=f"{GITHUB_URL}/tcs.html?id={tid}")],
        [InlineKeyboardButton("📱 Start Test (Eduquity)", url=f"{GITHUB_URL}/eduquity.html?id={tid}")],
        [InlineKeyboardButton("📢 Join Mock Update Channel", url="https://t.me/+N9ijRyP-zYtjNTg1")]
    ])
    
    exam_name = test_data["details"].get("exam", "Mock_Test").replace(" ", "_")
    file_name = f"{exam_name}_{tid}_Solutions.html"
    
    try:
        await client.send_message(chat_id=int(cid), text=msg_text, reply_markup=kb)
        html_content = generate_smart_html(test_data)
        with open(file_name, "w", encoding="utf-8") as f: f.write(html_content)
        
        await client.send_document(
            chat_id=int(cid),
            document=file_name,
            caption=f"📄 **{test_data['details'].get('exam', 'Mock Test')} - Full Solutions**\n💡 *इस टेस्ट के सभी सवालों और सही जवाबों की स्मार्ट फाइल।*"
        )
        if os.path.exists(file_name): os.remove(file_name)
        return True
    except FloodWait as e:
        if os.path.exists(file_name): os.remove(file_name)
        raise e  
    except Exception as e:
        if os.path.exists(file_name): os.remove(file_name)
        return False

async def run_bulk_transfer(client, status_msg, dest_id, uid, tests):
    total = len(tests)
    success = 0
    failed = []
    
    for i, test in enumerate(tests):
        if i % 3 == 0 and i > 0:
            try:
                await status_msg.edit_text(f"⏳ **ट्रांसफर चल रहा है...**\n\n📦 कुल टेस्ट: `{total}`\n✅ सफलता: `{success}`\n❌ फेल/कैंसिल: `{len(failed)}`\n⏳ बाकी: `{total - i}`")
            except: pass
        
        try:
            res = await send_test_to_channel(test, dest_id, client)
            if res:
                success += 1
                await tests_collection.update_one({"test_id": test["test_id"]}, {"$set": {"channel_id": int(dest_id)}})
            else:
                failed.append(test)
            await asyncio.sleep(4) 
        except FloodWait as e:
            await asyncio.sleep(e.value + 5)
            failed.append(test) 
        except Exception:
            failed.append(test)
            await asyncio.sleep(2)
            
    kb = None
    if failed:
        failed_transfers[uid] = {"tests": failed, "dest_id": dest_id}
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 फेल हुए टेस्ट दोबारा भेजें (Retry)", callback_data=f"retry_tf:{uid}")]])
    else:
        if uid in failed_transfers: del failed_transfers[uid]
        
    final_text = f"✅ **ट्रांसफर प्रक्रिया पूरी हो गई!**\n\n🎯 कुल टेस्ट: `{total}`\n✅ सफलतापूर्वक: `{success}`\n❌ फेल/कैंसिल: `{len(failed)}`"
    
    try: 
        await status_msg.edit_text(final_text, reply_markup=kb)
    except: 
        await client.send_message(uid, final_text, reply_markup=kb)

# ==========================================
# 🛠️ ADMIN COMMANDS & BOT MENU
# ==========================================
app = Client("MockTestBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = message.from_user.id
    # 🌟 TRACK USER IN DB 🌟
    await users_collection.update_one({"user_id": user_id}, {"$set": {"username": message.from_user.username, "first_name": message.from_user.first_name}}, upsert=True)
    
    # 🌟 FORCE SUB CHECK 🌟
    fsub_data = await settings_collection.find_one({"_id": "fsub"})
    if fsub_data and fsub_data.get("channel_id"):
        try:
            await client.get_chat_member(fsub_data["channel_id"], user_id)
        except UserNotParticipant:
            ch_link = fsub_data["channel_id"]
            if not str(ch_link).startswith("@") and not str(ch_link).startswith("http"):
                ch_link = "Private Channel (Ask Admin)"
            return await message.reply_text(f"❌ **कृपया पहले हमारे चैनल से जुड़ें, फिर /start दबाएं।**\n🔗 चैनल लिंक: {ch_link}")
        except Exception:
            pass # Ignore if bot is not admin

    await client.set_bot_commands([
        BotCommand("make_test", "नया टेस्ट बनाएं"),
        BotCommand("manage", "टेस्ट मैनेज या डिलीट करें"),
        BotCommand("add_channel", "नया चैनल जोड़ें"),
        BotCommand("remove_channel", "चैनल हटाएँ"),
        BotCommand("transfer", "टेस्ट दूसरे चैनल में भेजें"),
        BotCommand("resend", "पुराने टेस्ट दोबारा भेजें"),
        BotCommand("delete", "टेस्ट डिलीट करें"),
        BotCommand("addforcechannel", "Force Sub चालू करें"),
        BotCommand("removeforcechannel", "Force Sub बंद करें"),
        BotCommand("listchannel", "सभी सेव चैनल देखें"),
        BotCommand("listuser", "बॉट के यूज़र्स देखें"),
        BotCommand("listtestwithchannel", "टेस्ट और उनके चैनल देखें"),
        BotCommand("stats", "बॉट के आँकड़े देखें"),
        BotCommand("report", "टेस्ट रिपोर्ट"),
        BotCommand("db", "डेटाबेस स्टोरेज"),
        BotCommand("backup", "डेटाबेस बैकअप")
    ])
    await message.reply_text("👋 नमस्कार! टेस्ट बनाने और मैनेज करने के लिए Menu का इस्तेमाल करें।")

# ==========================================
# 🚀 NEW FEATURES COMMANDS
# ==========================================

@app.on_message(filters.command("addforcechannel") & filters.private)
async def add_force_sub(client, message):
    if len(message.command) < 2:
        return await message.reply_text("⚠️ **इस्तेमाल का तरीका:** `/addforcechannel @YourChannelUsername`\n(नोट: बॉट चैनल में एडमिन होना चाहिए)")
    ch_id = message.text.split(None, 1)[1]
    await settings_collection.update_one({"_id": "fsub"}, {"$set": {"channel_id": ch_id}}, upsert=True)
    await message.reply_text(f"✅ **Force Sub Channel सेट कर दिया गया है:** `{ch_id}`")

@app.on_message(filters.command("removeforcechannel") & filters.private)
async def remove_force_sub(client, message):
    await settings_collection.delete_one({"_id": "fsub"})
    await message.reply_text("✅ **Force Sub Channel सफलतापूर्वक हटा दिया गया है।**")

@app.on_message(filters.command("listchannel") & filters.private)
async def list_saved_channels(client, message):
    channels = await channels_collection.find().to_list(length=None)
    if not channels: return await message.reply_text("❌ डेटाबेस में कोई चैनल सेव नहीं है!")
    
    text = "📢 **सेव किए गए सभी चैनल्स की लिस्ट:**\n\n"
    for ch in channels:
        text += f"🔹 **{ch['name']}**\n└ ID: `{ch['chat_id']}`\n\n"
    await message.reply_text(text)

@app.on_message(filters.command("listuser") & filters.private)
async def list_bot_users(client, message):
    users = await users_collection.find().to_list(length=None)
    count = len(users)
    if count == 0: return await message.reply_text("❌ कोई यूज़र नहीं मिला!")
    
    wait = await message.reply_text("⏳ यूज़र्स की लिस्ट तैयार की जा रही है...")
    with open("users_list.txt", "w", encoding="utf-8") as f:
        f.write(f"Total Users: {count}\n\n")
        for u in users:
            f.write(f"ID: {u['user_id']} | Username: @{u.get('username', 'None')} | Name: {u.get('first_name', 'None')}\n")
            
    await message.reply_document("users_list.txt", caption=f"👥 **बॉट के कुल यूज़र्स:** `{count}`")
    os.remove("users_list.txt")
    await wait.delete()

@app.on_message(filters.command("listtestwithchannel") & filters.private)
async def list_tests_with_channels(client, message):
    tests = await tests_collection.find().to_list(length=None)
    if not tests: return await message.reply_text("❌ डेटाबेस में कोई टेस्ट नहीं है!")
    
    wait = await message.reply_text("⏳ टेस्ट्स और चैनल्स की रिपोर्ट बन रही है...")
    with open("tests_channels.txt", "w", encoding="utf-8") as f:
        f.write(f"Total Tests: {len(tests)}\n\n")
        for t in tests:
            exam = t['details'].get('exam', 'N/A')
            ch_id = t.get("channel_id", "Not Assigned (No Channel)")
            f.write(f"Test ID: {t['test_id']} | Exam: {exam} | Channel ID: {ch_id}\n")
            
    await message.reply_document("tests_channels.txt", caption=f"📦 **कुल टेस्ट और उनके चैनल्स:** `{len(tests)}`")
    os.remove("tests_channels.txt")
    await wait.delete()

# ==========================================
# 📊 EXISTING COMMANDS 
# ==========================================

@app.on_message(filters.command("stats") & filters.private)
async def bot_stats(client, message):
    total = await tests_collection.count_documents({})
    c_tests = await tests_collection.count_documents({"details.type": "COACHING"})
    p_tests = await tests_collection.count_documents({"details.type": "PYQ"})
    m_tests = await tests_collection.count_documents({"details.type": "MINI MOCK"})
    ch_count = await channels_collection.count_documents({})
    u_count = await users_collection.count_documents({})
    await message.reply_text(f"📊 **BOT REAL-TIME STATS** 📊\n\n👥 Total Users: {u_count}\n📁 Total Tests: {total}\n📢 Total Channels: {ch_count}\n\n🏢 Coaching Tests: {c_tests}\n📚 PYQ Papers: {p_tests}\n⚡ Mini Mocks: {m_tests}")

@app.on_message(filters.command("report") & filters.private)
async def attempts_report(client, message):
    wait = await message.reply_text("📊 **डेटा एनालाइज़ किया जा रहा है...**")
    pipeline = [
        {"$group": {"_id": "$details.exam", "total_attempts": {"$sum": {"$ifNull": ["$attempts", 0]}}, "test_count": {"$sum": 1}}},
        {"$sort": {"total_attempts": -1}}
    ]
    results = await tests_collection.aggregate(pipeline).to_list(length=None)
    if not results: return await wait.edit_text("❌ अभी तक कोई डेटा मौजूद नहीं है!")
        
    text = "📈 **EXAM-WISE TEST ATTEMPTS REPORT** 📈\n\n"
    total_all_attempts = 0
    for res in results:
        exam_name = res["_id"] if res["_id"] else "Unknown Exam"
        attempts = res.get("total_attempts", 0)
        t_count = res.get("test_count", 0)
        total_all_attempts += attempts
        text += f"🎯 **{exam_name}**\n├ 📝 Tests Published: `{t_count}`\n└ 👁 Total Attempts: `{attempts} Bar`\n\n"
        
    text += f"➖➖➖➖➖➖➖➖\n🔥 **Overall Total Attempts:** `{total_all_attempts}`"
    await wait.edit_text(text)

@app.on_message(filters.command("db") & filters.private)
async def db_storage(client, message):
    wait = await message.reply_text("⏳ **MongoDB से स्टोरेज डेटा मंगाया जा रहा है...**")
    try:
        db = async_db_client["MockTestDB"]
        stats = await db.command("dbstats")
        data_size = stats.get("dataSize", 0) / (1024 * 1024)
        storage_size = stats.get("storageSize", 0) / (1024 * 1024)
        index_size = stats.get("indexSize", 0) / (1024 * 1024)
        total_limit = 512.0
        used_percent = (storage_size / total_limit) * 100
        
        filled = int(used_percent / 10)
        empty = 10 - filled
        progress_bar = f"[{'█' * filled}{'░' * empty}]"

        text = (f"🗄 **MongoDB Storage Status** 🗄\n\n"
                f"💾 **Data Size:** `{data_size:.2f} MB`\n"
                f"🗂 **Index Size:** `{index_size:.2f} MB`\n"
                f"💽 **Total Used Space:** `{storage_size:.2f} MB`\n\n"
                f"📊 **Free Tier Storage (512 MB):**\n"
                f"{progress_bar} `{used_percent:.2f}% Used`")
        await wait.edit_text(text)
    except Exception as e:
        await wait.edit_text(f"❌ Error: {e}")

@app.on_message(filters.command("backup") & filters.private)
async def db_backup(client, message):
    wait = await message.reply_text("⏳ बैकअप तैयार हो रहा है...")
    all_data = await tests_collection.find({}, {"_id": 0}).to_list(length=None)
    with open("backup.json", "w", encoding="utf-8") as f: json.dump(all_data, f, indent=4)
    await message.reply_document("backup.json", caption="📂 Database Backup (.json)")
    os.remove("backup.json")
    await wait.delete()

@app.on_message(filters.command("add_channel") & filters.private)
async def add_channel_cmd(client, message: Message):
    user_steps[message.from_user.id] = {"step": "ASK_CH_NAME", "data": {}}
    await message.reply_text("📢 **चैनल का नाम बताएं?**\n(जैसे: SSC GD 2026 Channel)")

@app.on_message(filters.command("remove_channel") & filters.private)
async def remove_channel_cmd(client, message: Message):
    channels = await channels_collection.find().to_list(length=None)
    if not channels: return await message.reply_text("❌ डेटाबेस में कोई चैनल नहीं है!")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"❌ {ch['name']}", callback_data=f"rmch:{ch['chat_id']}")] for ch in channels])
    await message.reply_text("🗑 **डिलीट करने के लिए चैनल पर क्लिक करें:**", reply_markup=kb)

@app.on_message(filters.command("transfer") & filters.private)
async def transfer_tests(client, message):
    channels = await channels_collection.find().to_list(length=None)
    if not channels: return await message.reply_text("❌ पहले `/add_channel` से चैनल जोड़ें!")
    
    kb = [[InlineKeyboardButton(f"📤 {ch['name']}", callback_data=f"tf_src:{ch['chat_id']}")] for ch in channels]
    kb.append([InlineKeyboardButton("📦 सभी पुराने टेस्ट (All Database Tests)", callback_data="tf_src:ALL")])
    await message.reply_text("📤 **वह चैनल चुनें जो बैन हो गया है (Source Channel):**", reply_markup=InlineKeyboardMarkup(kb))

@app.on_message(filters.command("resend") & filters.private)
async def resend_tests(client, message):
    if len(message.command) < 2: return await message.reply_text("⚠️ **इस्तेमाल का तरीका:** `/resend ExamName`")
    exam_query = message.text.split(None, 1)[1]
    wait_msg = await message.reply_text(f"🔍 `{exam_query}` ढूंढे जा रहे हैं...")
    tests = await tests_collection.find({"details.exam": {"$regex": exam_query, "$options": "i"}}).to_list(length=None)
    if not tests: return await wait_msg.edit_text("❌ कोई टेस्ट नहीं मिला!")
    await wait_msg.edit_text(f"✅ **{len(tests)}** टेस्ट मिल गए हैं। सीधे यहाँ भेज रहा हूँ...")
    for test in tests:
        tid = test["test_id"]
        total_qs = sum(len(s["questions"]) for s in test["questions"])
        msg = get_premium_design(test["details"], total_qs)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💻 TCS", web_app=WebAppInfo(url=f"{GITHUB_URL}/tcs.html?id={tid}")),
             InlineKeyboardButton("📱 Eduquity", web_app=WebAppInfo(url=f"{GITHUB_URL}/eduquity.html?id={tid}"))],
            [InlineKeyboardButton("🚀 Publish (चैनल चुनें)", callback_data=f"preview:pub:{tid}")]
        ])
        try: 
            await message.reply_text(msg, reply_markup=kb)
            await asyncio.sleep(1)
        except: pass

@app.on_message(filters.command(["manage", "delete"]) & filters.private)
async def manage_cmd(client, message):
    await message.reply_text("🛠 **टेस्ट मैनेज या डिलीट कैसे करें?**\n\nजिस टेस्ट को डिलीट/मैनेज करना है, उसकी ID (जैसे: `TEST_123ABC`) मुझे भेजें।")

# ==========================================
# 📝 TEST CREATION FLOW
# ==========================================
async def ask_next(client, uid, step, edit=None):
    data = user_steps[uid]["data"]
    test_type = data.get("type")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back (रद्द करें)", callback_data=f"goback:{step}")]])
    
    msg = ""
    if step == "ASK_F1":
        if test_type == "COACHING": msg = "🏢 **कोचिंग का नाम बताएं?**\n(जैसे: RWA, Testbook)"
        elif test_type == "MINI MOCK": msg = "📝 **विषय (Subject) बताएं?**\n(जैसे: MATHS, REASONING)"
        else: msg = "📅 **परीक्षा का साल (Year) बताएं?**\n(जैसे: 2024)"
    elif step == "ASK_EXAM": msg = "🎯 **टारगेट एग्जाम का नाम बताएं?**\n(जैसे: SSC GD 2026)"
    elif step == "ASK_PAID": msg = "🏷 **टेस्ट का प्रकार बताएं?**\n(जैसे: Paid Test Series)"
    elif step == "ASK_NO": msg = "🔢 **टेस्ट नंबर या शिफ्ट बताएं?**\n(जैसे: Mock 01)"
    elif step == "ASK_DATE": msg = "📅 **टेस्ट की तारीख बताएं?**\n(जैसे: 10 May 2026)"
    elif step == "ASK_POS": msg = "✅ **सही जवाब के मार्क्स?**\n(जैसे: 2)"
    elif step == "ASK_NEG": msg = "❌ **नेगेटिव मार्किंग?**\n(जैसे: 0.50)"
    elif step == "ASK_TIME": msg = "⏱ **समय (Minutes)?**\n(जैसे: 15)"
    elif step == "ASK_JSON": msg = "📂 **अब टेस्ट की .json फाइल सेंड करें:**"

    if edit: await edit.edit_text(msg, reply_markup=kb)
    else: await client.send_message(uid, msg, reply_markup=kb)

@app.on_message(filters.command("make_test") & filters.private)
async def make_test(client, message):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏢 Coaching", callback_data="set:COACHING")],
                               [InlineKeyboardButton("📚 PYQ", callback_data="set:PYQ")],
                               [InlineKeyboardButton("⏱ Mini Mock", callback_data="set:MINI MOCK")]])
    user_steps[message.from_user.id] = {"step": "TYPE", "data": {}}
    await message.reply_text("🎯 **नया टेस्ट बनाने के लिए प्रकार चुनें:**", reply_markup=kb)

@app.on_callback_query(filters.regex("^(set:|goback:|preview:|pubto:|confirm:|delete:|tf_src:|tf_dest:|retry_tf:|rmch:)"))
async def callbacks(client, q):
    uid = q.from_user.id
    cmd = q.data.split(":")
    
    if cmd[0] == "set":
        user_steps[uid]["data"]["type"] = cmd[1]
        user_steps[uid]["step"] = "ASK_F1"
        await ask_next(client, uid, "ASK_F1", q.message)

    elif cmd[0] == "goback":
        if uid in user_steps: del user_steps[uid]
        await q.message.edit_text("❌ प्रक्रिया रद्द कर दी गई।")

    elif cmd[0] == "rmch":
        cid = int(cmd[1])
        await channels_collection.delete_one({"chat_id": cid})
        await q.message.edit_text("✅ **चैनल सफलतापूर्वक डेटाबेस से हटा दिया गया!**")

    elif cmd[0] == "tf_src":
        src_id = cmd[1]
        channels = await channels_collection.find().to_list(length=None)
        kb = []
        for ch in channels:
            if str(ch['chat_id']) != src_id:
                kb.append([InlineKeyboardButton(f"📥 {ch['name']}", callback_data=f"tf_dest:{src_id}:{ch['chat_id']}")])
        kb.append([InlineKeyboardButton("🔙 Cancel", callback_data="preview:can:0")])
        await q.message.edit_text("📥 **अब वह नया चैनल चुनें जहाँ टेस्ट ट्रांसफर करने हैं:**", reply_markup=InlineKeyboardMarkup(kb))

    elif cmd[0] == "tf_dest":
        src_id, dest_id = cmd[1], cmd[2]
        status_msg = await q.message.edit_text("⏳ **टेस्ट ढूँढे जा रहे हैं...**")
        
        if src_id == "ALL": tests = await tests_collection.find({}).to_list(length=None)
        else: tests = await tests_collection.find({"channel_id": int(src_id)}).to_list(length=None)
            
        if not tests: return await status_msg.edit_text("❌ सोर्स चैनल के कोई टेस्ट डेटाबेस में नहीं मिले!")
        await status_msg.edit_text(f"🚀 कुल **{len(tests)}** टेस्ट मिले हैं।")
        asyncio.create_task(run_bulk_transfer(client, status_msg, dest_id, uid, tests))

    elif cmd[0] == "retry_tf":
        target_uid = int(cmd[1])
        if target_uid in failed_transfers and failed_transfers[target_uid]["tests"]:
            tests_to_retry = failed_transfers[target_uid]["tests"]
            dest_id = failed_transfers[target_uid]["dest_id"]
            failed_transfers[target_uid]["tests"] = [] 
            status_msg = await q.message.edit_text(f"🔄 **{len(tests_to_retry)}** फेल हुए टेस्ट्स को दोबारा भेजने की कोशिश की जा रही है...")
            asyncio.create_task(run_bulk_transfer(client, status_msg, dest_id, target_uid, tests_to_retry))
        else:
            await q.message.edit_text("❌ कोई फेल हुआ टेस्ट नहीं मिला।")

    elif cmd[0] == "preview":
        if cmd[1] == "pub":
            tid = cmd[2]
            channels = await channels_collection.find().to_list(length=None)
            if not channels: return await q.message.edit_text("❌ पहले `/add_channel` कमांड से चैनल जोड़ें।")
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(ch["name"], callback_data=f"pubto:{tid}:{ch['chat_id']}")] for ch in channels])
            await q.message.edit_text("📢 **चैनल चुनें जहाँ टेस्ट पब्लिश करना है:**", reply_markup=kb)
        elif cmd[1] == "can":
            await q.message.edit_text("❌ प्रक्रिया रद्द कर दी गई।")

    elif cmd[0] == "pubto":
        tid, cid = cmd[1], cmd[2]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ कन्फर्म - पब्लिश करें", callback_data=f"confirm:{tid}:{cid}")],
            [InlineKeyboardButton("❌ कैंसिल", callback_data="preview:can:0")]
        ])
        await q.message.edit_text("❓ **क्या आप पक्का इस चैनल में पब्लिश करना चाहते हैं?**", reply_markup=kb)

    elif cmd[0] == "confirm":
        tid, cid = cmd[1], cmd[2]
        test = await tests_collection.find_one({"test_id": tid})
        if not test: return await q.message.edit_text("❌ टेस्ट डेटाबेस में नहीं मिला।")
        
        success = await send_test_to_channel(test, cid, client)
        if success:
            await tests_collection.update_one({"test_id": tid}, {"$set": {"channel_id": int(cid)}})
            await q.message.edit_text(f"✅ **सफलतापूर्वक चैनल में पब्लिश हो गया!**\n🔗 Test ID: `{tid}`")
        else:
            await q.message.edit_text(f"❌ **एरर:** बॉट चैनल में एडमिन नहीं है या ID गलत है।")

    elif cmd[0] == "delete":
        tid = cmd[1]
        await tests_collection.delete_one({"test_id": tid})
        await q.message.edit_text(f"🗑 **टेस्ट सफलतापूर्वक डेटाबेस से डिलीट कर दिया गया है!**\nID: `{tid}`")

@app.on_message(filters.text & filters.private & ~filters.command(["start", "make_test", "stats", "backup", "db", "report", "add_channel", "remove_channel", "transfer", "resend", "delete", "manage", "addforcechannel", "removeforcechannel", "listchannel", "listuser", "listtestwithchannel"]))
async def text_handler(client, message):
    uid = message.from_user.id
    if message.text.startswith("TEST_"):
        tid = message.text.strip()
        test = await tests_collection.find_one({"test_id": tid})
        if not test: return await message.reply_text("❌ यह Test ID डेटाबेस में नहीं मिली।")
        
        total_qs = sum(len(s["questions"]) for s in test["questions"])
        msg = get_premium_design(test["details"], total_qs)
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💻 TCS", web_app=WebAppInfo(url=f"{GITHUB_URL}/tcs.html?id={tid}")),
             InlineKeyboardButton("📱 Eduquity", web_app=WebAppInfo(url=f"{GITHUB_URL}/eduquity.html?id={tid}"))],
            [InlineKeyboardButton("🚀 चैनल में पब्लिश करें", callback_data=f"preview:pub:{tid}")],
            [InlineKeyboardButton("🗑 टेस्ट डिलीट करें (Delete)", callback_data=f"delete:{tid}")]
        ])
        return await message.reply_text(f"🛠 **Manage Test:**\n\n{msg}", reply_markup=kb)

    if uid not in user_steps: return
    
    step = user_steps[uid]["step"]
    if step == "ASK_CH_NAME":
        user_steps[uid]["data"]["ch_name"] = message.text
        user_steps[uid]["step"] = "ASK_CH_ID"
        await message.reply_text("🔑 **अब चैनल का ID बताएं?** (जैसे: -1001234567890)")
        return
    elif step == "ASK_CH_ID":
        try:
            ch_id = int(message.text)
            await channels_collection.update_one({"chat_id": ch_id}, {"$set": {"name": user_steps[uid]["data"]["ch_name"]}}, upsert=True)
            await message.reply_text("✅ **चैनल सफलतापूर्वक जुड़ गया!**")
            del user_steps[uid]
        except ValueError: await message.reply_text("❌ गलत ID! सिर्फ नंबर भेजें:")
        return

    steps = ["ASK_F1", "ASK_EXAM", "ASK_PAID", "ASK_NO", "ASK_DATE", "ASK_POS", "ASK_NEG", "ASK_TIME", "ASK_JSON"]
    if step in steps:
        key = step.replace("ASK_", "").lower()
        if key == "f1": key = "field1"
        if key == "paid": key = "paid_type"
        if key == "no": key = "test_no"
        user_steps[uid]["data"][key] = message.text
        
        next_idx = steps.index(step) + 1
        if next_idx < len(steps):
            next_step = steps[next_idx]
            if next_step == "ASK_PAID" and user_steps[uid]["data"]["type"] != "COACHING": next_step = "ASK_NO"
            user_steps[uid]["step"] = next_step
            await ask_next(client, uid, next_step)

@app.on_message(filters.document & filters.private)
async def json_handler(client, message):
    uid = message.from_user.id
    if uid not in user_steps or user_steps[uid]["step"] != "ASK_JSON": return
    
    wait = await message.reply_text("⏳ टेस्ट तैयार किया जा रहा है...")
    tid = f"TEST_{uuid.uuid4().hex[:6].upper()}"
    path = await message.download()
    with open(path, 'r', encoding='utf-8') as f: q_data = json.load(f)
    os.remove(path)
    
    await tests_collection.insert_one({"test_id": tid, "details": user_steps[uid]["data"], "questions": q_data, "attempts": 0})
    msg = get_premium_design(user_steps[uid]["data"], sum(len(s["questions"]) for s in q_data))
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💻 TCS Pattern", web_app=WebAppInfo(url=f"{GITHUB_URL}/tcs.html?id={tid}")),
         InlineKeyboardButton("📱 Eduquity", web_app=WebAppInfo(url=f"{GITHUB_URL}/eduquity.html?id={tid}"))],
        [InlineKeyboardButton("🚀 Publish (चैनल चुनें)", callback_data=f"preview:pub:{tid}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"preview:can:0")]
    ])
    await wait.delete()
    await message.reply_text(f"👀 **यह आपके टेस्ट का Preview है। पहले चेक करें:**\n\n{msg}", reply_markup=kb)
    del user_steps[uid]

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()

import asyncio
import traceback
from pyrogram import filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
from config import OWNER_ID
from Extractor import app
from Extractor.core.mongo.usersdb import get_users

# ---------------------------------------------------------------- #

async def send_msg(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return 200, None
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        return await send_msg(user_id, message)
    except InputUserDeactivated:
        return 400, f"{user_id} : deactivated\n"
    except UserIsBlocked:
        return 400, f"{user_id} : blocked the bot\n"
    except PeerIdInvalid:
        return 400, f"{user_id} : user id invalid\n"
    except Exception as e:
        return 500, f"{user_id} : {str(e)}\n"
    

# ----------------------------Broadcast---------------------------- #
    
@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(client, message):
    ask_prompt = (
        "📢 **Broadcast (ब्रोडकास्ट) सर्विस में आपका स्वागत है!**\n\n"
        "👉 *कृपया वह मैसेज भेजें जिसे आप सभी यूज़र्स को भेजना चाहते हैं।*\n\n"
        "💡 **नोट:** आप Text, Photo, Video, Document या Forwarded Message कुछ भी भेज सकते हैं।\n"
        "(कैंसिल करने के लिए /cancel टाइप करें)"
    )
    
    try:
        broadcast_msg = await client.ask(message.chat.id, text=ask_prompt, timeout=120)
        
        if broadcast_msg.text and broadcast_msg.text.lower() == "/cancel":
            return await message.reply_text("❌ ब्रोडकास्ट कैंसिल कर दिया गया है।")
            
    except asyncio.TimeoutError:
        return await message.reply_text("❌ **टाइमआउट:** आपने मैसेज भेजने में बहुत देर कर दी। कृपया दोबारा `/broadcast` कमांड दें।")
    
    exmsg = await message.reply_text(
        "🔄 **Broadcasting Started...**\n\n"
        "कृपया प्रतीक्षा करें, मैं सभी यूज़र्स को मैसेज भेज रहा हूँ 🚀"
    )
    
    all_users = await get_users()
    if not all_users:
        await exmsg.edit_text("❌ Database में कोई यूज़र नहीं मिला!")
        return
        
    done_users = 0
    failed_users = 0
    failed_details = ""
    
    for user in all_users:
        status, error = await send_msg(user, broadcast_msg)
        if status == 200:
            done_users += 1
        else:
            failed_users += 1
            if error:
                failed_details += error
        await asyncio.sleep(0.1)
    
    broadcast_text = (
        "📊 **Broadcast Successfully Completed!** 🎉\n\n"
        f"✅ सफलता (Success): <code>{done_users}</code> users\n"
        f"❌ विफल (Failed): <code>{failed_users}</code> users\n\n"
    )
    
    if failed_users > 0:
        broadcast_text += (
            "⚠️ **Failure Details:**\n"
            f"<code>{failed_details[:1000]}</code>"
        )
    
    await exmsg.edit_text(broadcast_text)


# ----------------------------Forward Broadcast---------------------------- #

@app.on_message(filters.command("forward") & filters.user(OWNER_ID))
async def forward_broadcast(client, message):
    ask_prompt = (
        "🔁 **फॉरवर्ड ब्रोडकास्ट (Forward) सर्विस में आपका स्वागत है!**\n\n"
        "👉 *कृपया वह मैसेज भेजें (या किसी चैनल से फॉरवर्ड करें) जिसे आप सभी को फॉरवर्ड करना चाहते हैं।*\n\n"
        "💡 **नोट:** इससे यूज़र्स के पास 'Forwarded from...' का टैग जाएगा।\n"
        "(कैंसिल करने के लिए /cancel टाइप करें)"
    )
    
    try:
        forward_msg = await client.ask(message.chat.id, text=ask_prompt, timeout=120)
        
        if forward_msg.text and forward_msg.text.lower() == "/cancel":
            return await message.reply_text("❌ फॉरवर्ड ब्रोडकास्ट कैंसिल कर दिया गया है।")
            
    except asyncio.TimeoutError:
        return await message.reply_text("❌ **टाइमआउट:** आपने मैसेज भेजने में बहुत देर कर दी। कृपया दोबारा `/forward` कमांड दें।")
        
    exmsg = await message.reply_text(
        "🔄 **Forwarding Started...**\n\n"
        "कृपया प्रतीक्षा करें, मैं सभी यूज़र्स को फॉरवर्ड कर रहा हूँ 🚀"
    )
    
    users = await get_users()
    if not users:
        await exmsg.edit_text("❌ Database में कोई यूज़र नहीं मिला!")
        return
        
    done_users = 0
    failed_users = 0
    
    for user in users:
        try:
            await forward_msg.forward(int(user))
            done_users += 1
        except Exception:
            failed_users += 1
        await asyncio.sleep(0.1)
    
    await exmsg.edit_text(
        "📊 **Forward Broadcast Completed!** 🎉\n\n"
        f"✅ सफलता (Success): <code>{done_users}</code> users\n"
        f"❌ विफल (Failed): <code>{failed_users}</code> users"
    )


# ----------------------------Announce---------------------------- #
        
@app.on_message(filters.command("announce") & filters.user(OWNER_ID))
async def announced(client, message):
    ask_prompt = (
        "📢 **Announce (अनाउंस) सर्विस में आपका स्वागत है!**\n\n"
        "👉 *कृपया वह मैसेज भेजें जिसे आप अनाउंस करना चाहते हैं।*\n\n"
        "(कैंसिल करने के लिए /cancel टाइप करें)"
    )
    
    try:
        announce_msg = await client.ask(message.chat.id, text=ask_prompt, timeout=120)
        
        if announce_msg.text and announce_msg.text.lower() == "/cancel":
            return await message.reply_text("❌ अनाउंस कैंसिल कर दिया गया है।")
            
    except asyncio.TimeoutError:
        return await message.reply_text("❌ **टाइमआउट:** आपने मैसेज भेजने में बहुत देर कर दी। कृपया दोबारा `/announce` कमांड दें।")
    
    exmsg = await message.reply_text(
        "🔄 **Announcing Started...**\n\n"
        "कृपया प्रतीक्षा करें, मैं सभी यूज़र्स को अनाउंसमेंट भेज रहा हूँ 🚀"
    )

    users = await get_users() or []
    if not users:
        await exmsg.edit_text("❌ Database में कोई यूज़र नहीं मिला!")
        return
        
    failed_users = 0
    done_users = 0
    to_send = announce_msg.id
  
    for user in users:
        try:
            await client.forward_messages(chat_id=int(user), from_chat_id=message.chat.id, message_ids=to_send)
            done_users += 1
            await asyncio.sleep(1)
        except Exception:
            failed_users += 1
          
    if failed_users == 0:
        await exmsg.edit_text(
            f"**sᴜᴄᴄᴇssғᴜʟʟʏ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ✅**\n\n**sᴇɴᴛ ᴍᴇssᴀɢᴇ ᴛᴏ** `{done_users}` **ᴜsᴇʀs**",
        )
    else:
        await exmsg.edit_text(
            f"**sᴜᴄᴄᴇssғᴜʟʟʏ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ✅**\n\n**sᴇɴᴛ ᴍᴇssᴀɢᴇ ᴛᴏ** `{done_users}` **ᴜsᴇʀs**\n\n**ɴᴏᴛᴇ:-** `ᴅᴜᴇ ᴛᴏ sᴏᴍᴇ ɪssᴜᴇ ᴄᴀɴ'ᴛ ᴀʙʟᴇ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ` `{failed_users}` **ᴜsᴇʀs**",
        )

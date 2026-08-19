import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import BotCommand, BotCommandScopeChat, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import CONFIG
from app.database import db
from app.queue_manager import queue_manager
from app.admin_handlers import admin_handlers
from app.extract_handlers import extract_handlers
from app.index_handlers import index_handlers
from app.payment_handlers import payment_handlers
from app.upload_handlers import upload_handlers
from app.user_handlers import user_handlers

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=getattr(logging, CONFIG.LOG_LEVEL, logging.INFO),
)
logger = logging.getLogger("telegram-test-series-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "10000"))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health"):
            body = b"Telegram Test Series Bot is running."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        return


def start_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info("Health server started on port %s", PORT)
    server.serve_forever()


def validate_environment():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")
    if not CONFIG.MONGO_URL:
        raise RuntimeError("MONGO_URL environment variable is missing.")
    if not CONFIG.ADMIN_IDS and not CONFIG.ADMIN_USERNAMES:
        raise RuntimeError(
            "Admin configuration missing. Set ADMIN_IDS (Telegram ID) "
            "or ADMIN_USERNAMES in Render Environment Variables."
        )
    logger.info("Environment validation successful.")


async def safe_call(fn, update, context, name, *args, **kwargs):
    try:
        result = fn(update, context, *args, **kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result
    except Exception:
        logger.exception("%s failed", name)
        message = update.effective_message if isinstance(update, Update) else None
        if message:
            try:
                await message.reply_text("⚠️ इस option को process करते समय error आया।")
            except Exception:
                pass
        return None


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    data = (query.data or "").strip()
    logger.info("Callback received: %s", data)

    # Each child handler normally answers its own callback. We answer here only
    # for callbacks that have no child handler.
    try:
        if data in ("home", "menu:commands"):
            await query.answer()
    except Exception:
        pass

    if data == "home":
        return await safe_call(user_handlers.handle_callback, update, context, "home")

    if data.startswith(("menu:", "user:", "trial:", "purchase:")):
        return await safe_call(user_handlers.handle_callback, update, context, "user callback")

    if data == "check_force_join":
        return await safe_call(user_handlers.start, update, context, "force join refresh")

    if data.startswith(("index:", "category:", "exam:", "type:", "year:")):
        return await safe_call(index_handlers.handle_callback, update, context, "index callback")

    if data.startswith(("test:", "extract:", "retry:", "retry_extract:", "extract_confirm:")):
        return await safe_call(extract_handlers.handle_callback, update, context, "extract callback")

    if data.startswith("payment:"):
        return await safe_call(payment_handlers.handle_callback, update, context, "payment callback")

    if data.startswith("admin:"):
        return await safe_call(admin_handlers.handle_callback, update, context, "admin callback")

    # Legacy keyboard callbacks: route the useful ones to their modern handlers.
    if data.startswith("upload:"):
        if data == "upload:manual":
            return await safe_call(upload_handlers.start_upload, update, context, "manual upload")
        if data == "upload:bulk":
            return await safe_call(upload_handlers.start_bulk_upload, update, context, "bulk upload")
        await query.answer("Upload option updated in /upload", show_alert=True)
        return

    if data in ("help", "commands"):
        return await safe_call(user_handlers.help_command, update, context, "help")

    try:
        await query.answer("Unknown option", show_alert=True)
    except Exception:
        pass
    logger.warning("Unhandled callback: %s", data)


async def document_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if await upload_handlers.handle_document(update, context):
            return
        # Non-admin documents, especially payment screenshots, continue to
        # the user flow instead of being swallowed by the upload router.
        if await user_handlers.handle_message(update, context):
            return
    except Exception:
        logger.exception("Document processing error")
        if update.effective_message:
            try:
                await update.effective_message.reply_text("❌ File process करते समय error आया।")
            except Exception:
                pass


async def photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if await user_handlers.handle_message(update, context):
            return
    except Exception:
        logger.exception("Photo handler error")
        if update.effective_message:
            try:
                await update.effective_message.reply_text("❌ Photo process करते समय error आया।")
            except Exception:
                pass


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_data = context.user_data or {}
        upload_mode = user_data.get("upload_mode")
        if upload_mode in ("manual", "bulk", "single"):
            if await upload_handlers.handle_text(update, context):
                return
        if await user_handlers.handle_message(update, context):
            return
        # Admin text flows (ban, broadcast, price, settings, etc.)
        if await admin_handlers.handle_admin_text(update, context):
            return
    except Exception:
        logger.exception("Text handler error")


async def start_command(update, context):
    await safe_call(user_handlers.start, update, context, "/start")

async def help_command(update, context):
    await safe_call(user_handlers.help_command, update, context, "/help")

async def menu_command(update, context):
    await safe_call(user_handlers.start, update, context, "/menu")

async def index_command(update, context):
    await safe_call(index_handlers.show_categories, update, context, "/index")

async def price_command(update, context):
    await safe_call(user_handlers.show_price, update, context, "/price")

async def userinfo_command(update, context):
    await safe_call(user_handlers.user_info, update, context, "/userinfo")

async def trial_command(update, context):
    await safe_call(user_handlers.show_trial, update, context, "/trial")

async def report_command(update, context):
    await safe_call(user_handlers.report_menu, update, context, "/report")

async def admin_command(update, context):
    await safe_call(admin_handlers.admin_command, update, context, "/admin")

async def admin_stats_command(update, context):
    await safe_call(admin_handlers.stats, update, context, "/stats")

async def admin_users_command(update, context):
    await safe_call(admin_handlers.user_list, update, context, "/users")

async def admin_paidusers_command(update, context):
    await safe_call(admin_handlers.paid_users, update, context, "/paidusers")

async def admin_trial_command(update, context):
    await safe_call(admin_handlers.trial_settings, update, context, "/trialsettings")

async def admin_broadcast_command(update, context):
    await safe_call(admin_handlers.broadcast_start, update, context, "/broadcast")

async def admin_price_command(update, context):
    await safe_call(admin_handlers.price_settings, update, context, "/adminprice")

async def admin_welcome_command(update, context):
    await safe_call(admin_handlers.welcome_settings, update, context, "/welcome")

async def admin_forcejoin_command(update, context):
    await safe_call(admin_handlers.force_join, update, context, "/forcejoin")

async def admin_backup_command(update, context):
    await safe_call(admin_handlers.backup, update, context, "/backup")

async def admin_testreport_command(update, context):
    await safe_call(admin_handlers.test_report, update, context, "/testreport")

async def admin_queue_command(update, context):
    await safe_call(admin_handlers.queue_status, update, context, "/queue")

async def admin_settings_command(update, context):
    await safe_call(admin_handlers.settings, update, context, "/settings")

async def admin_database_channel_command(update, context):
    await safe_call(admin_handlers.channel_settings, update, context, "database", "DATABASE CHANNEL")

async def admin_payment_channel_command(update, context):
    await safe_call(admin_handlers.channel_settings, update, context, "payment", "PAYMENT VERIFICATION CHANNEL")

async def admin_user_channel_command(update, context):
    await safe_call(admin_handlers.channel_settings, update, context, "user_activity", "USER ACTIVITY CHANNEL")

async def admin_paid_channel_command(update, context):
    await safe_call(admin_handlers.channel_settings, update, context, "paid", "PAID CHANNEL")

async def admin_paid_user_channel_command(update, context):
    await safe_call(admin_handlers.channel_settings, update, context, "paid_user", "PAID USER CHANNEL")

async def admin_ban_command(update, context):
    await safe_call(admin_handlers.ban_start, update, context, "/ban")

async def admin_unban_command(update, context):
    await safe_call(admin_handlers.unban_start, update, context, "/unban")

async def admin_trial_lock_command(update, context):
    await safe_call(admin_handlers.trial_lock_start, update, context, "/triallock")

async def admin_addtest_command(update, context):
    await safe_call(upload_handlers.start_upload, update, context, "/addtest")

async def id_command(update, context):
    user = update.effective_user
    if not user or not update.effective_message:
        return
    configured = CONFIG.is_admin(user)
    await update.effective_message.reply_text(
        "🆔 **Your Telegram ID**\n\n"
        f"`{user.id}`\n\n"
        f"Admin configured: {'✅ YES' if configured else '❌ NO'}\n\n"
        "अगर Admin = NO है तो Render में ADMIN_IDS में यही ID डालें "
        "या ADMIN_USERNAMES में अपना Telegram username डालें।",
        parse_mode="Markdown",
    )

async def stats_command(update, context):
    await safe_call(admin_handlers.stats, update, context, "/stats")

async def upload_command(update, context):
    await safe_call(upload_handlers.start_upload, update, context, "/upload")

async def extract_command(update, context):
    await safe_call(index_handlers.show_categories, update, context, "/extract")

async def seed_command(update, context):
    user = update.effective_user
    if not user or not CONFIG.is_admin(user):
        if update.effective_message:
            await update.effective_message.reply_text("🚫 यह command केवल Admin के लिए है।")
        return
    test_id = db.seed_demo_test()
    await update.effective_message.reply_text(
        "🧪 Demo Test तैयार है!\n\n"
        f"🆔 Test ID: `{test_id}`\n"
        "अब /index खोलकर पूरा flow test करें।",
        parse_mode="Markdown",
    )

async def commands_command(update, context):
    user = update.effective_user
    admin = bool(user and CONFIG.is_admin(user))
    text = (
        "📋 *COMMAND MENU*\n\n"
        "👤 User Commands\n"
        "/start — Main Menu\n"
        "/menu — Main Menu\n"
        "/help — Help\n"
        "/index — Test Index\n"
        "/extract — Extract Test\n"
        "/price — Premium Plans\n"
        "/trial — Free Trial\n"
        "/userinfo — My Account\n"
        "/report — Report\n"
        "/id — Show Telegram ID\n\n"
    )
    if admin:
        text += (
            "🛠️ *Admin Commands*\n"
            "/admin — Admin Panel\n"
            "/stats — Bot Statistics\n"
            "/users — User List\n"
            "/paidusers — Paid Users\n"
            "/upload — Upload Test\n"
            "/addtest — Add Test\n"
            "/ban — Ban User\n"
            "/unban — Unban User\n"
            "/triallock — Lock Trial\n"
            "/trialsettings — Trial Settings\n"
            "/broadcast — Broadcast\n"
            "/adminprice — Price Settings\n"
            "/welcome — Welcome Settings\n"
            "/forcejoin — Force Join\n"
            "/backup — Backup\n"
            "/testreport — Test Report\n"
            "/queue — Queue Status\n"
            "/settings — Bot Settings\n"
            "/database — Database Channel\n"
            "/paymentchannel — Payment Channel\n"
            "/userchannel — User Channel\n"
            "/paidchannel — Paid Channel\n"
            "/paiduserchannel — Paid User Channel\n"
            "/seed — Add Demo Test\n"
        )
    keyboard = user_handlers.main_keyboard(
        paid=db.is_paid_user(user.id) if user else False,
        is_admin=admin,
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def upload_job_complete(event):
    result = event.get("result") or {}
    payload = event.get("payload") or {}
    chat_id = payload.get("chat_id") or event.get("user_id")
    if not queue_manager.bot or not chat_id:
        return
    try:
        await queue_manager.bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ **TEST UPLOAD COMPLETED**\n\n"
                f"🆔 Test ID: `{result.get('test_id', '-')}`\n"
                f"📚 Test: **{result.get('title', '-') }**\n"
                f"❓ Questions: **{result.get('question_count', 0)}**\n\n"
                "📢 Original file Database Channel में save हो गई है।"
            ),
            parse_mode="Markdown",
        )
    except Exception:
        logger.exception("Could not send upload completion message")


async def upload_job_failed(event):
    payload = event.get("payload") or {}
    chat_id = payload.get("chat_id") or event.get("user_id")
    if not queue_manager.bot or not chat_id:
        return
    try:
        await queue_manager.bot.send_message(
            chat_id=chat_id,
            text=(
                "❌ **TEST UPLOAD FAILED**\n\n"
                f"📄 File: `{payload.get('filename', '-')}`\n"
                f"⚠️ Error: {event.get('error', 'Unknown error')}\n\n"
                "/queue से status check करें या file दोबारा भेजें।"
            ),
            parse_mode="Markdown",
        )
    except Exception:
        logger.exception("Could not send upload failure message")


async def post_init(application: Application):
    logger.info("Bot initialization started.")
    queue_manager.set_bot(application.bot)

    # Queue processors are registered here so extraction/upload jobs really run.
    queue_manager.register_processor("test_extract", extract_handlers.process_extract_job)
    queue_manager.register_processor("test_upload", upload_handlers.process_upload_job)
    queue_manager.register_processor("test_upload:complete", upload_job_complete)
    queue_manager.register_processor("test_upload:failed", upload_job_failed)
    await queue_manager.start()

    # Keep DB indexes compatible with older deployments.
    try:
        db.ensure_indexes()
    except Exception:
        logger.exception("Database index initialization failed.")

    # Telegram command menu for every user.
    user_commands = [
        BotCommand("start", "Main menu"),
        BotCommand("menu", "Main menu"),
        BotCommand("help", "Help"),
        BotCommand("index", "Test index"),
        BotCommand("extract", "Extract test"),
        BotCommand("price", "Premium plans"),
        BotCommand("trial", "Free trial"),
        BotCommand("userinfo", "My account"),
        BotCommand("report", "Report problem"),
        BotCommand("id", "Show my Telegram ID"),
        BotCommand("commands", "All commands"),
    ]
    await application.bot.set_my_commands(user_commands)

    # Admin chat gets admin-only commands in its command menu.
    for admin_id in CONFIG.admin_ids:
        try:
            await application.bot.set_my_commands(
                user_commands + [
                    BotCommand("admin", "Admin panel"),
                    BotCommand("stats", "Bot statistics"),
                    BotCommand("users", "User list"),
                    BotCommand("paidusers", "Paid users"),
                    BotCommand("upload", "Upload test"),
                    BotCommand("addtest", "Add test"),
                    BotCommand("ban", "Ban user"),
                    BotCommand("unban", "Unban user"),
                    BotCommand("triallock", "Lock trial"),
                    BotCommand("trialsettings", "Trial settings"),
                    BotCommand("broadcast", "Broadcast"),
                    BotCommand("adminprice", "Price settings"),
                    BotCommand("welcome", "Welcome settings"),
                    BotCommand("forcejoin", "Force join"),
                    BotCommand("backup", "Database backup"),
                    BotCommand("testreport", "Test report"),
                    BotCommand("queue", "Queue status"),
                    BotCommand("settings", "Bot settings"),
                    BotCommand("database", "Database channel"),
                    BotCommand("paymentchannel", "Payment channel"),
                    BotCommand("userchannel", "User activity channel"),
                    BotCommand("paidchannel", "Paid channel"),
                    BotCommand("paiduserchannel", "Paid user channel"),
                    BotCommand("seed", "Add demo test"),
                ],
                scope=BotCommandScopeChat(admin_id),
            )
        except Exception:
            logger.exception("Could not set admin command menu for %s", admin_id)

    logger.info("Bot initialization completed.")


async def post_shutdown(application: Application):
    logger.info("Bot shutdown started.")
    try:
        await queue_manager.stop()
    except Exception:
        logger.exception("Queue manager shutdown failed")
    try:
        db.close()
    except Exception:
        logger.exception("Database close failed")


def build_application():
    validate_environment()
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    commands = [
        ("start", start_command),
        ("menu", menu_command),
        ("help", help_command),
        ("commands", commands_command),
        ("index", index_command),
        ("extract", extract_command),
        ("price", price_command),
        ("trial", trial_command),
        ("userinfo", userinfo_command),
        ("report", report_command),
        ("id", id_command),
        ("admin", admin_command),
        ("stats", admin_stats_command),
        ("users", admin_users_command),
        ("paidusers", admin_paidusers_command),
        ("upload", upload_command),
        ("addtest", admin_addtest_command),
        ("ban", admin_ban_command),
        ("unban", admin_unban_command),
        ("triallock", admin_trial_lock_command),
        ("trialsettings", admin_trial_command),
        ("broadcast", admin_broadcast_command),
        ("adminprice", admin_price_command),
        ("welcome", admin_welcome_command),
        ("forcejoin", admin_forcejoin_command),
        ("backup", admin_backup_command),
        ("testreport", admin_testreport_command),
        ("queue", admin_queue_command),
        ("settings", admin_settings_command),
        ("database", admin_database_channel_command),
        ("paymentchannel", admin_payment_channel_command),
        ("userchannel", admin_user_channel_command),
        ("paidchannel", admin_paid_channel_command),
        ("paiduserchannel", admin_paid_user_channel_command),
        ("seed", seed_command),
    ]
    for name, handler in commands:
        application.add_handler(CommandHandler(name, handler))

    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_handler(MessageHandler(filters.Document.ALL, document_router))
    application.add_handler(MessageHandler(filters.PHOTO, photo_router))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    return application


def main():
    logger.info("Starting Telegram Test Series Bot...")
    threading.Thread(target=start_health_server, daemon=True, name="health-server").start()
    application = build_application()
    logger.info("Telegram polling starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()

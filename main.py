import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app.database import db
from app.queue_manager import queue_manager
from app.admin_handlers import admin_handlers
from app.extract_handlers import extract_handlers
from app.index_handlers import index_handlers
from app.payment_handlers import payment_handlers
from app.upload_handlers import upload_handlers
from app.user_handlers import user_handlers


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)

logger = logging.getLogger("telegram-test-series-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "10000"))


# ============================================================
# HEALTH SERVER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path in ("/", "/health"):
            body = b"Telegram Test Series Bot is running."
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8",
            )
            self.send_header(
                "Content-Length",
                str(len(body)),
            )
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


# ============================================================
# HELPERS
# ============================================================

def validate_environment():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is missing."
        )

    if not os.getenv("MONGO_URL", "").strip():
        raise RuntimeError(
            "MONGO_URL environment variable is missing."
        )

    logger.info("Environment validation successful.")


async def safe_call(coro, name: str):
    try:
        await coro
        return True
    except Exception:
        logger.exception("%s failed.", name)
        return False


# ============================================================
# CALLBACK ROUTER
# ============================================================

async def callback_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if not query:
        return

    data = query.data or ""

    try:
        await query.answer()
    except Exception:
        pass

    logger.info("Callback received: %s", data)

    # --------------------------------------------------------
    # HOME / USER MENU
    # --------------------------------------------------------

    if data in {
        "home",
        "menu:userinfo",
        "menu:premium",
        "menu:trial",
        "menu:price",
        "menu:channels",
        "menu:report",
        "trial:activate",
    } or data.startswith("purchase:"):

        if data == "home":
            return await safe_call(
                user_handlers.handle_callback(update, context),
                "Home handler",
            )

        return await safe_call(
            user_handlers.handle_callback(update, context),
            "User menu handler",
        )

    # --------------------------------------------------------
    # LEGACY / ALTERNATIVE USER CALLBACKS
    # --------------------------------------------------------

    if data == "trial:start":
        return await safe_call(
            user_handlers.activate_trial(update, context),
            "Trial activation handler",
        )

    if data == "menu:purchase":
        return await safe_call(
            user_handlers.premium_menu(update, context),
            "Purchase menu handler",
        )

    if data == "help":
        return await safe_call(
            user_handlers.help_command(update, context),
            "Help handler",
        )

    if data == "pricing:show":
        return await safe_call(
            user_handlers.premium_menu(update, context),
            "Pricing handler",
        )

    if data.startswith("pricing:buy:"):
        plan = data.split(":", 2)[2]
        return await safe_call(
            user_handlers.purchase(update, context, plan),
            "Pricing purchase handler",
        )

    if data == "trial:show":
        return await safe_call(
            user_handlers.show_trial(update, context),
            "Trial handler",
        )

    if data == "user:info":
        return await safe_call(
            user_handlers.user_info(update, context),
            "User info handler",
        )

    if data == "channels:list":
        return await safe_call(
            user_handlers.show_channels(update, context),
            "Channel handler",
        )

    # --------------------------------------------------------
    # INDEX
    # --------------------------------------------------------

    if (
        data == "index:categories"
        or data.startswith("index:category:")
        or data.startswith("index:exam:")
        or data.startswith("index:type:")
        or data.startswith("index:year:")
        or data.startswith("index:test:")
    ):
        return await safe_call(
            index_handlers.handle_callback(update, context),
            "Index handler",
        )

    # --------------------------------------------------------
    # EXTRACTION
    # --------------------------------------------------------

    if data.startswith("test:"):
        return await safe_call(
            extract_handlers._test_callback(update, context),
            "Extract test handler",
        )

    if data.startswith("extract_confirm:"):
        return await safe_call(
            extract_handlers._extract_confirm_callback(
                update, context
            ),
            "Extract confirmation handler",
        )

    if data.startswith("extract:"):
        return await safe_call(
            extract_handlers._extract_callback(update, context),
            "Extract handler",
        )

    if data.startswith("retry_extract:"):
        return await safe_call(
            extract_handlers._retry_callback(update, context),
            "Retry extraction handler",
        )

    # Old index/extract button compatibility
    if data.startswith("extract_test:"):
        test_id = data.split(":", 1)[1]
        return await safe_call(
            extract_handlers.confirm_extract(
                update,
                context,
                test_id,
            ),
            "Extract test compatibility handler",
        )

    if data.startswith("extract_cancel:"):
        try:
            await query.edit_message_text(
                "❌ Extract request cancel कर दिया गया।",
                reply_markup=None,
            )
        except Exception:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Extract request cancel कर दिया गया।"
                )
        return

    # --------------------------------------------------------
    # PAYMENT
    # --------------------------------------------------------

    if data.startswith("payment:"):
        return await safe_call(
            payment_handlers.handle_callback(update, context),
            "Payment handler",
        )

    # --------------------------------------------------------
    # UPLOAD MENU
    # --------------------------------------------------------

    if data == "upload:start" or data == "upload:manual":
        return await safe_call(
            upload_handlers.start_upload(update, context),
            "Upload start handler",
        )

    if data in {"upload:bulk", "upload:start_bulk"}:
        return await safe_call(
            upload_handlers.start_bulk_upload(update, context),
            "Bulk upload handler",
        )

    if data == "upload:cancel":
        context.user_data.pop("upload_mode", None)
        context.user_data.pop("upload_files", None)
        context.user_data.pop("admin_action", None)

        try:
            await query.edit_message_text(
                "❌ Upload session cancel कर दिया गया।",
                reply_markup=None,
            )
        except Exception:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Upload session cancel कर दिया गया।"
                )
        return

    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------

    if data.startswith("admin:"):
        return await safe_call(
            admin_handlers.handle_callback(update, context),
            "Admin handler",
        )

    # --------------------------------------------------------
    # USER REPORT / REPORT BUTTONS
    # --------------------------------------------------------

    if data.startswith("report:"):
        return await safe_call(
            user_handlers.report_menu(update, context),
            "Report handler",
        )

    # --------------------------------------------------------
    # FORCE JOIN VERIFY
    # --------------------------------------------------------

    if data == "forcejoin:verify":
        try:
            from app.force_join import force_join
            result = await force_join.verify_force_join(
                update,
                context,
            )
            return result
        except Exception:
            logger.exception("Force join verification failed.")
            return

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    logger.warning("Unhandled callback: %s", data)


# ============================================================
# MESSAGE ROUTERS
# ============================================================

async def document_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        # Payment screenshot as document
        if context.user_data.get("payment_id"):
            try:
                handled = await payment_handlers.handle_screenshot(
                    update, context
                )
                if handled is not False:
                    return
            except Exception:
                logger.exception(
                    "Payment document processing failed."
                )

        handled = await upload_handlers.handle_document(
            update,
            context,
        )

        if handled:
            return

    except Exception:
        logger.exception("Document processing error.")

        if update.effective_message:
            await update.effective_message.reply_text(
                "❌ File process करते समय error आया।"
            )


async def photo_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if context.user_data.get("payment_id"):
        try:
            await payment_handlers.handle_screenshot(
                update,
                context,
            )
            return
        except Exception:
            logger.exception(
                "Payment photo processing failed."
            )

    # User report does not need photo processing.
    return


async def text_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        # Upload text / DONE
        upload_mode = context.user_data.get("upload_mode")

        if upload_mode in {"manual", "single", "bulk"}:
            if await upload_handlers.handle_text(update, context):
                return

        # Admin interactive actions
        if await admin_handlers.handle_admin_text(update, context):
            return

        # User report / payment state
        if await user_handlers.handle_message(update, context):
            return

    except Exception:
        logger.exception("Text handler error.")


# ============================================================
# COMMANDS
# ============================================================

async def start_command(update, context):
    await user_handlers.start(update, context)


async def help_command(update, context):
    await user_handlers.help_command(update, context)


async def admin_command(update, context):
    await admin_handlers.admin_command(update, context)


async def extract_command(update, context):
    # Open Test Index. User can choose a test and extract it.
    await index_handlers.show_categories(
        update,
        context,
        edit=False,
    )


async def index_command(update, context):
    await index_handlers.show_categories(
        update,
        context,
        edit=False,
    )


async def upload_command(update, context):
    await upload_handlers.start_upload(update, context)


async def stats_command(update, context):
    await admin_handlers.stats(update, context)


async def price_command(update, context):
    await user_handlers.show_price(update, context)


async def trial_command(update, context):
    await user_handlers.show_trial(update, context)


async def account_command(update, context):
    await user_handlers.user_info(update, context)


async def report_command(update, context):
    await user_handlers.report_menu(update, context)


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.error(
        "Unhandled Telegram exception: %s",
        context.error,
        exc_info=context.error,
    )

    try:
        if isinstance(update, Update):
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Server पर temporary error आया है।\n"
                    "कृपया थोड़ी देर बाद दोबारा try करें।"
                )
    except Exception:
        logger.debug(
            "Could not send error message.",
            exc_info=True,
        )


# ============================================================
# STARTUP / SHUTDOWN
# ============================================================

async def post_init(application: Application):
    logger.info("Bot initialization started.")

    # Database
    db.ensure_indexes()
    db.get_prices()
    logger.info("Database indexes and default settings initialized.")

    # Queue processors
    queue_manager.set_bot(application.bot)

    queue_manager.register_processor(
        "test_extract",
        extract_handlers.process_extract_job,
    )

    queue_manager.register_processor(
        "test_upload",
        upload_handlers.process_upload_job,
    )

    await queue_manager.start()
    logger.info("Queue manager started.")

    logger.info("Bot initialization completed.")


async def post_shutdown(application: Application):
    logger.info("Bot shutdown started.")

    try:
        await queue_manager.stop()
    except Exception:
        logger.exception("Queue manager shutdown failed.")

    try:
        db.close()
    except Exception:
        logger.exception("Database close failed.")

    logger.info("Bot shutdown completed.")


# ============================================================
# APPLICATION
# ============================================================

def build_application():
    validate_environment()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("index", index_command))
    application.add_handler(CommandHandler("extract", extract_command))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("trial", trial_command))
    application.add_handler(CommandHandler("userinfo", account_command))
    application.add_handler(CommandHandler("report", report_command))

    # One central callback router.
    # This avoids callback-handler ordering conflicts.
    application.add_handler(
        CallbackQueryHandler(callback_router)
    )

    # Files
    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            document_router,
        )
    )

    # Payment screenshots / photos
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_router,
        )
    )

    # Text
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router,
        )
    )

    application.add_error_handler(error_handler)

    return application


# ============================================================
# MAIN
# ============================================================

def main():
    logger.info("Starting Telegram Test Series Bot...")

    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True,
        name="health-server",
    )
    health_thread.start()

    application = build_application()

    logger.info("Telegram polling starting...")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception:
        logger.exception("Fatal application error.")
        raise

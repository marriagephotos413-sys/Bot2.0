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

# ============================================================
# APP IMPORTS
# ============================================================

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
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
    level=logging.INFO,
)

logger = logging.getLogger("telegram-test-series-bot")


# ============================================================
# ENVIRONMENT
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

PORT = int(os.getenv("PORT", "10000"))


# ============================================================
# HEALTH SERVER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        if self.path in ("/", "/health"):

            body = (
                b"Telegram Test Series Bot is running."
            )

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

    server = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler,
    )

    logger.info(
        "Health server started on port %s",
        PORT,
    )

    server.serve_forever()


# ============================================================
# BASIC VALIDATION
# ============================================================

def validate_environment():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN environment variable is missing."
        )

    logger.info(
        "Environment validation successful."
    )


# ============================================================
# SAFE HANDLER CALL
# ============================================================

async def safe_callback_handler(
    handler,
    update,
    context,
    name="handler",
):
    try:

        result = handler(
            update,
            context,
        )

        if hasattr(result, "__await__"):
            await result

        return True

    except Exception:

        logger.exception(
            "%s callback failed.",
            name,
        )

        return False


# ============================================================
# MAIN CALLBACK ROUTER
# ============================================================

async def callback_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    data = query.data or ""

    # --------------------------------------------------------
    # ANSWER CALLBACK
    # --------------------------------------------------------

    try:
        await query.answer()
    except Exception:
        pass

    logger.info(
        "Callback received: %s",
        data,
    )

    # ========================================================
    # MENU
    # ========================================================

    if data.startswith("menu:"):

        menu_type = data.split(":", 1)[1]

        # ----------------------------------------------------
        # User info
        # ----------------------------------------------------

        if menu_type == "userinfo":

            if hasattr(
                user_handlers,
                "userinfo",
            ):

                await safe_callback_handler(
                    user_handlers.userinfo,
                    update,
                    context,
                    "userinfo",
                )

            elif hasattr(
                user_handlers,
                "user_info",
            ):

                await safe_callback_handler(
                    user_handlers.user_info,
                    update,
                    context,
                    "user_info",
                )

            else:

                logger.warning(
                    "userinfo handler not found."
                )

            return

        # ----------------------------------------------------
        # Premium
        # ----------------------------------------------------

        if menu_type == "premium":

            if hasattr(
                user_handlers,
                "premium",
            ):

                await safe_callback_handler(
                    user_handlers.premium,
                    update,
                    context,
                    "premium",
                )

            elif hasattr(
                payment_handlers,
                "premium",
            ):

                await safe_callback_handler(
                    payment_handlers.premium,
                    update,
                    context,
                    "premium",
                )

            else:

                logger.warning(
                    "premium handler not found."
                )

            return

        # ----------------------------------------------------
        # Trial
        # ----------------------------------------------------

        if menu_type == "trial":

            if hasattr(
                user_handlers,
                "trial",
            ):

                await safe_callback_handler(
                    user_handlers.trial,
                    update,
                    context,
                    "trial",
                )

            elif hasattr(
                extract_handlers,
                "trial",
            ):

                await safe_callback_handler(
                    extract_handlers.trial,
                    update,
                    context,
                    "trial",
                )

            else:

                logger.warning(
                    "trial handler not found."
                )

            return

        # ----------------------------------------------------
        # Price
        # ----------------------------------------------------

        if menu_type == "price":

            if hasattr(
                payment_handlers,
                "price",
            ):

                await safe_callback_handler(
                    payment_handlers.price,
                    update,
                    context,
                    "price",
                )

            elif hasattr(
                payment_handlers,
                "show_price",
            ):

                await safe_callback_handler(
                    payment_handlers.show_price,
                    update,
                    context,
                    "show_price",
                )

            else:

                logger.warning(
                    "price handler not found."
                )

            return

        # ----------------------------------------------------
        # Report
        # ----------------------------------------------------

        if menu_type == "report":

            if hasattr(
                admin_handlers,
                "report",
            ):

                await safe_callback_handler(
                    admin_handlers.report,
                    update,
                    context,
                    "report",
                )

            elif hasattr(
                admin_handlers,
                "stats",
            ):

                await safe_callback_handler(
                    admin_handlers.stats,
                    update,
                    context,
                    "stats",
                )

            else:

                logger.warning(
                    "report handler not found."
                )

            return

        # ----------------------------------------------------
        # Unknown menu
        # ----------------------------------------------------

        logger.warning(
            "Unhandled menu callback: %s",
            data,
        )

        return

    # ========================================================
    # UPLOAD
    # ========================================================

    if data.startswith("upload:"):

        await safe_callback_handler(
            upload_handlers.handle_callback,
            update,
            context,
            "upload",
        )

        return

    # ========================================================
    # INDEX
    # ========================================================

    if (
        data.startswith("index:")
        or data.startswith("category:")
        or data.startswith("exam:")
        or data.startswith("type:")
        or data.startswith("year:")
    ):

        await safe_callback_handler(
            index_handlers.handle_callback,
            update,
            context,
            "index",
        )

        return

    # ========================================================
    # TEST
    # ========================================================

    if data.startswith("test:"):

        # Test callbacks are handled by index handler
        # unless extraction handler explicitly owns it.

        if hasattr(
            index_handlers,
            "handle_callback",
        ):

            await safe_callback_handler(
                index_handlers.handle_callback,
                update,
                context,
                "test",
            )

        return

    # ========================================================
    # PAYMENT
    # ========================================================

    if data.startswith("payment:"):

        await safe_callback_handler(
            payment_handlers.handle_callback,
            update,
            context,
            "payment",
        )

        return

    # ========================================================
    # ADMIN
    # ========================================================

    if data.startswith("admin:"):

        await safe_callback_handler(
            admin_handlers.handle_callback,
            update,
            context,
            "admin",
        )

        return

    # ========================================================
    # EXTRACT
    # ========================================================

    if (
        data.startswith("extract:")
        or data.startswith("retry:")
        or data.startswith("retry_extract:")
        or data.startswith("extract_confirm:")
    ):

        await safe_callback_handler(
            extract_handlers.handle_callback,
            update,
            context,
            "extract",
        )

        return

    # ========================================================
    # USER
    # ========================================================

    if (
        data.startswith("user:")
        or data == "home"
        or data.startswith("home:")
    ):

        await safe_callback_handler(
            user_handlers.handle_callback,
            update,
            context,
            "user",
        )

        return

    # ========================================================
    # UNKNOWN CALLBACK
    # ========================================================

    logger.warning(
        "Unhandled callback: %s",
        data,
    )


# ============================================================
# DOCUMENT ROUTER
# ============================================================

async def document_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    try:

        handled = await upload_handlers.handle_document(
            update,
            context,
        )

        if handled:
            return

    except Exception:

        logger.exception(
            "Document processing error."
        )

        if update.effective_message:

            await update.effective_message.reply_text(
                "❌ File process करते समय error आया।"
            )


# ============================================================
# TEXT ROUTER
# ============================================================

async def text_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    try:

        upload_mode = context.user_data.get(
            "upload_mode"
        )

        if upload_mode in (
            "manual",
            "bulk",
        ):

            handled = await upload_handlers.handle_text(
                update,
                context,
            )

            if handled:
                return

        await user_handlers.handle_text(
            update,
            context,
        )

    except Exception:

        logger.exception(
            "Text handler error."
        )


# ============================================================
# COMMANDS
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    try:

        await user_handlers.start(
            update,
            context,
        )

    except Exception:

        logger.exception(
            "Start command failed."
        )

        if update.effective_message:

            await update.effective_message.reply_text(
                (
                    "❌ Bot start करते समय "
                    "temporary error आया।\n"
                    "कृपया थोड़ी देर बाद /start करें।"
                )
            )


async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    try:

        await admin_handlers.admin_panel(
            update,
            context,
        )

    except Exception:

        logger.exception(
            "Admin command failed."
        )


async def extract_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    try:

        await index_handlers.extract_command(
            update,
            context,
        )

    except Exception:

        logger.exception(
            "Extract command failed."
        )


async def upload_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    try:

        await upload_handlers.start_upload(
            update,
            context,
        )

    except Exception:

        logger.exception(
            "Upload command failed."
        )


async def stats_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    try:

        await admin_handlers.stats(
            update,
            context,
        )

    except Exception:

        logger.exception(
            "Stats command failed."
        )


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
                    (
                        "⚠️ अभी server पर "
                        "temporary error आया है।\n\n"
                        "कृपया थोड़ी देर बाद "
                        "दोबारा try करें।"
                    )
                )

    except Exception:

        logger.debug(
            "Could not send error message.",
            exc_info=True,
        )


# ============================================================
# APPLICATION INITIALIZATION
# ============================================================

async def post_init(
    application: Application,
):

    logger.info(
        "Bot initialization started."
    )

    # --------------------------------------------------------
    # Queue manager
    # --------------------------------------------------------

    try:

        queue_manager.set_bot(
            application.bot
        )

        logger.info(
            "Queue manager initialized."
        )

    except Exception:

        logger.exception(
            "Queue manager initialization failed."
        )

    # --------------------------------------------------------
    # Database indexes
    # --------------------------------------------------------

    try:

        if hasattr(
            db,
            "ensure_indexes",
        ):

            db.ensure_indexes()

            logger.info(
                "Database indexes initialized."
            )

        else:

            logger.warning(
                "ensure_indexes() not available."
            )

    except Exception:

        logger.exception(
            "Database index initialization failed."
        )

    # --------------------------------------------------------
    # Extract handlers
    # --------------------------------------------------------

    try:

        # IMPORTANT:
        # Old code used:
        #     extract_handlers.register()
        #
        # That caused:
        #     missing 1 required positional argument: application
        #
        # Registration is now handled safely.

        if hasattr(
            extract_handlers,
            "register",
        ):

            try:

                extract_handlers.register(
                    application
                )

                logger.info(
                    "Extract handlers registered."
                )

            except TypeError:

                logger.exception(
                    "ExtractHandlers.register() signature mismatch."
                )

        else:

            logger.info(
                "ExtractHandlers uses main callback router."
            )

    except Exception:

        logger.exception(
            "Extract handlers registration failed."
        )

    # --------------------------------------------------------
    # Admin handlers
    # --------------------------------------------------------

    try:

        if hasattr(
            admin_handlers,
            "register",
        ):

            try:

                admin_handlers.register(
                    application
                )

                logger.info(
                    "Admin handlers registered."
                )

            except TypeError:

                logger.exception(
                    "AdminHandlers.register() signature mismatch."
                )

    except Exception:

        logger.exception(
            "Admin handlers registration failed."
        )

    logger.info(
        "Bot initialization completed."
    )


# ============================================================
# APPLICATION SHUTDOWN
# ============================================================

async def post_shutdown(
    application: Application,
):

    logger.info(
        "Bot shutdown started."
    )

    try:

        await queue_manager.shutdown()

    except Exception:

        logger.exception(
            "Queue manager shutdown failed."
        )

    try:

        db.close()

    except Exception:

        logger.exception(
            "Database close failed."
        )

    logger.info(
        "Bot shutdown completed."
    )


# ============================================================
# BUILD APPLICATION
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

    # ========================================================
    # COMMANDS
    # ========================================================

    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            admin_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "extract",
            extract_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "upload",
            upload_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "stats",
            stats_command,
        )
    )

    # ========================================================
    # CALLBACK ROUTER
    # ========================================================

    application.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    # ========================================================
    # DOCUMENT
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            document_router,
        )
    )

    # ========================================================
    # TEXT
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_router,
        )
    )

    # ========================================================
    # ERROR
    # ========================================================

    application.add_error_handler(
        error_handler
    )

    return application


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "Starting Telegram Test Series Bot..."
    )

    # --------------------------------------------------------
    # Render health server
    # --------------------------------------------------------

    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True,
        name="health-server",
    )

    health_thread.start()

    # --------------------------------------------------------
    # Telegram application
    # --------------------------------------------------------

    application = build_application()

    logger.info(
        "Telegram polling started."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        logger.info(
            "Bot stopped by user."
        )

    except Exception:

        logger.exception(
            "Fatal application error."
        )

        raise

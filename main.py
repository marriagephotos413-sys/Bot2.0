import asyncio
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

logger = logging.getLogger(
    "telegram-test-series-bot"
)


# ============================================================
# ENVIRONMENT
# ============================================================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    ""
)

PORT = int(
    os.getenv(
        "PORT",
        "10000",
    )
)


# ============================================================
# HEALTH SERVER
# ============================================================

class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        if self.path in (
            "/",
            "/health",
        ):

            body = (
                b"Telegram Test Series Bot "
                b"is running."
            )

            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8",
            )

            self.send_header(
                "Content-Length",
                str(len(body)),
            )

            self.end_headers()

            self.wfile.write(
                body
            )

            return

        self.send_response(
            404
        )

        self.end_headers()

    def log_message(
        self,
        format,
        *args,
    ):
        return


def start_health_server():

    server = HTTPServer(
        (
            "0.0.0.0",
            PORT,
        ),
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
# CALLBACK ROUTER
# ============================================================

async def callback_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    data = (
        query.data
        or ""
    )

    try:

        await query.answer()

    except Exception:

        pass

    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

    if data.startswith(
        "upload:"
    ):

        await upload_handlers.handle_callback(
            update,
            context,
        )

        return

    # --------------------------------------------------------
    # INDEX
    # --------------------------------------------------------

    if (
        data.startswith(
            "index:"
        )
        or data.startswith(
            "category:"
        )
        or data.startswith(
            "exam:"
        )
        or data.startswith(
            "type:"
        )
        or data.startswith(
            "year:"
        )
        or data.startswith(
            "test:"
        )
    ):

        await index_handlers.handle_callback(
            update,
            context,
        )

        return

    # --------------------------------------------------------
    # PAYMENT
    # --------------------------------------------------------

    if data.startswith(
        "payment:"
    ):

        await payment_handlers.handle_callback(
            update,
            context,
        )

        return

    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------

    if data.startswith(
        "admin:"
    ):

        await admin_handlers.handle_callback(
            update,
            context,
        )

        return

    # --------------------------------------------------------
    # EXTRACT
    # --------------------------------------------------------

    if (
        data.startswith(
            "extract:"
        )
        or data.startswith(
            "retry:"
        )
    ):

        await extract_handlers.handle_callback(
            update,
            context,
        )

        return

    # --------------------------------------------------------
    # USER
    # --------------------------------------------------------

    if (
        data.startswith(
            "user:"
        )
        or data.startswith(
            "home"
        )
    ):

        await user_handlers.handle_callback(
            update,
            context,
        )

        return

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

        # ----------------------------------------------------
        # Upload mode
        # ----------------------------------------------------

        upload_mode = (
            context.user_data.get(
                "upload_mode"
            )
        )

        if upload_mode in (
            "manual",
            "bulk",
        ):

            handled = (
                await upload_handlers.handle_text(
                    update,
                    context,
                )
            )

            if handled:
                return

        # ----------------------------------------------------
        # User handler
        # ----------------------------------------------------

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

    logger.exception(
        "Unhandled Telegram exception",
        exc_info=context.error,
    )

    # User को internal error details नहीं भेजेंगे।

    try:

        if isinstance(
            update,
            Update,
        ):

            if update.effective_message:

                await update.effective_message.reply_text(
                    (
                        "⚠️ अभी server पर load/error आया है।\n\n"
                        "Please wait करके दोबारा try करें।"
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

    except Exception:

        logger.exception(
            "Queue manager initialization failed."
        )

    # --------------------------------------------------------
    # Extract processors
    # --------------------------------------------------------

    try:

        extract_handlers.register()

    except Exception:

        logger.exception(
            "Extract handlers registration failed."
        )

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    try:

        db.ensure_indexes()

    except Exception:

        logger.exception(
            "Database index initialization failed."
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
        .post_init(
            post_init
        )
        .post_shutdown(
            post_shutdown
        )
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
    # CALLBACKS
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

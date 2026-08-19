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


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=getattr(
        logging,
        CONFIG.LOG_LEVEL,
        logging.INFO,
    ),
)

logger = logging.getLogger(
    "telegram-test-series-bot"
)


# ============================================================
# ENVIRONMENT
# ============================================================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "",
).strip()

PORT = int(
    os.getenv(
        "PORT",
        "10000",
    )
)


# ============================================================
# HEALTH SERVER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        if self.path in (
            "/",
            "/health",
        ):

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
# ENVIRONMENT VALIDATION
# ============================================================

def validate_environment():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN environment variable is missing."
        )

    if not CONFIG.MONGO_URL:

        raise RuntimeError(
            "MONGO_URL environment variable is missing."
        )

    if (
        not CONFIG.ADMIN_IDS
        and not CONFIG.ADMIN_USERNAMES
    ):

        raise RuntimeError(
            "Admin configuration missing. "
            "Set ADMIN_IDS or ADMIN_USERNAMES."
        )

    logger.info(
        "Environment validation successful."
    )


# ============================================================
# SAFE CALL
# ============================================================

async def safe_call(
    fn,
    update,
    context,
    name,
    *args,
    **kwargs,
):

    try:

        result = fn(
            update,
            context,
            *args,
            **kwargs,
        )

        if hasattr(
            result,
            "__await__",
        ):

            return await result

        return result

    except Exception:

        logger.exception(
            "%s failed",
            name,
        )

        message = (
            update.effective_message
            if isinstance(
                update,
                Update,
            )
            else None
        )

        if message:

            try:

                await message.reply_text(
                    "⚠️ इस option को process करते समय error आया।\n"
                    "Admin log में पूरी जानकारी उपलब्ध है।"
                )

            except Exception:

                pass

        return None


# ============================================================
# USER STATE HELPER
# ============================================================

def get_user_state(
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Safely return user_data.

    PTB normally provides a dict. Some custom/persistence
    situations can return None. Never call .get() directly
    without checking.
    """

    data = getattr(
        context,
        "user_data",
        None,
    )

    if isinstance(
        data,
        dict,
    ):

        return data

    return {}


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
        query.data or ""
    ).strip()

    logger.info(
        "Callback received: %s",
        data,
    )

    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    if data == "home":

        try:
            await query.answer()
        except Exception:
            pass

        return await safe_call(
            user_handlers.handle_callback,
            update,
            context,
            "home",
        )

    # --------------------------------------------------------
    # USER CALLBACKS
    # --------------------------------------------------------

    if data.startswith(
        (
            "menu:",
            "user:",
            "trial:",
            "purchase:",
        )
    ):

        return await safe_call(
            user_handlers.handle_callback,
            update,
            context,
            "user callback",
        )

    # --------------------------------------------------------
    # FORCE JOIN
    # --------------------------------------------------------

    if data == "check_force_join":

        return await safe_call(
            user_handlers.start,
            update,
            context,
            "force join refresh",
        )

    # --------------------------------------------------------
    # INDEX
    # --------------------------------------------------------

    if data.startswith(
        (
            "index:",
            "category:",
            "exam:",
            "type:",
            "year:",
        )
    ):

        return await safe_call(
            index_handlers.handle_callback,
            update,
            context,
            "index callback",
        )

    # --------------------------------------------------------
    # EXTRACT
    # --------------------------------------------------------

    if data.startswith(
        (
            "test:",
            "extract:",
            "retry:",
            "retry_extract:",
            "extract_confirm:",
        )
    ):

        return await safe_call(
            extract_handlers.handle_callback,
            update,
            context,
            "extract callback",
        )

    # --------------------------------------------------------
    # PAYMENT
    # --------------------------------------------------------

    if data.startswith(
        "payment:"
    ):

        return await safe_call(
            payment_handlers.handle_callback,
            update,
            context,
            "payment callback",
        )

    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------

    if data.startswith(
        "admin:"
    ):

        return await safe_call(
            admin_handlers.handle_callback,
            update,
            context,
            "admin callback",
        )

    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

    if data.startswith(
        "upload:"
    ):

        if data == "upload:manual":

            return await safe_call(
                upload_handlers.start_upload,
                update,
                context,
                "manual upload",
            )

        if data == "upload:bulk":

            return await safe_call(
                upload_handlers.start_bulk_upload,
                update,
                context,
                "bulk upload",
            )

        try:

            await query.answer(
                "Upload option updated in /upload",
                show_alert=True,
            )

        except Exception:

            pass

        return

    # --------------------------------------------------------
    # HELP
    # --------------------------------------------------------

    if data in (
        "help",
        "commands",
    ):

        return await safe_call(
            user_handlers.help_command,
            update,
            context,
            "help",
        )

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    try:

        await query.answer(
            "Unknown option",
            show_alert=True,
        )

    except Exception:

        pass

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
            "Document processing error"
        )

        if update.effective_message:

            try:

                await update.effective_message.reply_text(
                    "❌ File process करते समय error आया।"
                )

            except Exception:

                pass


# ============================================================
# TEXT ROUTER
# ============================================================

async def text_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    user = update.effective_user

    if not message or not user:

        return

    try:

        # ====================================================
        # IMPORTANT:
        # ADMIN ACTION MUST BE CHECKED FIRST
        # ====================================================

        state = get_user_state(
            context
        )

        admin_action = state.get(
            "admin_action"
        )

        upload_mode = state.get(
            "upload_mode"
        )

        logger.info(
            "Text received | user=%s | admin_action=%s | upload_mode=%s",
            user.id,
            admin_action,
            upload_mode,
        )

        # ====================================================
        # ADMIN TEXT FLOW
        # ====================================================

        if CONFIG.is_admin(user):

            try:

                handled = await admin_handlers.handle_admin_text(
                    update,
                    context,
                )

                if handled:

                    return

            except Exception:

                logger.exception(
                    "Admin text handler error"
                )

                try:

                    await message.reply_text(
                        "⚠️ Admin input process करते समय error आया।"
                    )

                except Exception:

                    pass

                return

        # ====================================================
        # UPLOAD TEXT FLOW
        # ====================================================

        if upload_mode in (
            "manual",
            "bulk",
        ):

            try:

                handled = await upload_handlers.handle_text(
                    update,
                    context,
                )

                if handled:

                    return

            except Exception:

                logger.exception(
                    "Upload text handler error"
                )

                try:

                    await message.reply_text(
                        "❌ Upload process करते समय error आया।"
                    )

                except Exception:

                    pass

                return

        # ====================================================
        # NORMAL USER TEXT
        # ====================================================

        try:

            handled = await user_handlers.handle_message(
                update,
                context,
            )

            if handled:

                return

        except Exception:

            logger.exception(
                "User text handler error"
            )

            try:

                await message.reply_text(
                    "⚠️ Message process करते समय error आया।"
                )

            except Exception:

                pass

    except Exception:

        logger.exception(
            "Text handler error"
        )

        try:

            await message.reply_text(
                "⚠️ Message process करते समय unexpected error आया।"
            )

        except Exception:

            pass


# ============================================================
# USER COMMANDS
# ============================================================

async def start_command(
    update,
    context,
):

    await safe_call(
        user_handlers.start,
        update,
        context,
        "/start",
    )


async def help_command(
    update,
    context,
):

    await safe_call(
        user_handlers.help_command,
        update,
        context,
        "/help",
    )


async def menu_command(
    update,
    context,
):

    await safe_call(
        user_handlers.start,
        update,
        context,
        "/menu",
    )


async def index_command(
    update,
    context,
):

    await safe_call(
        index_handlers.show_categories,
        update,
        context,
        "/index",
    )


async def price_command(
    update,
    context,
):

    await safe_call(
        user_handlers.show_price,
        update,
        context,
        "/price",
    )


async def userinfo_command(
    update,
    context,
):

    await safe_call(
        user_handlers.user_info,
        update,
        context,
        "/userinfo",
    )


async def trial_command(
    update,
    context,
):

    await safe_call(
        user_handlers.show_trial,
        update,
        context,
        "/trial",
    )


async def report_command(
    update,
    context,
):

    await safe_call(
        user_handlers.report_menu,
        update,
        context,
        "/report",
    )


# ============================================================
# ADMIN COMMANDS
# ============================================================

async def admin_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.admin_command,
        update,
        context,
        "/admin",
    )


async def admin_stats_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.stats,
        update,
        context,
        "/stats",
    )


async def admin_users_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.user_list,
        update,
        context,
        "/users",
    )


async def admin_paidusers_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.paid_users,
        update,
        context,
        "/paidusers",
    )


async def admin_trial_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.trial_settings,
        update,
        context,
        "/trialsettings",
    )


async def admin_broadcast_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.broadcast_start,
        update,
        context,
        "/broadcast",
    )


async def admin_price_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.price_settings,
        update,
        context,
        "/adminprice",
    )


async def admin_welcome_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.welcome_settings,
        update,
        context,
        "/welcome",
    )


async def admin_forcejoin_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.force_join,
        update,
        context,
        "/forcejoin",
    )


async def admin_backup_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.backup,
        update,
        context,
        "/backup",
    )


async def admin_testreport_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.test_report,
        update,
        context,
        "/testreport",
    )


async def admin_queue_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.queue_status,
        update,
        context,
        "/queue",
    )


async def admin_settings_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.settings,
        update,
        context,
        "/settings",
    )


# ============================================================
# CHANNEL COMMAND WRAPPERS
# ============================================================

async def admin_database_channel_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.channel_settings,
        update,
        context,
        "database channel",
        "database",
        "DATABASE CHANNEL",
    )


async def admin_payment_channel_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.channel_settings,
        update,
        context,
        "payment channel",
        "payment",
        "PAYMENT VERIFICATION CHANNEL",
    )


async def admin_user_channel_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.channel_settings,
        update,
        context,
        "user activity channel",
        "user_activity",
        "USER ACTIVITY CHANNEL",
    )


async def admin_paid_channel_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.channel_settings,
        update,
        context,
        "paid channel",
        "paid",
        "PAID CHANNEL",
    )


async def admin_paid_user_channel_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.channel_settings,
        update,
        context,
        "paid user channel",
        "paid_user",
        "PAID USER CHANNEL",
    )


async def admin_ban_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.ban_start,
        update,
        context,
        "/ban",
    )


async def admin_unban_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.unban_start,
        update,
        context,
        "/unban",
    )


async def admin_trial_lock_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.trial_lock_start,
        update,
        context,
        "/triallock",
    )


async def admin_addtest_command(
    update,
    context,
):

    await safe_call(
        upload_handlers.start_upload,
        update,
        context,
        "/addtest",
    )


# ============================================================
# ID
# ============================================================

async def id_command(
    update,
    context,
):

    user = update.effective_user

    message = update.effective_message

    if not user or not message:

        return

    configured = CONFIG.is_admin(
        user
    )

    await message.reply_text(
        "🆔 **Your Telegram ID**\n\n"
        f"`{user.id}`\n\n"
        f"Admin configured: "
        f"{'✅ YES' if configured else '❌ NO'}\n\n"
        "अगर Admin = NO है तो Render में "
        "ADMIN_IDS में यही ID डालें या "
        "ADMIN_USERNAMES में अपना username डालें।",
        parse_mode="Markdown",
    )


async def stats_command(
    update,
    context,
):

    await safe_call(
        admin_handlers.stats,
        update,
        context,
        "/stats",
    )


async def upload_command(
    update,
    context,
):

    await safe_call(
        upload_handlers.start_upload,
        update,
        context,
        "/upload",
    )


async def extract_command(
    update,
    context,
):

    await safe_call(
        index_handlers.show_categories,
        update,
        context,
        "/extract",
    )


# ============================================================
# SEED
# ============================================================

async def seed_command(
    update,
    context,
):

    user = update.effective_user

    if not user or not CONFIG.is_admin(user):

        if update.effective_message:

            await update.effective_message.reply_text(
                "🚫 यह command केवल Admin के लिए है।"
            )

        return

    test_id = db.seed_demo_test()

    await update.effective_message.reply_text(
        "🧪 Demo Test तैयार है!\n\n"
        f"🆔 Test ID: `{test_id}`\n"
        "अब /index खोलकर पूरा flow test करें।",
        parse_mode="Markdown",
    )


# ============================================================
# COMMANDS
# ============================================================

async def commands_command(
    update,
    context,
):

    user = update.effective_user

    admin = bool(
        user
        and CONFIG.is_admin(user)
    )

    text = (
        "📋 *COMMAND MENU*\n\n"

        "👤 User Commands\n"
        "/start — Main menu\n"
        "/menu — Main menu\n"
        "/help — Help\n"
        "/index — Test index\n"
        "/extract — Extract test\n"
        "/price — Premium plans\n"
        "/trial — Free trial\n"
        "/userinfo — My account\n"
        "/report — Report problem\n"
        "/id — Show Telegram ID\n\n"
    )

    if admin:

        text += (
            "🛠️ *Admin Commands*\n"
            "/admin — Admin panel\n"
            "/stats — Bot statistics\n"
            "/users — User list\n"
            "/paidusers — Paid users\n"
            "/upload — Upload test\n"
            "/addtest — Add test\n"
            "/ban — Ban user\n"
            "/unban — Unban user\n"
            "/triallock — Lock trial\n"
            "/trialsettings — Trial settings\n"
            "/broadcast — Broadcast\n"
            "/adminprice — Price settings\n"
            "/welcome — Welcome settings\n"
            "/forcejoin — Force join\n"
            "/backup — Backup\n"
            "/testreport — Test report\n"
            "/queue — Queue status\n"
            "/settings — Bot settings\n"
            "/database — Database channel\n"
            "/paymentchannel — Payment channel\n"
            "/userchannel — User activity channel\n"
            "/paidchannel — Paid channel\n"
            "/paiduserchannel — Paid user channel\n"
            "/seed — Add demo test\n"
        )

    keyboard = user_handlers.main_keyboard(
        paid=(
            db.is_paid_user(user.id)
            if user
            else False
        ),
        is_admin=admin,
    )

    if update.callback_query:

        await update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    else:

        await update.effective_message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


# ============================================================
# POST INIT
# ============================================================

async def post_init(
    application: Application,
):

    logger.info(
        "Bot initialization started."
    )

    queue_manager.set_bot(
        application.bot
    )

    # --------------------------------------------------------
    # QUEUE
    # --------------------------------------------------------

    queue_manager.register_processor(
        "test_extract",
        extract_handlers.process_extract_job,
    )

    queue_manager.register_processor(
        "test_upload",
        upload_handlers.process_upload_job,
    )

    await queue_manager.start()

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    try:

        db.ensure_indexes()

    except Exception:

        logger.exception(
            "Database index initialization failed."
        )

    # --------------------------------------------------------
    # USER COMMANDS
    # --------------------------------------------------------

    user_commands = [
        BotCommand(
            "start",
            "Main menu",
        ),
        BotCommand(
            "menu",
            "Main menu",
        ),
        BotCommand(
            "help",
            "Help",
        ),
        BotCommand(
            "index",
            "Test index",
        ),
        BotCommand(
            "extract",
            "Extract test",
        ),
        BotCommand(
            "price",
            "Premium plans",
        ),
        BotCommand(
            "trial",
            "Free trial",
        ),
        BotCommand(
            "userinfo",
            "My account",
        ),
        BotCommand(
            "report",
            "Report problem",
        ),
        BotCommand(
            "id",
            "Show Telegram ID",
        ),
        BotCommand(
            "commands",
            "All commands",
        ),
    ]

    await application.bot.set_my_commands(
        user_commands
    )

    # --------------------------------------------------------
    # ADMIN COMMANDS
    # --------------------------------------------------------

    admin_commands = (
        user_commands
        + [
            BotCommand(
                "admin",
                "Admin panel",
            ),
            BotCommand(
                "stats",
                "Bot statistics",
            ),
            BotCommand(
                "users",
                "User list",
            ),
            BotCommand(
                "paidusers",
                "Paid users",
            ),
            BotCommand(
                "upload",
                "Upload test",
            ),
            BotCommand(
                "addtest",
                "Add test",
            ),
            BotCommand(
                "ban",
                "Ban user",
            ),
            BotCommand(
                "unban",
                "Unban user",
            ),
            BotCommand(
                "triallock",
                "Lock trial",
            ),
            BotCommand(
                "trialsettings",
                "Trial settings",
            ),
            BotCommand(
                "broadcast",
                "Broadcast",
            ),
            BotCommand(
                "adminprice",
                "Price settings",
            ),
            BotCommand(
                "welcome",
                "Welcome settings",
            ),
            BotCommand(
                "forcejoin",
                "Force join",
            ),
            BotCommand(
                "backup",
                "Database backup",
            ),
            BotCommand(
                "testreport",
                "Test report",
            ),
            BotCommand(
                "queue",
                "Queue status",
            ),
            BotCommand(
                "settings",
                "Bot settings",
            ),
            BotCommand(
                "database",
                "Database channel",
            ),
            BotCommand(
                "paymentchannel",
                "Payment channel",
            ),
            BotCommand(
                "userchannel",
                "User activity channel",
            ),
            BotCommand(
                "paidchannel",
                "Paid channel",
            ),
            BotCommand(
                "paiduserchannel",
                "Paid user channel",
            ),
            BotCommand(
                "seed",
                "Add demo test",
            ),
        ]
    )

    for admin_id in CONFIG.admin_ids:

        try:

            await application.bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(
                    admin_id
                ),
            )

        except Exception:

            logger.exception(
                "Could not set admin command menu for %s",
                admin_id,
            )

    logger.info(
        "Bot initialization completed."
    )


# ============================================================
# POST SHUTDOWN
# ============================================================

async def post_shutdown(
    application: Application,
):

    logger.info(
        "Bot shutdown started."
    )

    try:

        await queue_manager.stop()

    except Exception:

        logger.exception(
            "Queue manager shutdown failed"
        )

    try:

        db.close()

    except Exception:

        logger.exception(
            "Database close failed"
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

    # --------------------------------------------------------
    # COMMAND REGISTRATION
    # --------------------------------------------------------

    commands = [

        (
            "start",
            start_command,
        ),

        (
            "menu",
            menu_command,
        ),

        (
            "help",
            help_command,
        ),

        (
            "commands",
            commands_command,
        ),

        (
            "index",
            index_command,
        ),

        (
            "extract",
            extract_command,
        ),

        (
            "price",
            price_command,
        ),

        (
            "trial",
            trial_command,
        ),

        (
            "userinfo",
            userinfo_command,
        ),

        (
            "report",
            report_command,
        ),

        (
            "id",
            id_command,
        ),

        (
            "admin",
            admin_command,
        ),

        (
            "stats",
            admin_stats_command,
        ),

        (
            "users",
            admin_users_command,
        ),

        (
            "paidusers",
            admin_paidusers_command,
        ),

        (
            "upload",
            upload_command,
        ),

        (
            "addtest",
            admin_addtest_command,
        ),

        (
            "ban",
            admin_ban_command,
        ),

        (
            "unban",
            admin_unban_command,
        ),

        (
            "triallock",
            admin_trial_lock_command,
        ),

        (
            "trialsettings",
            admin_trial_command,
        ),

        (
            "broadcast",
            admin_broadcast_command,
        ),

        (
            "adminprice",
            admin_price_command,
        ),

        (
            "welcome",
            admin_welcome_command,
        ),

        (
            "forcejoin",
            admin_forcejoin_command,
        ),

        (
            "backup",
            admin_backup_command,
        ),

        (
            "testreport",
            admin_testreport_command,
        ),

        (
            "queue",
            admin_queue_command,
        ),

        (
            "settings",
            admin_settings_command,
        ),

        (
            "database",
            admin_database_channel_command,
        ),

        (
            "paymentchannel",
            admin_payment_channel_command,
        ),

        (
            "userchannel",
            admin_user_channel_command,
        ),

        (
            "paidchannel",
            admin_paid_channel_command,
        ),

        (
            "paiduserchannel",
            admin_paid_user_channel_command,
        ),

        (
            "seed",
            seed_command,
        ),
    ]

    for name, handler in commands:

        application.add_handler(
            CommandHandler(
                name,
                handler,
            )
        )

    # --------------------------------------------------------
    # CALLBACKS
    # --------------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    # --------------------------------------------------------
    # DOCUMENTS
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            document_router,
        )
    )

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router,
        )
    )

    return application


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "Starting Telegram Test Series Bot..."
    )

    threading.Thread(
        target=start_health_server,
        daemon=True,
        name="health-server",
    ).start()

    application = build_application()

    logger.info(
        "Telegram polling starting..."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()

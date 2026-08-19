import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ContextTypes,
)

from .config import CONFIG
from .database import db
from .github import github
from .telegram_utils import telegram_utils

logger = logging.getLogger(__name__)


class AdminHandlers:
    """
    ADMIN PANEL

    Features:

    1.  Bot Stats
    2.  User List
    3.  Paid User List
    4.  Ban User
    5.  Unban User
    6.  Free Trial
    7.  Trial Lock
    8.  Broadcast
    9.  Price
    10. Welcome Message
    11. Upload Test
    12. Force Join Channel
    13. Backup
    14. Test Extract Reports
    15. Payment Verification
    16. User Activity Channel
    17. User Info
    18. Paid User Channel
    19. Maintenance
    20. Queue Status
    """

    # ============================================================
    # ADMIN CHECK
    # ============================================================

    async def is_admin(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> bool:

        user = update.effective_user

        if not user:
            return False

        if user.id in CONFIG.admin_ids:
            return True

        message = update.effective_message

        if message:

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                "🚫 यह section केवल Admin के लिए है।",
            )

        return False

    # ============================================================
    # /ADMIN
    # ============================================================

    async def admin_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        await self.show_panel(
            update,
            context,
        )

    # ============================================================
    # ADMIN PANEL
    # ============================================================

    async def show_panel(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        text = (
            "🛠️ **ADMIN CONTROL PANEL**\n\n"
            "नीचे किसी भी feature को select करें:"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📊 BOT STATS",
                        callback_data="admin:stats",
                    ),
                    InlineKeyboardButton(
                        "👥 USER LIST",
                        callback_data="admin:users",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "💎 PAID USERS",
                        callback_data="admin:paidusers",
                    ),
                    InlineKeyboardButton(
                        "🚫 BAN USER",
                        callback_data="admin:ban",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "✅ UNBAN USER",
                        callback_data="admin:unban",
                    ),
                    InlineKeyboardButton(
                        "🆓 FREE TRIAL",
                        callback_data="admin:trial",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "🔒 TRIAL LOCK",
                        callback_data="admin:trial_lock",
                    ),
                    InlineKeyboardButton(
                        "📢 BROADCAST",
                        callback_data="admin:broadcast",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "💰 PRICE",
                        callback_data="admin:price",
                    ),
                    InlineKeyboardButton(
                        "👋 WELCOME",
                        callback_data="admin:welcome",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "📤 UPLOAD TEST",
                        callback_data="admin:upload",
                    ),
                    InlineKeyboardButton(
                        "📚 TEST REPORT",
                        callback_data="admin:report",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "📢 FORCE JOIN",
                        callback_data="admin:forcejoin",
                    ),
                    InlineKeyboardButton(
                        "💾 BACKUP",
                        callback_data="admin:backup",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "💳 PAYMENT CHANNEL",
                        callback_data="admin:payment_channel",
                    ),
                    InlineKeyboardButton(
                        "👤 USER CHANNEL",
                        callback_data="admin:user_channel",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "💎 PAID USER CHANNEL",
                        callback_data="admin:paid_channel",
                    ),
                    InlineKeyboardButton(
                        "⚙️ SETTINGS",
                        callback_data="admin:settings",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "⚡ QUEUE STATUS",
                        callback_data="admin:queue",
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🏠 HOME",
                        callback_data="home",
                    )
                ],
            ]
        )

        query = update.callback_query

        if query:

            try:

                await query.edit_message_text(
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )

                return

            except Exception:

                pass

        message = update.effective_message

        if message:

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

    # ============================================================
    # BOT STATS
    # ============================================================

    async def stats(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        stats = db.get_bot_stats()

        text = (
            "📊 **BOT STATISTICS**\n\n"

            f"👥 Total Users: "
            f"**{stats.get('total_users', 0):,}**\n"

            f"🟢 Active Users: "
            f"**{stats.get('active_users', 0):,}**\n"

            f"💎 Paid Users: "
            f"**{stats.get('paid_users', 0):,}**\n"

            f"🚫 Banned Users: "
            f"**{stats.get('banned_users', 0):,}**\n\n"

            f"📚 Total Tests: "
            f"**{stats.get('total_tests', 0):,}**\n"

            f"🚀 Total Extracts: "
            f"**{stats.get('total_extracts', 0):,}**\n"

            f"✅ Successful: "
            f"**{stats.get('successful_extracts', 0):,}**\n"

            f"❌ Failed: "
            f"**{stats.get('failed_extracts', 0):,}**\n\n"

            f"💰 Revenue: "
            f"**₹{stats.get('revenue', 0):,.2f}**\n\n"

            f"⏳ Queue: "
            f"**{stats.get('queue_size', 0)}**"
        )

        await self._edit_or_send(
            update,
            context,
            text,
            self.back_panel(),
        )

    # ============================================================
    # USER LIST
    # ============================================================

    async def user_list(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        page: int = 1,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        per_page = 15

        users = db.get_users(
            page=page,
            per_page=per_page,
        )

        total = db.count_users()

        text = (
            "👥 **USER LIST**\n\n"
            f"Total Users: **{total:,}**\n\n"
        )

        if not users:

            text += "कोई User नहीं मिला।"

        else:

            start = (
                (page - 1)
                * per_page
                + 1
            )

            for index, user in enumerate(
                users,
                start=start,
            ):

                name = (
                    user.get(
                        "name",
                        "-",
                    )
                    or "-"
                )

                username = (
                    user.get(
                        "username",
                        "",
                    )
                    or "-"
                )

                paid = (
                    "💎"
                    if db.is_paid_user(
                        user.get(
                            "user_id"
                        )
                    )
                    else "🆓"
                )

                banned = (
                    "🚫"
                    if user.get(
                        "banned",
                        False,
                    )
                    else ""
                )

                text += (
                    f"{index}. {paid}{banned} "
                    f"{name[:25]}\n"
                    f"   🆔 `{user.get('user_id')}` "
                    f"@{username}\n"
                )

        rows = []

        navigation = []

        if page > 1:

            navigation.append(
                InlineKeyboardButton(
                    "⬅️ Previous",
                    callback_data=(
                        f"admin:users:{page - 1}"
                    ),
                )
            )

        if (
            page * per_page
            < total
        ):

            navigation.append(
                InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=(
                        f"admin:users:{page + 1}"
                    ),
                )
            )

        if navigation:

            rows.append(
                navigation
            )

        rows.append(
            [
                InlineKeyboardButton(
                    "🔄 Refresh",
                    callback_data=(
                        f"admin:users:{page}"
                    ),
                )
            ]
        )

        rows.append(
            self.back_panel()
        )

        await self._edit_or_send(
            update,
            context,
            text,
            InlineKeyboardMarkup(rows),
        )

    # ============================================================
    # PAID USERS
    # ============================================================

    async def paid_users(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        page: int = 1,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        per_page = 15

        users = db.get_paid_users(
            page=page,
            per_page=per_page,
        )

        total = db.count_paid_users()

        text = (
            "💎 **PAID USER LIST**\n\n"
            f"Total Paid Users: **{total:,}**\n\n"
        )

        if not users:

            text += "कोई Paid User नहीं मिला।"

        else:

            for index, user in enumerate(
                users,
                start=(
                    (page - 1)
                    * per_page
                    + 1
                ),
            ):

                text += (
                    f"{index}. "
                    f"👤 {user.get('name', '-')}\n"
                    f"   🆔 `{user.get('user_id')}`\n"
                    f"   📦 {user.get('paid_plan', '-')}\n"
                    f"   ⏰ {user.get('paid_expiry', '-')}\n\n"
                )

        rows = []

        navigation = []

        if page > 1:

            navigation.append(
                InlineKeyboardButton(
                    "⬅️ Previous",
                    callback_data=(
                        f"admin:paidusers:{page - 1}"
                    ),
                )
            )

        if (
            page * per_page
            < total
        ):

            navigation.append(
                InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=(
                        f"admin:paidusers:{page + 1}"
                    ),
                )
            )

        if navigation:

            rows.append(
                navigation
            )

        rows.append(
            self.back_panel()
        )

        await self._edit_or_send(
            update,
            context,
            text,
            InlineKeyboardMarkup(rows),
        )

    # ============================================================
    # BAN
    # ============================================================

    async def ban_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        context.user_data[
            "admin_action"
        ] = "ban"

        await self._ask(
            update,
            context,
            (
                "🚫 **BAN USER**\n\n"
                "जिस User को ban करना है उसका Telegram ID भेजें।"
            ),
        )

    async def ban_user(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
    ):

        db.ban_user(
            user_id
        )

        await telegram_utils.send_message(
            context.bot,
            user_id,
            (
                "🚫 आपका account Admin द्वारा banned कर दिया गया है।"
            ),
        )

        await self._admin_success(
            update,
            context,
            f"✅ User `{user_id}` banned.",
        )

    # ============================================================
    # UNBAN
    # ============================================================

    async def unban_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        context.user_data[
            "admin_action"
        ] = "unban"

        await self._ask(
            update,
            context,
            (
                "✅ **UNBAN USER**\n\n"
                "User Telegram ID भेजें।"
            ),
        )

    async def unban_user(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
    ):

        db.unban_user(
            user_id
        )

        await telegram_utils.send_message(
            context.bot,
            user_id,
            "✅ आपका account unban कर दिया गया है।",
        )

        await self._admin_success(
            update,
            context,
            f"✅ User `{user_id}` unbanned.",
        )

    # ============================================================
    # FREE TRIAL SETTINGS
    # ============================================================

    async def trial_settings(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        enabled = db.get_setting(
            "trial_enabled",
            True,
        )

        allowed = db.get_setting(
            "trial_allowed",
            True,
        )

        days = db.get_setting(
            "trial_days",
            1,
        )

        limit = db.get_setting(
            "trial_extract_limit",
            1,
        )

        text = (
            "🆓 **FREE TRIAL SETTINGS**\n\n"
            f"Status: "
            f"{'🟢 ON' if enabled else '🔴 OFF'}\n"
            f"Allowed: "
            f"{'🟢 YES' if allowed else '🔴 NO'}\n"
            f"Duration: **{days} day(s)**\n"
            f"Extract Limit: **{limit}**"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🟢 Enable",
                        callback_data="admin:trial:on",
                    ),
                    InlineKeyboardButton(
                        "🔴 Disable",
                        callback_data="admin:trial:off",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "⏱ Set Days",
                        callback_data="admin:trial_days",
                    ),
                    InlineKeyboardButton(
                        "📚 Set Limit",
                        callback_data="admin:trial_limit",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "🔒 Lock User Trial",
                        callback_data="admin:trial_lock",
                    )
                ],

                self.back_panel(),
            ]
        )

        await self._edit_or_send(
            update,
            context,
            text,
            keyboard,
        )

    # ============================================================
    # TRIAL LOCK
    # ============================================================

    async def trial_lock_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        context.user_data[
            "admin_action"
        ] = "trial_lock"

        await self._ask(
            update,
            context,
            (
                "🔒 **TRIAL LOCK**\n\n"
                "User ID भेजें जिसे Trial से lock करना है।"
            ),
        )

    async def trial_lock_user(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
    ):

        db.lock_trial(
            user_id
        )

        await telegram_utils.send_message(
            context.bot,
            user_id,
            (
                "🔒 आपका Free Trial Admin द्वारा lock कर दिया गया है।"
            ),
        )

        await self._admin_success(
            update,
            context,
            f"🔒 Trial locked for `{user_id}`.",
        )

    # ============================================================
    # BROADCAST
    # ============================================================

    async def broadcast_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        context.user_data[
            "admin_action"
        ] = "broadcast"

        await self._ask(
            update,
            context,
            (
                "📢 **BROADCAST**\n\n"
                "अब जो message भेजेंगे वही Users को broadcast होगा।\n\n"
                "⚠️ बहुत बड़े user base में bot rate-limit के अनुसार "
                "batch में भेजेगा।"
            ),
        )

    async def broadcast(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        message = update.effective_message

        if not message:
            return

        users = db.get_all_user_ids()

        success = 0
        failed = 0

        status_message = await telegram_utils.send_message(
            context.bot,
            message.chat_id,
            (
                "📢 Broadcast शुरू...\n"
                f"👥 Users: {len(users):,}\n\n"
                "⏳ Please wait..."
            ),
        )

        for index, user_id in enumerate(
            users,
            start=1,
        ):

            try:

                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=message.chat_id,
                    message_id=message.message_id,
                )

                success += 1

            except Exception:

                failed += 1

            # ----------------------------------------------------
            # Flood control
            # ----------------------------------------------------

            await asyncio.sleep(
                CONFIG.broadcast_delay
            )

            # ----------------------------------------------------
            # Live admin report
            # ----------------------------------------------------

            if (
                status_message
                and (
                    index % 50 == 0
                    or index == len(users)
                )
            ):

                await telegram_utils.update_progress_message(
                    context,
                    status_message,
                    (
                        "📢 **Broadcast Running**\n\n"
                        f"📊 Progress: {index}/{len(users)}\n"
                        f"✅ Success: {success}\n"
                        f"❌ Failed: {failed}"
                    ),
                    force=True,
                )

        if status_message:

            await telegram_utils.update_progress_message(
                context,
                status_message,
                (
                    "✅ **Broadcast Completed**\n\n"
                    f"👥 Total: {len(users)}\n"
                    f"✅ Success: {success}\n"
                    f"❌ Failed: {failed}"
                ),
                force=True,
            )

        context.user_data.pop(
            "admin_action",
            None,
        )

    # ============================================================
    # PRICE
    # ============================================================

    async def price_settings(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        prices = db.get_setting(
            "prices",
            {},
        )

        text = (
            "💰 **PRICE SETTINGS**\n\n"
        )

        if prices:

            for plan, price in prices.items():

                text += (
                    f"📦 {plan}: ₹{price}\n"
                )

        else:

            text += (
                "अभी कोई plan नहीं है।"
            )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ ADD / UPDATE",
                        callback_data="admin:price_set",
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🗑 DELETE PLAN",
                        callback_data="admin:price_delete",
                    )
                ],

                self.back_panel(),
            ]
        )

        await self._edit_or_send(
            update,
            context,
            text,
            keyboard,
        )

    async def price_set_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        context.user_data[
            "admin_action"
        ] = "price_set"

        await self._ask(
            update,
            context,
            (
                "💰 **SET PRICE**\n\n"
                "Format:\n"
                "`30_days=149`\n\n"
                "उदाहरण:\n"
                "`7_days=49`"
            ),
        )

    # ============================================================
    # WELCOME
    # ============================================================

    async def welcome_settings(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        welcome = db.get_setting(
            "welcome_message",
            "",
        )

        enabled = db.get_setting(
            "welcome_enabled",
            True,
        )

        text = (
            "👋 **WELCOME SETTINGS**\n\n"
            f"Status: "
            f"{'🟢 ON' if enabled else '🔴 OFF'}\n\n"
            f"Current Message:\n"
            f"{welcome}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✏️ CHANGE MESSAGE",
                        callback_data="admin:welcome_set",
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🟢 ON",
                        callback_data="admin:welcome:on",
                    ),
                    InlineKeyboardButton(
                        "🔴 OFF",
                        callback_data="admin:welcome:off",
                    ),
                ],

                self.back_panel(),
            ]
        )

        await self._edit_or_send(
            update,
            context,
            text,
            keyboard,
        )

    async def welcome_set_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        context.user_data[
            "admin_action"
        ] = "welcome_set"

        await self._ask(
            update,
            context,
            (
                "👋 नया Welcome Message भेजें।"
            ),
        )

    # ============================================================
    # FORCE JOIN
    # ============================================================

    async def force_join(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        channels = db.get_force_join_channels()

        text = (
            "📢 **FORCE JOIN CHANNELS**\n\n"
        )

        if not channels:

            text += (
                "कोई channel configured नहीं है।"
            )

        else:

            for index, channel in enumerate(
                channels,
                start=1,
            ):

                status = (
                    "🟢"
                    if channel.get(
                        "enabled",
                        True,
                    )
                    else "🔴"
                )

                text += (
                    f"{index}. {status} "
                    f"{channel.get('title', '-')}\n"
                    f"   ID: `{channel.get('channel_id')}`\n\n"
                )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ ADD CHANNEL",
                        callback_data="admin:forcejoin_add",
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🗑 REMOVE CHANNEL",
                        callback_data="admin:forcejoin_remove",
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🟢 ENABLE",
                        callback_data="admin:forcejoin:on",
                    ),
                    InlineKeyboardButton(
                        "🔴 DISABLE",
                        callback_data="admin:forcejoin:off",
                    ),
                ],

                self.back_panel(),
            ]
        )

        await self._edit_or_send(
            update,
            context,
            text,
            keyboard,
        )

    async def forcejoin_add_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        context.user_data[
            "admin_action"
        ] = "forcejoin_add"

        await self._ask(
            update,
            context,
            (
                "📢 Channel का username या ID भेजें।\n\n"
                "उदाहरण:\n"
                "`@mychannel`"
            ),
        )

    # ============================================================
    # BACKUP
    # ============================================================

    async def backup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        tests = db.get_all_tests_for_backup()

        text = (
            "💾 **DATABASE BACKUP**\n\n"
            f"📚 Tests: {len(tests):,}\n\n"
            "Backup शुरू किया जा सकता है।"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🚀 START BACKUP",
                        callback_data="admin:backup_start",
                    )
                ],

                self.back_panel(),
            ]
        )

        await self._edit_or_send(
            update,
            context,
            text,
            keyboard,
        )

    # ============================================================
    # TEST REPORT
    # ============================================================

    async def test_report(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        report = db.get_extract_report()

        text = (
            "📊 **TEST EXTRACT REPORT**\n\n"
        )

        if not report:

            text += (
                "अभी कोई extraction data नहीं है।"
            )

        else:

            for index, item in enumerate(
                report,
                start=1,
            ):

                text += (
                    f"{index}. "
                    f"📚 {item.get('title', '-')}\n"
                    f"   🎯 {item.get('exam', '-')}\n"
                    f"   🚀 Extracts: "
                    f"**{item.get('extract_count', 0)}**\n\n"
                )

        await self._edit_or_send(
            update,
            context,
            text,
            self.back_panel(),
        )

    # ============================================================
    # QUEUE STATUS
    # ============================================================

    async def queue_status(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        status = db.get_queue_status()

        text = (
            "⚡ **QUEUE STATUS**\n\n"
            f"📥 Queued: "
            f"**{status.get('queued', 0)}**\n"
            f"⚙️ Processing: "
            f"**{status.get('processing', 0)}**\n"
            f"🔄 Retrying: "
            f"**{status.get('retrying', 0)}**\n"
            f"✅ Done: "
            f"**{status.get('done', 0)}**\n"
            f"❌ Failed: "
            f"**{status.get('failed', 0)}**"
        )

        await self._edit_or_send(
            update,
            context,
            text,
            self.back_panel(),
        )

    # ============================================================
    # CHANNEL SETTINGS
    # ============================================================

    async def channel_settings(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        channel_type: str,
        title: str,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        channel = db.get_channel(
            channel_type
        )

        text = (
            f"📢 **{title}**\n\n"
        )

        if channel:

            text += (
                f"🆔 ID: `{channel.get('channel_id')}`\n"
                f"📛 Name: "
                f"{channel.get('title', '-')}\n"
                f"🔗 Username: "
                f"{channel.get('username', '-')}\n"
            )

        else:

            text += (
                "❌ Channel configured नहीं है।"
            )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ SET / CHANGE",
                        callback_data=(
                            f"admin:setchannel:{channel_type}"
                        ),
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🗑 REMOVE",
                        callback_data=(
                            f"admin:removechannel:{channel_type}"
                        ),
                    )
                ],

                self.back_panel(),
            ]
        )

        await self._edit_or_send(
            update,
            context,
            text,
            keyboard,
        )

    async def set_channel_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        channel_type: str,
    ):

        context.user_data[
            "admin_action"
        ] = (
            "set_channel:"
            + channel_type
        )

        await self._ask(
            update,
            context,
            (
                "📢 Channel username या ID भेजें।"
            ),
        )

    # ============================================================
    # SETTINGS
    # ============================================================

    async def settings(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await self.is_admin(
            update,
            context,
        ):
            return

        maintenance = db.get_setting(
            "maintenance_mode",
            False,
        )

        extract_enabled = db.get_setting(
            "extract_enabled",
            True,
        )

        upload_enabled = db.get_setting(
            "upload_enabled",
            True,
        )

        text = (
            "⚙️ **BOT SETTINGS**\n\n"
            f"🛠 Maintenance: "
            f"{'🟢' if maintenance else '🔴'}\n"
            f"🚀 Extract: "
            f"{'🟢' if extract_enabled else '🔴'}\n"
            f"📤 Upload: "
            f"{'🟢' if upload_enabled else '🔴'}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🛠 Maintenance ON",
                        callback_data="admin:maintenance:on",
                    ),
                    InlineKeyboardButton(
                        "🛠 OFF",
                        callback_data="admin:maintenance:off",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "🚀 Extract ON",
                        callback_data="admin:extract:on",
                    ),
                    InlineKeyboardButton(
                        "🚀 OFF",
                        callback_data="admin:extract:off",
                    ),
                ],

                [
                    InlineKeyboardButton(
                        "📤 Upload ON",
                        callback_data="admin:upload:on",
                    ),
                    InlineKeyboardButton(
                        "📤 OFF",
                        callback_data="admin:upload:off",
                    ),
                ],

                self.back_panel(),
            ]
        )

        await self._edit_or_send(
            update,
            context,
            text,
            keyboard,
        )

    # ============================================================
    # TEXT ACTION HANDLER
    # ============================================================

    async def handle_admin_text(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> bool:

        user = update.effective_user

        message = update.effective_message

        if not user or not message:

            return False

        if user.id not in CONFIG.admin_ids:

            return False

        action = context.user_data.get(
            "admin_action"
        )

        if not action:

            return False

        text = (
            message.text
            or message.caption
            or ""
        ).strip()

        # ========================================================
        # BAN
        # ========================================================

        if action == "ban":

            user_id = self.to_user_id(
                text
            )

            if user_id is None:

                await telegram_utils.send_message(
                    context.bot,
                    message.chat_id,
                    "❌ Valid Telegram ID भेजें।",
                )

                return True

            await self.ban_user(
                update,
                context,
                user_id,
            )

            context.user_data.pop(
                "admin_action",
                None,
            )

            return True

        # ========================================================
        # UNBAN
        # ========================================================

        if action == "unban":

            user_id = self.to_user_id(
                text
            )

            if user_id is None:

                await telegram_utils.send_message(
                    context.bot,
                    message.chat_id,
                    "❌ Valid Telegram ID भेजें।",
                )

                return True

            await self.unban_user(
                update,
                context,
                user_id,
            )

            context.user_data.pop(
                "admin_action",
                None,
            )

            return True

        # ========================================================
        # TRIAL LOCK
        # ========================================================

        if action == "trial_lock":

            user_id = self.to_user_id(
                text
            )

            if user_id is None:

                await telegram_utils.send_message(
                    context.bot,
                    message.chat_id,
                    "❌ Valid Telegram ID भेजें।",
                )

                return True

            await self.trial_lock_user(
                update,
                context,
                user_id,
            )

            context.user_data.pop(
                "admin_action",
                None,
            )

            return True

        # ========================================================
        # BROADCAST
        # ========================================================

        if action == "broadcast":

            await self.broadcast(
                update,
                context,
            )

            return True

        # ========================================================
        # PRICE
        # ========================================================

        if action == "price_set":

            if "=" not in text:

                await telegram_utils.send_message(
                    context.bot,
                    message.chat_id,
                    (
                        "❌ Format गलत है।\n"
                        "Example: `30_days=149`"
                    ),
                    parse_mode="Markdown",
                )

                return True

            plan, price = text.split(
                "=",
                1,
            )

            try:

                price_value = float(
                    price.strip()
                )

            except ValueError:

                await telegram_utils.send_message(
                    context.bot,
                    message.chat_id,
                    "❌ Price number होना चाहिए।",
                )

                return True

            prices = db.get_setting(
                "prices",
                {},
            )

            prices[
                plan.strip()
            ] = price_value

            db.set_setting(
                "prices",
                prices,
            )

            await self._admin_success(
                update,
                context,
                (
                    f"✅ `{plan.strip()}` "
                    f"₹{price_value} set."
                ),
            )

            context.user_data.pop(
                "admin_action",
                None,
            )

            return True

        # ========================================================
        # WELCOME
        # ========================================================

        if action == "welcome_set":

            db.set_setting(
                "welcome_message",
                text,
            )

            await self._admin_success(
                update,
                context,
                "✅ Welcome message updated.",
            )

            context.user_data.pop(
                "admin_action",
                None,
            )

            return True

        # ========================================================
        # FORCE JOIN
        # ========================================================

        if action == "forcejoin_add":

            channel = await telegram_utils.resolve_channel(
                context,
                text,
            )

            if not channel:

                await telegram_utils.send_message(
                    context.bot,
                    message.chat_id,
                    (
                        "❌ Channel resolve नहीं हुआ।\n"
                        "Bot को उस channel में Admin बनाना जरूरी हो सकता है।"
                    ),
                )

                return True

            db.add_force_join_channel(
                channel,
                added_by=user.id,
            )

            await self._admin_success(
                update,
                context,
                (
                    "✅ Force Join channel added.\n"
                    f"📢 {channel.get('title')}"
                ),
            )

            context.user_data.pop(
                "admin_action",
                None,
            )

            return True

        # ========================================================
        # SET CHANNEL
        # ========================================================

        if action.startswith(
            "set_channel:"
        ):

            channel_type = action.split(
                ":",
                1,
            )[1]

            channel = await telegram_utils.resolve_channel(
                context,
                text,
            )

            if not channel:

                await telegram_utils.send_message(
                    context.bot,
                    message.chat_id,
                    "❌ Channel resolve नहीं हुआ।",
                )

                return True

            db.set_channel(
                channel_type,
                channel,
                added_by=user.id,
            )

            await self._admin_success(
                update,
                context,
                (
                    f"✅ {channel_type} channel updated."
                ),
            )

            context.user_data.pop(
                "admin_action",
                None,
            )

            return True

        return False

    # ============================================================
    # CALLBACK ROUTER
    # ============================================================

    async def handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        query = update.callback_query

        if not query:

            return

        if not await self.is_admin(
            update,
            context,
        ):

            await telegram_utils.answer_callback(
                query,
                "🚫 Admin only",
                show_alert=True,
            )

            return

        data = query.data or ""

        await telegram_utils.answer_callback(
            query
        )

        # --------------------------------------------------------
        # Panel
        # --------------------------------------------------------

        if data == "admin:panel":

            return await self.show_panel(
                update,
                context,
            )

        # --------------------------------------------------------
        # Stats
        # --------------------------------------------------------

        if data == "admin:stats":

            return await self.stats(
                update,
                context,
            )

        # --------------------------------------------------------
        # Users
        # --------------------------------------------------------

        if data == "admin:users":

            return await self.user_list(
                update,
                context,
                1,
            )

        if data.startswith(
            "admin:users:"
        ):

            page = self.to_int(
                data.split(
                    ":"
                )[-1],
                1,
            )

            return await self.user_list(
                update,
                context,
                page,
            )

        # --------------------------------------------------------
        # Paid Users
        # --------------------------------------------------------

        if data == "admin:paidusers":

            return await self.paid_users(
                update,
                context,
                1,
            )

        if data.startswith(
            "admin:paidusers:"
        ):

            page = self.to_int(
                data.split(
                    ":"
                )[-1],
                1,
            )

            return await self.paid_users(
                update,
                context,
                page,
            )

        # --------------------------------------------------------
        # Ban
        # --------------------------------------------------------

        if data == "admin:ban":

            return await self.ban_start(
                update,
                context,
            )

        # --------------------------------------------------------
        # Unban
        # --------------------------------------------------------

        if data == "admin:unban":

            return await self.unban_start(
                update,
                context,
            )

        # --------------------------------------------------------
        # Trial
        # --------------------------------------------------------

        if data == "admin:trial":

            return await self.trial_settings(
                update,
                context,
            )

        if data == "admin:trial:on":

            db.set_setting(
                "trial_enabled",
                True,
            )

            return await self.trial_settings(
                update,
                context,
            )

        if data == "admin:trial:off":

            db.set_setting(
                "trial_enabled",
                False,
            )

            return await self.trial_settings(
                update,
                context,
            )

        if data == "admin:trial_lock":

            return await self.trial_lock_start(
                update,
                context,
            )

        # --------------------------------------------------------
        # Broadcast
        # --------------------------------------------------------

        if data == "admin:broadcast":

            return await self.broadcast_start(
                update,
                context,
            )

        # --------------------------------------------------------
        # Price
        # --------------------------------------------------------

        if data == "admin:price":

            return await self.price_settings(
                update,
                context,
            )

        if data == "admin:price_set":

            return await self.price_set_start(
                update,
                context,
            )

        # --------------------------------------------------------
        # Welcome
        # --------------------------------------------------------

        if data == "admin:welcome":

            return await self.welcome_settings(
                update,
                context,
            )

        if data == "admin:welcome_set":

            return await self.welcome_set_start(
                update,
                context,
            )

        if data == "admin:welcome:on":

            db.set_setting(
                "welcome_enabled",
                True,
            )

            return await self.welcome_settings(
                update,
                context,
            )

        if data == "admin:welcome:off":

            db.set_setting(
                "welcome_enabled",
                False,
            )

            return await self.welcome_settings(
                update,
                context,
            )

        # --------------------------------------------------------
        # Force Join
        # --------------------------------------------------------

        if data == "admin:forcejoin":

            return await self.force_join(
                update,
                context,
            )

        if data == "admin:forcejoin_add":

            return await self.forcejoin_add_start(
                update,
                context,
            )

        if data == "admin:forcejoin:on":

            db.set_setting(
                "force_join_enabled",
                True,
            )

            return await self.force_join(
                update,
                context,
            )

        if data == "admin:forcejoin:off":

            db.set_setting(
                "force_join_enabled",
                False,
            )

            return await self.force_join(
                update,
                context,
            )

        # --------------------------------------------------------
        # Backup
        # --------------------------------------------------------

        if data == "admin:backup":

            return await self.backup(
                update,
                context,
            )

        if data == "admin:backup_start":

            return await self._start_backup(
                update,
                context,
            )

        # --------------------------------------------------------
        # Report
        # --------------------------------------------------------

        if data == "admin:report":

            return await self.test_report(
                update,
                context,
            )

        # --------------------------------------------------------
        # Queue
        # --------------------------------------------------------

        if data == "admin:queue":

            return await self.queue_status(
                update,
                context,
            )

        # --------------------------------------------------------
        # Payment Channel
        # --------------------------------------------------------

        if data == "admin:payment_channel":

            return await self.channel_settings(
                update,
                context,
                "payment",
                "PAYMENT VERIFICATION CHANNEL",
            )

        # --------------------------------------------------------
        # User Channel
        # --------------------------------------------------------

        if data == "admin:user_channel":

            return await self.channel_settings(
                update,
                context,
                "user_activity",
                "USER ACTIVITY CHANNEL",
            )

        # --------------------------------------------------------
        # Paid Channel
        # --------------------------------------------------------

        if data == "admin:paid_channel":

            return await self.channel_settings(
                update,
                context,
                "paid_user",
                "PAID USER CHANNEL",
            )

        # --------------------------------------------------------
        # Set Channel
        # --------------------------------------------------------

        if data.startswith(
            "admin:setchannel:"
        ):

            channel_type = data.split(
                ":"
            )[-1]

            return await self.set_channel_start(
                update,
                context,
                channel_type,
            )

        # --------------------------------------------------------
        # Settings
        # --------------------------------------------------------

        if data == "admin:settings":

            return await self.settings(
                update,
                context,
            )

        if data == "admin:maintenance:on":

            db.set_setting(
                "maintenance_mode",
                True,
            )

            return await self.settings(
                update,
                context,
            )

        if data == "admin:maintenance:off":

            db.set_setting(
                "maintenance_mode",
                False,
            )

            return await self.settings(
                update,
                context,
            )

        if data == "admin:extract:on":

            db.set_setting(
                "extract_enabled",
                True,
            )

            return await self.settings(
                update,
                context,
            )

        if data == "admin:extract:off":

            db.set_setting(
                "extract_enabled",
                False,
            )

            return await self.settings(
                update,
                context,
            )

        if data == "admin:upload:on":

            db.set_setting(
                "upload_enabled",
                True,
            )

            return await self.settings(
                update,
                context,
            )

        if data == "admin:upload:off":

            db.set_setting(
                "upload_enabled",
                False,
            )

            return await self.settings(
                update,
                context,
            )

        # --------------------------------------------------------
        # Upload
        # --------------------------------------------------------

        if data == "admin:upload":

            context.user_data[
                "admin_action"
            ] = "upload_test"

            return await self._ask(
                update,
                context,
                (
                    "📤 **TEST UPLOAD**\n\n"
                    "एक Test HTML भेजें।\n\n"
                    "Bulk upload के लिए कई HTML files "
                    "एक साथ document के रूप में भेज सकते हैं।"
                ),
            )

        # --------------------------------------------------------
        # Back
        # --------------------------------------------------------

        if data == "admin:back":

            return await self.show_panel(
                update,
                context,
            )

    # ============================================================
    # BACKUP
    # ============================================================

    async def _start_backup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        tests = db.get_all_tests_for_backup()

        query = update.callback_query

        if not query:

            return

        status = await telegram_utils.edit_message(
            context.bot,
            query.message.chat_id,
            query.message.message_id,
            (
                "💾 **BACKUP STARTED**\n\n"
                f"📚 Tests: {len(tests):,}\n"
                "⏳ Processing..."
            ),
            parse_mode="Markdown",
        )

        success = 0
        failed = 0

        for index, test in enumerate(
            tests,
            start=1,
        ):

            try:

                # GitHub file से HTML download
                path = test.get(
                    "github_path"
                )

                if not path:

                    failed += 1
                    continue

                html = github.download_test(
                    path
                )

                await telegram_utils.send_database_backup(
                    context,
                    html,
                    "tcs.html",
                    (
                        f"💾 BACKUP\n"
                        f"🆔 {test.get('test_id')}\n"
                        f"📚 {test.get('title', '-')}"
                    ),
                )

                success += 1

            except Exception:

                failed += 1

                logger.exception(
                    "Backup failed for %s",
                    test.get(
                        "test_id"
                    ),
                )

            if (
                status
                and (
                    index % 5 == 0
                    or index == len(tests)
                )
            ):

                await telegram_utils.update_progress_message(
                    context,
                    status,
                    (
                        "💾 **BACKUP RUNNING**\n\n"
                        f"📊 {index}/{len(tests)}\n"
                        f"✅ Success: {success}\n"
                        f"❌ Failed: {failed}"
                    ),
                    force=True,
                )

        if status:

            await telegram_utils.update_progress_message(
                context,
                status,
                (
                    "✅ **BACKUP COMPLETE**\n\n"
                    f"📚 Total: {len(tests)}\n"
                    f"✅ Success: {success}\n"
                    f"❌ Failed: {failed}"
                ),
                force=True,
            )

    # ============================================================
    # HELPERS
    # ============================================================

    def back_panel(self):

        return InlineKeyboardButton(
            "⬅️ ADMIN PANEL",
            callback_data="admin:panel",
        )

    async def _ask(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
    ):

        query = update.callback_query

        if query:

            try:

                await query.edit_message_text(
                    text=text,
                    parse_mode="Markdown",
                )

                return

            except Exception:

                pass

        message = update.effective_message

        if message:

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                text,
                parse_mode="Markdown",
            )

    async def _admin_success(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
    ):

        message = update.effective_message

        if message:

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                text,
                parse_mode="Markdown",
            )

    async def _edit_or_send(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        keyboard: InlineKeyboardMarkup,
    ):

        query = update.callback_query

        if query:

            try:

                await query.edit_message_text(
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )

                return

            except Exception:

                pass

        message = update.effective_message

        if message:

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

    @staticmethod
    def to_user_id(
        value: str,
    ) -> Optional[int]:

        try:

            return int(
                value.strip()
            )

        except Exception:

            return None

    @staticmethod
    def to_int(
        value: str,
        default: int = 0,
    ) -> int:

        try:

            return int(
                value
            )

        except Exception:

            return default


# ================================================================
# SINGLE INSTANCE
# ================================================================

admin_handlers = AdminHandlers()

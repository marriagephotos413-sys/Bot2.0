import asyncio
import logging
from typing import Any, Dict, Iterable, List, Optional

from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from telegram.error import (
    BadRequest,
    Forbidden,
    NetworkError,
    RetryAfter,
    TelegramError,
    TimedOut,
)
from telegram.ext import ContextTypes

from .config import CONFIG
from .database import db

logger = logging.getLogger(__name__)


# ================================================================
# TELEGRAM HELPERS
# ================================================================


class TelegramUtilsError(Exception):
    """Telegram utility error."""


class TelegramUtils:
    """
    Telegram-related common utilities.

    इस file में:
        - Safe message sending
        - Safe message editing
        - Channel management
        - Force Join checking
        - Admin checking
        - Progress message
        - User notification
        - Database channel backup
        - Payment channel forwarding
        - User activity channel logging
        - Paid user channel logging
        - Rate-limit handling

    रखा गया है।
    """

    def __init__(self):
        self._progress_cache = {}

    # ============================================================
    # BASIC
    # ============================================================

    @staticmethod
    def is_admin(
        user_id: int,
    ) -> bool:

        return user_id in CONFIG.admin_ids

    # ============================================================
    # SAFE SEND MESSAGE
    # ============================================================

    async def send_message(
        self,
        bot: Bot,
        chat_id: Any,
        text: str,
        **kwargs,
    ) -> Optional[Message]:

        if not chat_id:
            return None

        max_attempts = 5

        for attempt in range(
            max_attempts
        ):

            try:

                return await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    **kwargs,
                )

            except RetryAfter as exc:

                wait_time = (
                    getattr(
                        exc,
                        "retry_after",
                        3,
                    )
                    or 3
                )

                logger.warning(
                    "Telegram rate limit. "
                    "Waiting %s seconds.",
                    wait_time,
                )

                await asyncio.sleep(
                    float(wait_time)
                )

            except (
                TimedOut,
                NetworkError,
            ):

                if attempt == (
                    max_attempts - 1
                ):

                    raise

                await asyncio.sleep(
                    2 ** attempt
                )

            except Forbidden:

                logger.warning(
                    "Bot cannot message chat %s",
                    chat_id,
                )

                return None

            except BadRequest as exc:

                logger.warning(
                    "Telegram BadRequest: %s",
                    exc,
                )

                return None

            except TelegramError:

                if attempt == (
                    max_attempts - 1
                ):

                    raise

                await asyncio.sleep(
                    2 ** attempt
                )

        return None

    # ============================================================
    # SAFE EDIT
    # ============================================================

    async def edit_message(
        self,
        bot: Bot,
        chat_id: Any,
        message_id: int,
        text: str,
        **kwargs,
    ) -> Optional[Message]:

        for attempt in range(5):

            try:

                return await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    **kwargs,
                )

            except RetryAfter as exc:

                wait_time = (
                    getattr(
                        exc,
                        "retry_after",
                        2,
                    )
                    or 2
                )

                await asyncio.sleep(
                    float(wait_time)
                )

            except BadRequest as exc:

                # "Message is not modified"
                # को error नहीं मानेंगे।
                if (
                    "not modified"
                    in str(exc).lower()
                ):

                    return None

                logger.warning(
                    "Edit failed: %s",
                    exc,
                )

                return None

            except (
                TimedOut,
                NetworkError,
            ):

                if attempt == 4:
                    return None

                await asyncio.sleep(
                    2 ** attempt
                )

            except TelegramError:

                return None

        return None

    # ============================================================
    # SAFE DELETE
    # ============================================================

    async def delete_message(
        self,
        bot: Bot,
        chat_id: Any,
        message_id: int,
    ) -> bool:

        try:

            await bot.delete_message(
                chat_id=chat_id,
                message_id=message_id,
            )

            return True

        except (
            TelegramError,
            BadRequest,
            Forbidden,
        ):

            return False

    # ============================================================
    # CALLBACK ANSWER
    # ============================================================

    async def answer_callback(
        self,
        query,
        text: str = "",
        show_alert: bool = False,
    ):

        try:

            await query.answer(
                text=text,
                show_alert=show_alert,
            )

        except TelegramError:

            pass

    # ============================================================
    # ADMIN CHECK
    # ============================================================

    async def require_admin(
        self,
        update: Update,
    ) -> bool:

        user = update.effective_user

        if not user:

            return False

        if self.is_admin(
            user.id
        ):

            return True

        message = (
            update.effective_message
        )

        if message:

            await self.send_message(
                message.get_bot(),
                message.chat_id,
                "🚫 यह command केवल Admin के लिए है।",
            )

        return False

    # ============================================================
    # USER REGISTRATION
    # ============================================================

    def register_user(
        self,
        user,
    ):

        if not user:

            return None

        return db.create_or_update_user(
            user_id=user.id,
            name=user.full_name or "",
            username=user.username or "",
            language=user.language_code or "",
            is_bot=user.is_bot,
        )

    # ============================================================
    # BAN CHECK
    # ============================================================

    def is_banned(
        self,
        user_id: int,
    ) -> bool:

        user = db.get_user(
            user_id
        )

        if not user:

            return False

        return bool(
            user.get(
                "banned",
                False,
            )
        )

    # ============================================================
    # USER ACCESS CHECK
    # ============================================================

    async def check_user_access(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> bool:

        user = update.effective_user

        if not user:

            return False

        # Register/update user
        self.register_user(
            user
        )

        # --------------------------------------------------------
        # Ban
        # --------------------------------------------------------

        if self.is_banned(
            user.id
        ):

            message = (
                update.effective_message
            )

            if message:

                await self.send_message(
                    context.bot,
                    message.chat_id,
                    "🚫 आपका account banned है।",
                )

            return False

        # --------------------------------------------------------
        # Maintenance
        # --------------------------------------------------------

        maintenance = db.get_setting(
            "maintenance_mode",
            False,
        )

        if maintenance and not self.is_admin(
            user.id
        ):

            message = (
                update.effective_message
            )

            if message:

                maintenance_message = db.get_setting(
                    "maintenance_message",
                    (
                        "🛠️ Bot अभी maintenance में है।\n"
                        "कृपया थोड़ी देर बाद कोशिश करें।"
                    ),
                )

                await self.send_message(
                    context.bot,
                    message.chat_id,
                    maintenance_message,
                )

            return False

        # --------------------------------------------------------
        # Force Join
        # --------------------------------------------------------

        if not await self.check_force_join(
            context,
            user.id,
        ):

            message = (
                update.effective_message
            )

            if message:

                keyboard = (
                    await self.force_join_keyboard(
                        context
                    )
                )

                await self.send_message(
                    context.bot,
                    message.chat_id,
                    (
                        "🔒 **Channel Join Required**\n\n"
                        "Bot use करने से पहले "
                        "नीचे दिए गए सभी required channels "
                        "join करें।"
                    ),
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )

            return False

        return True

    # ============================================================
    # FORCE JOIN CHECK
    # ============================================================

    async def check_force_join(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
    ) -> bool:

        enabled = db.get_setting(
            "force_join_enabled",
            False,
        )

        if not enabled:

            return True

        channels = db.get_force_join_channels()

        if not channels:

            return True

        for channel in channels:

            if not channel.get(
                "enabled",
                True,
            ):

                continue

            channel_id = channel.get(
                "channel_id"
            )

            if not channel_id:

                continue

            try:

                member = (
                    await context.bot.get_chat_member(
                        chat_id=channel_id,
                        user_id=user_id,
                    )
                )

                if member.status in (
                    "left",
                    "kicked",
                ):

                    return False

            except TelegramError as exc:

                logger.warning(
                    "Force join check failed "
                    "for %s: %s",
                    channel_id,
                    exc,
                )

                # Security-wise, failed check को
                # access deny माना जाएगा।
                return False

        return True

    # ============================================================
    # FORCE JOIN BUTTONS
    # ============================================================

    async def force_join_keyboard(
        self,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> InlineKeyboardMarkup:

        channels = db.get_force_join_channels()

        rows = []

        for channel in channels:

            if not channel.get(
                "enabled",
                True,
            ):

                continue

            title = (
                channel.get(
                    "title"
                )
                or channel.get(
                    "username"
                )
                or "Join Channel"
            )

            invite_link = channel.get(
                "invite_link"
            )

            if not invite_link:

                try:

                    chat = (
                        await context.bot.get_chat(
                            channel.get(
                                "channel_id"
                            )
                        )
                    )

                    if chat.username:

                        invite_link = (
                            f"https://t.me/"
                            f"{chat.username}"
                        )

                except TelegramError:

                    pass

            if invite_link:

                rows.append(
                    [
                        InlineKeyboardButton(
                            f"📢 {title}",
                            url=invite_link,
                        )
                    ]
                )

        rows.append(
            [
                InlineKeyboardButton(
                    "✅ Check Join",
                    callback_data="check_force_join",
                )
            ]
        )

        return InlineKeyboardMarkup(
            rows
        )

    # ============================================================
    # CHANNEL ID EXTRACTION
    # ============================================================

    async def resolve_channel(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        value: str,
    ) -> Optional[Dict[str, Any]]:

        value = (
            value or ""
        ).strip()

        if not value:

            return None

        try:

            chat = (
                await context.bot.get_chat(
                    value
                )
            )

            invite_link = ""

            if chat.username:

                invite_link = (
                    f"https://t.me/"
                    f"{chat.username}"
                )

            return {
                "channel_id": chat.id,
                "title": chat.title or "",
                "username": (
                    f"@{chat.username}"
                    if chat.username
                    else ""
                ),
                "invite_link": invite_link,
            }

        except TelegramError as exc:

            logger.warning(
                "Unable to resolve channel %s: %s",
                value,
                exc,
            )

            return None

    # ============================================================
    # CHANNEL ADMIN CHECK
    # ============================================================

    async def bot_is_channel_admin(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        channel_id: Any,
    ) -> bool:

        try:

            me = (
                await context.bot.get_me()
            )

            member = (
                await context.bot.get_chat_member(
                    chat_id=channel_id,
                    user_id=me.id,
                )
            )

            return member.status in (
                "administrator",
                "creator",
            )

        except TelegramError:

            return False

    # ============================================================
    # DATABASE CHANNEL
    # ============================================================

    async def send_database_backup(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        file_bytes: bytes,
        filename: str,
        caption: str,
    ) -> Optional[Message]:

        channel = db.get_channel(
            "database"
        )

        if not channel:

            logger.warning(
                "Database channel not configured."
            )

            return None

        channel_id = channel.get(
            "channel_id"
        )

        if not channel_id:

            return None

        from io import BytesIO

        document = BytesIO(
            file_bytes
        )

        document.name = filename

        message = await self.send_document(
            context.bot,
            channel_id,
            document,
            filename,
            caption=caption,
        )

        return message

    # ============================================================
    # SEND DOCUMENT
    # ============================================================

    async def send_document(
        self,
        bot: Bot,
        chat_id: Any,
        document,
        filename: str,
        caption: str = "",
        **kwargs,
    ) -> Optional[Message]:

        for attempt in range(5):

            try:

                return await bot.send_document(
                    chat_id=chat_id,
                    document=document,
                    filename=filename,
                    caption=caption[:1024],
                    **kwargs,
                )

            except RetryAfter as exc:

                wait_time = (
                    getattr(
                        exc,
                        "retry_after",
                        3,
                    )
                    or 3
                )

                await asyncio.sleep(
                    float(wait_time)
                )

            except (
                TimedOut,
                NetworkError,
            ):

                if attempt == 4:

                    raise

                await asyncio.sleep(
                    2 ** attempt
                )

            except TelegramError as exc:

                logger.exception(
                    "send_document failed: %s",
                    exc,
                )

                return None

        return None

    # ============================================================
    # PAYMENT CHANNEL
    # ============================================================

    async def send_payment_for_verification(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        screenshot_message: Message,
        payment_id: str,
        amount: float,
        plan: str,
    ) -> Optional[Message]:

        channel = db.get_channel(
            "payment"
        )

        if not channel:

            return None

        channel_id = channel.get(
            "channel_id"
        )

        if not channel_id:

            return None

        # --------------------------------------------------------
        # Forward original screenshot/message
        # --------------------------------------------------------

        try:

            forwarded = (
                await context.bot.forward_message(
                    chat_id=channel_id,
                    from_chat_id=(
                        screenshot_message.chat_id
                    ),
                    message_id=(
                        screenshot_message.message_id
                    ),
                )
            )

        except TelegramError:

            forwarded = None

        # --------------------------------------------------------
        # Approval buttons
        # --------------------------------------------------------

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ APPROVE",
                        callback_data=(
                            f"payment_approve:{payment_id}"
                        ),
                    ),
                    InlineKeyboardButton(
                        "❌ REJECT",
                        callback_data=(
                            f"payment_reject:{payment_id}"
                        ),
                    ),
                ]
            ]
        )

        info_text = (
            "💳 **PAYMENT VERIFICATION**\n\n"
            f"🆔 Payment: `{payment_id}`\n"
            f"👤 User ID: `{user_id}`\n"
            f"💰 Amount: ₹{amount}\n"
            f"📦 Plan: {plan}\n\n"
            "ऊपर screenshot/payment proof है।\n"
            "नीचे से Approve या Reject करें।"
        )

        message = await self.send_message(
            context.bot,
            channel_id,
            info_text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

        return message

    # ============================================================
    # USER ACTIVITY CHANNEL
    # ============================================================

    async def log_user_activity(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        action: str,
        extra: str = "",
    ):

        channel = db.get_channel(
            "user_activity"
        )

        if not channel:

            return

        channel_id = channel.get(
            "channel_id"
        )

        if not channel_id:

            return

        user = db.get_user(
            user_id
        )

        name = (
            user.get(
                "name",
                "-",
            )
            if user
            else "-"
        )

        username = (
            user.get(
                "username",
                "",
            )
            if user
            else ""
        )

        text = (
            "👤 **USER ACTIVITY**\n\n"
            f"🆔 ID: `{user_id}`\n"
            f"👤 Name: {name}\n"
            f"🔗 Username: "
            f"@{username}\n"
            f"⚡ Action: {action}\n"
        )

        if extra:

            text += (
                f"\n📌 {extra}"
            )

        await self.send_message(
            context.bot,
            channel_id,
            text,
            parse_mode="Markdown",
        )

    # ============================================================
    # PAID USER CHANNEL
    # ============================================================

    async def log_paid_user(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        plan: str,
        amount: float,
        payment_id: str = "",
    ):

        channel = db.get_channel(
            "paid_user"
        )

        if not channel:

            return

        channel_id = channel.get(
            "channel_id"
        )

        if not channel_id:

            return

        user = db.get_user(
            user_id
        )

        name = (
            user.get(
                "name",
                "-",
            )
            if user
            else "-"
        )

        username = (
            user.get(
                "username",
                "",
            )
            if user
            else ""
        )

        expiry = (
            user.get(
                "paid_expiry"
            )
            if user
            else None
        )

        text = (
            "💎 **NEW PAID USER**\n\n"
            f"🆔 User ID: `{user_id}`\n"
            f"👤 Name: {name}\n"
            f"🔗 Username: @{username}\n"
            f"📦 Plan: {plan}\n"
            f"💰 Amount: ₹{amount}\n"
        )

        if payment_id:

            text += (
                f"💳 Payment ID: `{payment_id}`\n"
            )

        if expiry:

            text += (
                f"⏰ Expiry: {expiry}\n"
            )

        await self.send_message(
            context.bot,
            channel_id,
            text,
            parse_mode="Markdown",
        )

    # ============================================================
    # PROGRESS MESSAGE
    # ============================================================

    async def create_progress_message(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: Any,
        text: str = "⏳ Processing...",
    ) -> Optional[Message]:

        return await self.send_message(
            context.bot,
            chat_id,
            text,
        )

    # ============================================================
    # UPDATE PROGRESS
    # ============================================================

    async def update_progress_message(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        message: Message,
        text: str,
        force: bool = False,
    ):

        if not message:

            return

        key = (
            f"{message.chat_id}:"
            f"{message.message_id}"
        )

        # --------------------------------------------------------
        # Telegram flood control से बचने के लिए
        # बहुत जल्दी-जल्दी edit नहीं करेंगे।
        # --------------------------------------------------------

        if not force:

            last = self._progress_cache.get(
                key
            )

            if last == text:

                return

        self._progress_cache[
            key
        ] = text

        await self.edit_message(
            context.bot,
            message.chat_id,
            message.message_id,
            text,
        )

    # ============================================================
    # USER TEST READY
    # ============================================================

    async def send_test_ready(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        title: str,
        url: str,
        question_count: int = 0,
    ):

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🚀 START TEST",
                        url=url,
                    )
                ]
            ]
        )

        text = (
            "✅ **Test Ready!**\n\n"
            f"📚 {title}\n"
            f"❓ Questions: {question_count}\n\n"
            "👇 Test शुरू करें:"
        )

        return await self.send_message(
            context.bot,
            user_id,
            text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    # ============================================================
    # QUEUE MESSAGE
    # ============================================================

    async def send_queue_status(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        position: Optional[int],
        is_paid: bool,
    ):

        if position is None:

            text = (
                "⏳ आपका request process हो रहा है..."
            )

        else:

            priority_text = (
                "💎 Premium Priority"
                if is_paid
                else "🆓 Normal Queue"
            )

            text = (
                "⏳ **Please Wait**\n\n"
                f"{priority_text}\n"
                f"📌 Queue Position: {position}\n\n"
                "आपका Test जल्दी तैयार किया जाएगा।"
            )

        return await self.send_message(
            context.bot,
            user_id,
            text,
            parse_mode="Markdown",
        )

    # ============================================================
    # GENERIC BUTTON
    # ============================================================

    @staticmethod
    def button(
        text: str,
        callback_data: str,
    ) -> InlineKeyboardButton:

        return InlineKeyboardButton(
            text=text,
            callback_data=callback_data,
        )

    @staticmethod
    def url_button(
        text: str,
        url: str,
    ) -> InlineKeyboardButton:

        return InlineKeyboardButton(
            text=text,
            url=url,
        )

    @staticmethod
    def keyboard(
        rows: List[List[InlineKeyboardButton]],
    ) -> InlineKeyboardMarkup:

        return InlineKeyboardMarkup(
            rows
        )


# ================================================================
# SINGLE INSTANCE
# ================================================================

telegram_utils = TelegramUtils()

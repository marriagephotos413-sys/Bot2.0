import logging
from typing import Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes

from .config import CONFIG
from .database import db
from .telegram_utils import telegram_utils

logger = logging.getLogger(__name__)


class PaymentHandlers:
    """
    PAYMENT SYSTEM

    Flow:

        User
          ↓
        Payment
          ↓
        Screenshot
          ↓
        Bot
          ↓
        Payment Verification Channel
          ↓
        ┌───────────────┐
        │               │
      APPROVE         REJECT
        │               │
        ↓               ↓
      Paid ON        Paid OFF
        │
        ↓
    User notification

    Important:
    Payment screenshot को MongoDB में image के रूप में store नहीं किया जाता।
    Telegram message/channel reference और payment metadata store किया जाता है।
    """

    # ============================================================
    # PAYMENT START
    # ============================================================

    async def payment(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        user = update.effective_user

        if not user:

            return

        if await self.is_banned(
            user.id
        ):

            return

        prices = db.get_prices()

        text = (
            "💎 **PREMIUM MEMBERSHIP**\n\n"
            "Premium लेने के बाद आपको:\n\n"
            "⚡ Paid Priority Extraction\n"
            "🚀 Faster Test Processing\n"
            "📚 Premium Test Access\n"
            "📊 Priority Queue\n\n"

            "💰 **PLANS**\n\n"

            f"📅 7 Days — ₹{prices.get('7_days', 0)}\n"
            f"📅 30 Days — ₹{prices.get('30_days', 0)}\n"
            f"📅 90 Days — ₹{prices.get('90_days', 0)}\n"
            f"♾️ Lifetime — ₹{prices.get('lifetime', 0)}\n\n"

            "नीचे अपना plan select करें।"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"📅 7 DAYS • ₹{prices.get('7_days', 0)}",
                        callback_data="payment:plan:7_days",
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"📅 30 DAYS • ₹{prices.get('30_days', 0)}",
                        callback_data="payment:plan:30_days",
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"📅 90 DAYS • ₹{prices.get('90_days', 0)}",
                        callback_data="payment:plan:90_days",
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"♾️ LIFETIME • ₹{prices.get('lifetime', 0)}",
                        callback_data="payment:plan:lifetime",
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

        await self.send_or_edit(
            update,
            context,
            text,
            keyboard,
        )

    # ============================================================
    # SELECT PLAN
    # ============================================================

    async def select_plan(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        plan: str,
    ):

        user = update.effective
        await self.send_or_edit(
            update,
            context,
            text,
            self.back_home_keyboard(),
        )

    # ============================================================
    # RECEIVE PAYMENT SCREENSHOT
    # ============================================================

    async def handle_screenshot(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> bool:

        user = update.effective_user
        message = update.effective_message

        if not user or not message:
            return False

        payment_id = context.user_data.get(
            "payment_screenshot"
        )

        if not payment_id:
            return False

        payment = db.get_payment(
            payment_id
        )

        if not payment:

            context.user_data.pop(
                "payment_screenshot",
                None,
            )

            await message.reply_text(
                "❌ Payment request नहीं मिली।"
            )

            return True

        if payment.get("user_id") != user.id:

            context.user_data.pop(
                "payment_screenshot",
                None,
            )

            return True

        # --------------------------------------------------------
        # Accept photo
        # --------------------------------------------------------

        if message.photo:

            photo = message.photo[-1]

            file_id = photo.file_id

            await self.save_screenshot(
                update,
                context,
                payment,
                file_id,
                "photo",
            )

            context.user_data.pop(
                "payment_screenshot",
                None,
            )

            return True

        # --------------------------------------------------------
        # Accept document image
        # --------------------------------------------------------

        if message.document:

            document = message.document

            mime = (
                document.mime_type
                or ""
            ).lower()

            if mime.startswith(
                "image/"
            ):

                await self.save_screenshot(
                    update,
                    context,
                    payment,
                    document.file_id,
                    "document",
                )

                context.user_data.pop(
                    "payment_screenshot",
                    None,
                )

                return True

        await message.reply_text(
            "❌ कृपया payment का screenshot/photo भेजें।"
        )

        return True

    # ============================================================
    # SAVE + SEND TO VERIFICATION CHANNEL
    # ============================================================

    async def save_screenshot(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        payment: dict,
        file_id: str,
        file_type: str,
    ):

        user = update.effective_user

        if not user:
            return

        payment_id = payment.get(
            "payment_id"
        )

        # --------------------------------------------------------
        # Update DB metadata
        # --------------------------------------------------------

        db.attach_payment_screenshot(
            payment_id=payment_id,
            file_id=file_id,
            file_type=file_type,
        )

        channel_id = db.get_channel_setting(
            "payment_verify_channel"
        )

        if not channel_id:

            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    "⚠️ Payment screenshot receive हो गया है।\n\n"
                    "लेकिन verification channel अभी configured नहीं है।\n"
                    "Admin को inform कर दिया गया है।"
                ),
            )

            logger.error(
                "Payment verification channel not configured."
            )

            return

        # --------------------------------------------------------
        # Verification message
        # --------------------------------------------------------

        username = (
            f"@{user.username}"
            if user.username
            else "No Username"
        )

        name = (
            user.full_name
            or "Unknown"
        )

        caption = (
            "💳 **NEW PAYMENT VERIFICATION**\n\n"

            f"🆔 Payment ID:\n"
            f"`{payment_id}`\n\n"

            f"👤 Name: **{name}**\n"
            f"🔖 Username: {username}\n"
            f"🆔 User ID: `{user.id}`\n\n"

            f"📦 Plan: **{payment.get('plan_name', '-') }**\n"
            f"💰 Amount: **₹{payment.get('amount', 0)}**\n\n"

            "⏳ Status: **PENDING**"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ APPROVE",
                        callback_data=(
                            f"payment:approve:{payment_id}"
                        ),
                    ),
                    InlineKeyboardButton(
                        "❌ REJECT",
                        callback_data=(
                            f"payment:reject:{payment_id}"
                        ),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "👤 USER INFO",
                        callback_data=(
                            f"payment:user:{user.id}"
                        ),
                    ),
                ],
            ]
        )

        try:

            if file_type == "photo":

                sent = await context.bot.send_photo(
                    chat_id=channel_id,
                    photo=file_id,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )

            else:

                sent = await context.bot.send_document(
                    chat_id=channel_id,
                    document=file_id,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )

            # ----------------------------------------------------
            # Save verification message reference
            # ----------------------------------------------------

            db.set_payment_verification_message(
                payment_id=payment_id,
                channel_id=channel_id,
                message_id=sent.message_id,
            )

            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    "✅ **SCREENSHOT RECEIVED**\n\n"
                    f"🆔 Payment ID: `{payment_id}`\n"
                    f"💰 Amount: ₹{payment.get('amount', 0)}\n\n"
                    "⏳ आपका payment verification के लिए भेज दिया गया है।\n"
                    "Approval होने के बाद Premium automatically activate हो जाएगा।"
                ),
                parse_mode="Markdown",
            )

        except Exception as exc:

            logger.exception(
                "Payment verification channel send failed"
            )

            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    "⚠️ Screenshot receive हो गया है, "
                    "लेकिन verification queue में भेजने में समस्या आई।\n\n"
                    "Admin को इसे manually verify करना होगा।"
                ),
            )

    # ============================================================
    # APPROVE PAYMENT
    # ============================================================

    async def approve_payment(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        payment_id: str,
    ):

        query = update.callback_query

        if not await self.is_admin_callback(
            update
        ):

            return

        payment = db.get_payment(
            payment_id
        )

        if not payment:

            await query.answer(
                "Payment नहीं मिली।",
                show_alert=True,
            )

            return

        status = payment.get(
            "status"
        )

        if status == "approved":

            await query.answer(
                "Already approved.",
                show_alert=True,
            )

            return

        if status == "rejected":

            await query.answer(
                "यह payment पहले reject हो चुकी है।",
                show_alert=True,
            )

            return

        # --------------------------------------------------------
        # Atomic approval
        # --------------------------------------------------------

        approved = db.approve_payment(
            payment_id=payment_id,
            admin_id=update.effective_user.id,
        )

        if not approved:

            await query.answer(
                "Payment process नहीं हो सकी।",
                show_alert=True,
            )

            return

        user_id = payment.get(
            "user_id"
        )

        # --------------------------------------------------------
        # Add premium
        # --------------------------------------------------------

        db.add_paid_user(
            user_id=user_id,
            plan=payment.get(
                "plan"
            ),
            payment_id=payment_id,
        )

        # --------------------------------------------------------
        # Update verification message
        # --------------------------------------------------------

        try:

            old_text = (
                query.message.caption
                or query.message.text
                or ""
            )

            new_text = (
                old_text
                + "\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "✅ **PAYMENT APPROVED**\n"
                f"👮 Approved By: `{update.effective_user.id}`"
            )

            await query.edit_message_caption(
                caption=new_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "✅ APPROVED",
                                callback_data="payment:done",
                            )
                        ]
                    ]
                ),
            )

        except Exception:

            logger.debug(
                "Could not update payment verification message",
                exc_info=True,
            )

        # --------------------------------------------------------
        # User notification
        # --------------------------------------------------------

        try:

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 **PAYMENT APPROVED**\n\n"
                    "आपका Premium account successfully activate हो गया है।\n\n"
                    f"📦 Plan: **{payment.get('plan_name', '-') }**\n"
                    f"💰 Paid: **₹{payment.get('amount', 0)}**\n\n"
                    "⚡ अब आपके Test Extract requests को priority मिलेगी।"
                ),
                parse_mode="Markdown",
            )

        except Exception:

            logger.debug(
                "Could not notify approved user",
                exc_info=True,
            )

        # --------------------------------------------------------
        # Paid channel log
        # --------------------------------------------------------

        try:

            await telegram_utils.log_paid_user(
                context,
                user_id,
                action="PAYMENT_APPROVED",
                payment_id=payment_id,
                plan=payment.get(
                    "plan_name"
                ),
                amount=payment.get(
                    "amount"
                ),
            )

        except Exception:

            logger.debug(
                "Paid channel log failed",
                exc_info=True,
            )

        await query.answer(
            "✅ Payment approved और Premium activated.",
            show_alert=True,
        )

    # ============================================================
    # REJECT PAYMENT
    # ============================================================

    async def reject_payment(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        payment_id: str,
    ):

        query = update.callback_query

        if not await self.is_admin_callback(
            update
        ):

            return

        payment = db.get_payment(
            payment_id
        )

        if not payment:

            await query.answer(
                "Payment नहीं मिली।",
                show_alert=True,
            )

            return

        if payment.get(
            "status"
        ) == "approved":

            await query.answer(
                "Approved payment reject नहीं की जा सकती।",
                show_alert=True,
            )

            return

        if payment.get(
            "status"
        ) == "rejected":

            await query.answer(
                "Already rejected.",
                show_alert=True,
            )

            return

        # --------------------------------------------------------
        # Reject
        # --------------------------------------------------------

        rejected = db.reject_payment(
            payment_id=payment_id,
            admin_id=update.effective_user.id,
        )

        if not rejected:

            await query.answer(
                "Payment reject नहीं हो सकी।",
                show_alert=True,
            )

            return

        user_id = payment.get(
            "user_id"
        )

        # --------------------------------------------------------
        # Update channel message
        # --------------------------------------------------------

        try:

            old_text = (
                query.message.caption
                or query.message.text
                or ""
            )

            new_text = (
                old_text
                + "\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "❌ **PAYMENT REJECTED**\n"
                f"👮 Rejected By: `{update.effective_user.id}`"
            )

            await query.edit_message_caption(
                caption=new_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "❌ REJECTED",
                                callback_data="payment:done",
                            )
                        ]
                    ]
                ),
            )

        except Exception:

            logger.debug(
                "Could not update rejected payment message",
                exc_info=True,
            )

        # --------------------------------------------------------
        # Notify user
        # --------------------------------------------------------

        try:

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ **PAYMENT REJECTED**\n\n"
                    f"🆔 Payment ID: `{payment_id}`\n\n"
                    "आपका payment screenshot verify नहीं हो पाया।\n"
                    "कृपया सही payment proof के साथ दोबारा payment request करें।"
                ),
                parse_mode="Markdown",
            )

        except Exception:

            logger.debug(
                "Could not notify rejected user",
                exc_info=True,
            )

        await query.answer(
            "❌ Payment rejected.",
            show_alert=True,
        )

    # ============================================================
    # PAYMENT CALLBACK ROUTER
    # ============================================================

    async def handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        query = update.callback_query

        if not query:

            return

        data = query.data or ""

        # --------------------------------------------------------
        # Plan
        # --------------------------------------------------------

        if data.startswith(
            "payment:plan:"
        ):

            await query.answer()

            plan = data.split(
                ":",
                2,
            )[2]

            return await self.select_plan(
                update,
                context,
                plan,
            )

        # --------------------------------------------------------
        # Screenshot
        # --------------------------------------------------------

        if data.startswith(
            "payment:screenshot:"
        ):

            await query.answer()

            payment_id = data.split(
                ":",
                2,
            )[2]

            return await self.request_screenshot(
                update,
                context,
                payment_id,
            )

        # --------------------------------------------------------
        # Cancel
        # --------------------------------------------------------

        if data.startswith(
            "payment:cancel:"
        ):

            await query.answer()

            payment_id = data.split(
                ":",
                2,
            )[2]

            return await self.cancel_payment(
                update,
                context,
                payment_id,
            )

        # --------------------------------------------------------
        # Approve
        # --------------------------------------------------------

        if data.startswith(
            "payment:approve:"
        ):

            return await self.approve_payment(
                update,
                context,
                data.split(
                    ":",
                    2,
                )[2],
            )

        # --------------------------------------------------------
        # Reject
        # --------------------------------------------------------

        if data.startswith(
            "payment:reject:"
        ):

            return await self.reject_payment(
                update,
                context,
                data.split(
                    ":",
                    2,
                )[2],
            )

        # --------------------------------------------------------
        # User info
        # --------------------------------------------------------

        if data.startswith(
            "payment:user:"
        ):

            if not await self.is_admin_callback(
                update
            ):

                return

            user_id = self.to_int(
                data.split(
                    ":",
                    2,
                )[2],
                0,
            )

            user = db.get_user(
                user_id
            )

            if not user:

                return await query.answer(
                    "User नहीं मिला।",
                    show_alert=True,
                )

            text = (
                "👤 **PAYMENT USER INFO**\n\n"
                f"🆔 User ID: `{user_id}`\n"
                f"👤 Name: {user.get('first_name', '-')}\n"
                f"🔖 Username: @{user.get('username', '-')}\n"
                f"💎 Paid: {user.get('paid', False)}\n"
                f"🚫 Banned: {user.get('banned', False)}\n"
                f"🚀 Extracts: {user.get('extract_count', 0):,}"
            )

            await query.message.reply_text(
                text,
                parse_mode="Markdown",
            )

            await query.answer()

            return

        if data == "payment:done":

            await query.answer(
                "Payment already processed.",
                show_alert=True,
            )

    # ============================================================
    # CANCEL PAYMENT
    # ============================================================

    async def cancel_payment(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        payment_id: str,
    ):

        user = update.effective_user

        if not user:

            return

        payment = db.get_payment(
            payment_id
        )

        if not payment:

            return await self.error(
                update,
                context,
                "❌ Payment नहीं मिली।",
            )

        if payment.get(
            "user_id"
        ) != user.id:

            return await self.error(
                update,
                context,
                "🚫 यह payment आपकी नहीं है।",
            )

        if payment.get(
            "status"
        ) != "pending":

            return await self.error(
                update,
                context,
                "❌ यह payment cancel नहीं की जा सकती।",
            )

        db.cancel_payment(
            payment_id
        )

        context.user_data.pop(
            "payment_screenshot",
            None,
        )

        await self.send_or_edit(
            update,
            context,
            (
                "❌ **PAYMENT CANCELLED**\n\n"
                "आप नई payment request बना सकते हैं।"
            ),
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💎 BUY PREMIUM",
                            callback_data="payment:start",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🏠 HOME",
                            callback_data="home",
                        )
                    ],
                ]
            ),
        )

    # ============================================================
    # PAYMENT HISTORY
    # ============================================================

    async def history(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        user = update.effective_user

        if not user:

            return

        payments = db.get_user_payments(
            user.id,
            limit=10,
        )

        text = (
            "💳 **PAYMENT HISTORY**\n\n"
        )

        if not payments:

            text += (
                "अभी कोई payment record नहीं है।"
            )

        else:

            for payment in payments:

                status = payment.get(
                    "status",
                    "unknown",
                )

                icon = {
                    "approved": "✅",
                    "rejected": "❌",
                    "pending": "⏳",
                    "cancelled": "🚫",
                }.get(
                    status,
                    "ℹ️",
                )

                text += (
                    f"{icon} "
                    f"`{payment.get('payment_id', '-')}`\n"
                    f"📦 {payment.get('plan_name', '-')}\n"
                    f"💰 ₹{payment.get('amount', 0)}\n"
                    f"📌 {status.upper()}\n\n"
                )

        await self.send_or_edit(
            update,
            context,
            text,
            self.back_home_keyboard(),
        )

    # ============================================================
    # ADMIN CHECK
    # ============================================================

    async def is_admin_callback(
        self,
        update: Update,
    ) -> bool:

        user = update.effective_user

        if not user:

            return False

        if user.id not in CONFIG.admin_ids:

            try:

                await update.callback_query.answer(
                    "🚫 Admin Only",
                    show_alert=True,
                )

            except Exception:

                pass

            return False

        return True

    # ============================================================
    # BAN CHECK
    # ============================================================

    async def is_banned(
        self,
        user_id: int,
    ) -> bool:

        try:

            user = db.get_user(
                user_id
            )

            return bool(
                user
                and user.get(
                    "banned",
                    False,
                )
            )

        except Exception:

            return False

    # ============================================================
    # UI HELPERS
    # ============================================================

    async def send_or_edit(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        keyboard: Optional[
            InlineKeyboardMarkup
        ] = None,
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

                logger.debug(
                    "Payment edit failed",
                    exc_info=True,
                )

        message = update.effective_message

        if message:

            await context.bot.send_message(
                chat_id=message.chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

    async def error(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
    ):

        await self.send_or_edit(
            update,
            context,
            text,
            self.back_home_keyboard(),
        )

    @staticmethod
    def back_home_keyboard():

        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💎 PREMIUM",
                        callback_data="payment:start",
                    ),
                    InlineKeyboardButton(
                        "🏠 HOME",
                        callback_data="home",
                    ),
                ]
            ]
        )

    @staticmethod
    def to_int(
        value,
        default=0,
    ) -> int:

        try:

            return int(
                str(value)
            )

        except Exception:

            return default


# =================================================================
# SINGLE INSTANCE
# =================================================================

payment_handlers = PaymentHandlers()

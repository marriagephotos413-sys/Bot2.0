import logging
from datetime import datetime, timezone
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


class UserHandlers:
    """
    User-side commands और menu handlers.

    Main features:

    /start
    /help
    /index
    /price
    /userinfo
    /trial
    /report

    साथ में:

    - Welcome message
    - Free Trial
    - Paid status
    - User info
    - Test Index
    - Payment menu
    - Support / Report
    """

    # ============================================================
    # /START
    # ============================================================

    async def start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        user = update.effective_user

        if not user:
            return

        # --------------------------------------------------------
        # Register user
        # --------------------------------------------------------

        telegram_utils.register_user(
            user
        )

        # --------------------------------------------------------
        # Access
        # --------------------------------------------------------

        if not await telegram_utils.check_user_access(
            update,
            context,
        ):
            return

        # --------------------------------------------------------
        # User activity
        # --------------------------------------------------------

        await telegram_utils.log_user_activity(
            context,
            user.id,
            "BOT_START",
        )

        # --------------------------------------------------------
        # Welcome settings
        # --------------------------------------------------------

        welcome_enabled = db.get_setting(
            "welcome_enabled",
            True,
        )

        welcome_message = db.get_setting(
            "welcome_message",
            (
                "👋 Welcome!\n\n"
                "📚 Test Extract करने के लिए "
                "नीचे button दबाएँ।"
            ),
        )

        if not welcome_enabled:

            welcome_message = (
                "👋 Welcome!\n\n"
                "नीचे दिए गए options में से "
                "अपना option चुनें।"
            )

        # --------------------------------------------------------
        # User status
        # --------------------------------------------------------

        user_data = db.get_user(
            user.id
        ) or {}

        paid = db.is_paid_user(
            user.id
        )

        if paid:

            welcome_message += (
                "\n\n💎 **Premium User**"
            )

        else:

            welcome_message += (
                "\n\n🆓 **Free User**"
            )

        # --------------------------------------------------------
        # Keyboard
        # --------------------------------------------------------

        keyboard = self.main_keyboard(
            paid=paid,
            is_admin=CONFIG.is_admin(user),
        )

        await telegram_utils.send_message(
            context.bot,
            update.effective_chat.id,
            welcome_message,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    # ============================================================
    # MAIN MENU
    # ============================================================

    def main_keyboard(
        self,
        paid: bool = False,
        is_admin: bool = False,
    ) -> InlineKeyboardMarkup:

        rows = [
            [InlineKeyboardButton("📚 TEST INDEX", callback_data="index:categories")],
            [InlineKeyboardButton("🚀 EXTRACT TEST", callback_data="index:categories")],
            [
                InlineKeyboardButton("💎 PREMIUM", callback_data="menu:premium"),
                InlineKeyboardButton("🆓 FREE TRIAL", callback_data="menu:trial"),
            ],
            [
                InlineKeyboardButton("👤 MY ACCOUNT", callback_data="menu:userinfo"),
                InlineKeyboardButton("💰 PRICE", callback_data="menu:price"),
            ],
            [
                InlineKeyboardButton("📢 JOIN CHANNEL", callback_data="menu:channels"),
                InlineKeyboardButton("📞 REPORT", callback_data="menu:report"),
            ],
            [InlineKeyboardButton("📋 COMMAND MENU", callback_data="menu:commands")],
        ]
        # Show the admin entry to everyone so the owner can immediately see it
        # even if Render's ADMIN_IDS is temporarily misconfigured. The callback
        # is still protected by admin_handlers.is_admin(), so normal users
        # cannot enter the panel.
        rows.append([InlineKeyboardButton("🛠️ ADMIN PANEL", callback_data="admin:panel")])
        return InlineKeyboardMarkup(rows)

    # ============================================================
    # /HELP
    # ============================================================

    async def help_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await telegram_utils.check_user_access(
            update,
            context,
        ):
            return

        text = (
            "📖 **BOT HELP**\n\n"

            "📚 **Test Index**\n"
            "Category → Exam → Type → Year → Test\n\n"

            "🚀 **Extract Test**\n"
            "अपना Test चुनकर Extract करें।\n\n"

            "💎 **Premium**\n"
            "Paid users को queue में priority मिलेगी।\n\n"

            "🆓 **Free Trial**\n"
            "अगर Trial available है तो activate कर सकते हैं।\n\n"

            "💳 **Payment**\n"
            "Payment screenshot भेजकर verification करा सकते हैं।\n\n"

            "📞 **Report**\n"
            "किसी Test या Bot problem की report भेजें।"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📚 TEST INDEX",
                        callback_data="index:categories",
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

        await telegram_utils.send_message(
            context.bot,
            update.effective_chat.id,
            text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    # ============================================================
    # PRICE
    # ============================================================

    async def show_price(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await telegram_utils.check_user_access(
            update,
            context,
        ):
            return

        prices = db.get_prices()

        text = (
            "💎 **PREMIUM PLANS**\n\n"
        )

        if not prices:

            text += (
                "अभी कोई Premium Plan configure नहीं है।"
            )

        else:

            for plan, price in prices.items():

                text += (
                    f"📦 **{plan}** — ₹{price}\n"
                )

            text += (
                "\n💳 Payment करने के लिए नीचे "
                "Purchase button दबाएँ।"
            )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💳 PURCHASE",
                        callback_data="menu:premium",
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

        await self._reply_menu(
            update,
            context,
            text,
            keyboard,
        )

    # ============================================================
    # TRIAL
    # ============================================================

    async def show_trial(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        user = update.effective_user

        if not user:
            return

        if not await telegram_utils.check_user_access(
            update,
            context,
        ):
            return

        user_data = db.get_user(
            user.id
        ) or {}

        # --------------------------------------------------------
        # Trial locked
        # --------------------------------------------------------

        if user_data.get(
            "trial_locked",
            False,
        ):

            text = (
                "🔒 **FREE TRIAL LOCKED**\n\n"
                "आपका Free Trial currently locked है।"
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💎 PREMIUM",
                            callback_data="menu:premium",
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

            return await self._reply_menu(
                update,
                context,
                text,
                keyboard,
            )

        # --------------------------------------------------------
        # Already used
        # --------------------------------------------------------

        if user_data.get(
            "trial_used",
            False,
        ):

            text = (
                "🆓 **FREE TRIAL**\n\n"
                "आप Free Trial पहले ही use कर चुके हैं।\n\n"
                "Premium plans देखने के लिए नीचे button दबाएँ।"
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💎 PREMIUM",
                            callback_data="menu:premium",
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

            return await self._reply_menu(
                update,
                context,
                text,
                keyboard,
            )

        # --------------------------------------------------------
        # Trial settings
        # --------------------------------------------------------

        enabled = db.get_setting(
            "trial_enabled",
            True,
        )

        allowed = db.get_setting(
            "trial_allowed",
            True,
        )

        if not enabled or not allowed:

            text = (
                "🆓 **FREE TRIAL**\n\n"
                "अभी Free Trial available नहीं है।"
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💎 PREMIUM",
                            callback_data="menu:premium",
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

            return await self._reply_menu(
                update,
                context,
                text,
                keyboard,
            )

        trial_days = db.get_setting(
            "trial_days",
            1,
        )

        trial_limit = db.get_setting(
            "trial_extract_limit",
            1,
        )

        text = (
            "🆓 **FREE TRIAL AVAILABLE**\n\n"
            f"⏱ Duration: **{trial_days} Day(s)**\n"
            f"📚 Extract Limit: **{trial_limit} Test(s)**\n\n"
            "Trial activate करना चाहते हैं?"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ ACTIVATE TRIAL",
                        callback_data="trial:activate",
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

        await self._reply_menu(
            update,
            context,
            text,
            keyboard,
        )

    # ============================================================
    # ACTIVATE TRIAL
    # ============================================================

    async def activate_trial(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        query = update.callback_query

        user = update.effective_user

        if not user:
            return

        await telegram_utils.answer_callback(
            query
        )

        if not await telegram_utils.check_user_access(
            update,
            context,
        ):
            return

        # --------------------------------------------------------
        # Atomic activation database function
        # --------------------------------------------------------

        result = db.activate_trial(
            user.id
        )

        if not result.get(
            "success",
            False,
        ):

            reason = result.get(
                "reason",
                "Trial activate नहीं हुआ।",
            )

            return await telegram_utils.edit_message(
                context.bot,
                query.message.chat_id,
                query.message.message_id,
                f"❌ {reason}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "💎 PREMIUM",
                                callback_data="menu:premium",
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

        trial_expiry = result.get(
            "trial_expiry"
        )

        text = (
            "🎉 **FREE TRIAL ACTIVATED!**\n\n"
            f"⏱ Duration: {result.get('trial_days', 1)} Day(s)\n"
            f"📚 Extract Limit: {result.get('trial_limit', 1)}\n"
        )

        if trial_expiry:

            text += (
                f"⏰ Expiry: {trial_expiry}\n"
            )

        text += (
            "\nअब Test Index से Test Extract कर सकते हैं।"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📚 TEST INDEX",
                        callback_data="index:categories",
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

        await telegram_utils.edit_message(
            context.bot,
            query.message.chat_id,
            query.message.message_id,
            text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

        await telegram_utils.log_user_activity(
            context,
            user.id,
            "TRIAL_ACTIVATED",
        )

    # ============================================================
    # USER INFO
    # ============================================================

    async def user_info(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        user = update.effective_user

        if not user:
            return

        if not await telegram_utils.check_user_access(
            update,
            context,
        ):
            return

        data = db.get_user(
            user.id
        ) or {}

        paid = db.is_paid_user(
            user.id
        )

        status = (
            "💎 PAID"
            if paid
            else "🆓 FREE"
        )

        text = (
            "👤 **MY ACCOUNT**\n\n"

            f"🆔 User ID: `{user.id}`\n"
            f"👤 Name: {data.get('name', user.full_name)}\n"
            f"🔗 Username: "
            f"@{data.get('username', user.username or '-')}\n\n"

            f"📊 Status: **{status}**\n"
            f"📚 Total Extract: "
            f"**{data.get('extract_count', 0)}**\n"
            f"✅ Successful: "
            f"**{data.get('successful_extracts', 0)}**\n"
            f"❌ Failed: "
            f"**{data.get('failed_extracts', 0)}**\n"
        )

        if paid:

            text += (
                f"\n📦 Plan: "
                f"**{data.get('paid_plan', '-')}**\n"
                f"⏰ Expiry: "
                f"**{data.get('paid_expiry', '-')}**\n"
            )

        else:

            text += (
                f"\n🆓 Trial Used: "
                f"**{'Yes' if data.get('trial_used') else 'No'}**\n"
            )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📚 TEST INDEX",
                        callback_data="index:categories",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "💎 PREMIUM",
                        callback_data="menu:premium",
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

        await self._reply_menu(
            update,
            context,
            text,
            keyboard,
        )

    # ============================================================
    # PREMIUM
    # ============================================================

    async def premium_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await telegram_utils.check_user_access(
            update,
            context,
        ):
            return

        prices = db.get_prices()

        rows = []

        for plan, price in prices.items():

            rows.append(
                [
                    InlineKeyboardButton(
                        f"💎 {plan} — ₹{price}",
                        callback_data=(
                            f"purchase:{self._safe_callback(plan)}"
                        ),
                    )
                ]
            )

        rows.append(
            [
                InlineKeyboardButton(
                    "💰 PRICE",
                    callback_data="menu:price",
                )
            ]
        )

        rows.append(
            [
                InlineKeyboardButton(
                    "🏠 HOME",
                    callback_data="home",
                )
            ]
        )

        text = (
            "💎 **PREMIUM MEMBERSHIP**\n\n"
            "Premium users को Test Extract queue में "
            "**priority processing** मिलेगी।\n\n"
            "अपना plan चुनें:"
        )

        await self._reply_menu(
            update,
            context,
            text,
            InlineKeyboardMarkup(rows),
        )

    # ============================================================
    # PURCHASE
    # ============================================================

    async def purchase(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        plan: str,
    ):

        user = update.effective_user

        if not user:
            return

        prices = db.get_prices()

        amount = prices.get(
            plan
        )

        if amount is None:

            text = (
                "❌ यह Premium Plan available नहीं है।"
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💎 PREMIUM",
                            callback_data="menu:premium",
                        )
                    ]
                ]
            )

            return await self._reply_menu(
                update,
                context,
                text,
                keyboard,
            )

        payment_id = db.create_payment(
            user_id=user.id,
            amount=float(amount),
            plan=plan,
        )

        # --------------------------------------------------------
        # Payment instructions
        # --------------------------------------------------------

        payment_text = db.get_setting(
            "payment_message",
            (
                "💳 Payment instructions "
                "Admin द्वारा configure नहीं की गई हैं।"
            ),
        )

        text = (
            "💳 **PAYMENT**\n\n"
            f"📦 Plan: **{plan}**\n"
            f"💰 Amount: **₹{amount}**\n"
            f"🆔 Payment ID: `{payment_id}`\n\n"
            f"{payment_text}\n\n"
            "Payment करने के बाद अपना screenshot "
            "यहाँ भेजें।"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCEL",
                        callback_data="home",
                    )
                ]
            ]
        )

        await self._reply_menu(
            update,
            context,
            text,
            keyboard,
        )

        # Conversation state
        context.user_data[
            "payment_id"
        ] = payment_id

        context.user_data[
            "payment_plan"
        ] = plan

    # ============================================================
    # PAYMENT SCREENSHOT
    # ============================================================

    async def handle_payment_screenshot(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        user = update.effective_user

        message = update.effective_message

        if not user or not message:
            return

        payment_id = context.user_data.get(
            "payment_id"
        )

        if not payment_id:

            return

        payment = db.get_payment(
            payment_id
        )

        if not payment:

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                (
                    "❌ Payment session expire हो गया।\n"
                    "कृपया नया plan select करें।"
                ),
            )

            context.user_data.pop(
                "payment_id",
                None,
            )

            return

        # --------------------------------------------------------
        # Send screenshot to payment channel
        # --------------------------------------------------------

        screenshot_message = await telegram_utils.send_payment_for_verification(
            context,
            user.id,
            message,
            payment_id,
            float(
                payment.get(
                    "amount",
                    0,
                )
            ),
            payment.get(
                "plan",
                "",
            ),
        )

        if screenshot_message:

            db.update_payment(
                payment_id,
                status="submitted",
                verification_message_id=(
                    screenshot_message.message_id
                ),
            )

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                (
                    "✅ **Payment Screenshot Received**\n\n"
                    f"🆔 Payment ID: `{payment_id}`\n\n"
                    "Admin verification के बाद "
                    "आपका Premium activate किया जाएगा।"
                ),
                parse_mode="Markdown",
            )

        else:

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                (
                    "❌ Payment verification channel "
                    "configure नहीं है।\n"
                    "कृपया Admin से contact करें।"
                ),
            )

        context.user_data.pop(
            "payment_id",
            None,
        )

    # ============================================================
    # CHANNELS
    # ============================================================

    async def show_channels(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        channels = db.get_force_join_channels()

        rows = []

        for channel in channels:

            if not channel.get(
                "enabled",
                True,
            ):

                continue

            link = channel.get(
                "invite_link"
            )

            if link:

                rows.append(
                    [
                        InlineKeyboardButton(
                            (
                                "📢 "
                                + channel.get(
                                    "title",
                                    "Join Channel",
                                )
                            ),
                            url=link,
                        )
                    ]
                )

        rows.append(
            [
                InlineKeyboardButton(
                    "🏠 HOME",
                    callback_data="home",
                )
            ]
        )

        text = (
            "📢 **OUR CHANNELS**\n\n"
            "Latest Tests और Updates के लिए "
            "हमारे channels join करें।"
        )

        await self._reply_menu(
            update,
            context,
            text,
            InlineKeyboardMarkup(rows),
        )

    # ============================================================
    # REPORT
    # ============================================================

    async def report_menu(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        user = update.effective_user

        if not user:
            return

        text = (
            "📞 **REPORT / SUPPORT**\n\n"
            "अपनी समस्या नीचे लिखकर भेजें।\n\n"
            "उदाहरण:\n"
            "• Test open नहीं हो रहा\n"
            "• Wrong question\n"
            "• Wrong answer\n"
            "• Payment problem\n"
            "• कोई और issue"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCEL",
                        callback_data="home",
                    )
                ]
            ]
        )

        await self._reply_menu(
            update,
            context,
            text,
            keyboard,
        )

        context.user_data[
            "awaiting_report"
        ] = True

    # ============================================================
    # RECEIVE REPORT
    # ============================================================

    async def receive_report(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        user = update.effective_user

        message = update.effective_message

        if not user or not message:
            return False

        if not context.user_data.get(
            "awaiting_report",
            False,
        ):

            return False

        report_text = (
            message.text
            or message.caption
            or ""
        )

        if not report_text.strip():

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                "❌ कृपया अपनी समस्या text में लिखें।",
            )

            return True

        report_id = db.create_report(
            user_id=user.id,
            text=report_text,
        )

        # --------------------------------------------------------
        # Admin report channel
        # --------------------------------------------------------

        report_channel = db.get_channel(
            "report"
        )

        if report_channel:

            channel_id = report_channel.get(
                "channel_id"
            )

            if channel_id:

                report_message = (
                    "🚨 **NEW USER REPORT**\n\n"
                    f"🆔 Report: `{report_id}`\n"
                    f"👤 User: `{user.id}`\n"
                    f"👤 Name: {user.full_name}\n\n"
                    f"📝 Report:\n{report_text}"
                )

                await telegram_utils.send_message(
                    context.bot,
                    channel_id,
                    report_message,
                    parse_mode="Markdown",
                )

        await telegram_utils.send_message(
            context.bot,
            message.chat_id,
            (
                "✅ **Report Submitted**\n\n"
                f"🆔 Report ID: `{report_id}`\n"
                "Admin इसे check करेगा।"
            ),
            parse_mode="Markdown",
        )

        context.user_data.pop(
            "awaiting_report",
            None,
        )

        return True

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

        data = query.data or ""

        await telegram_utils.answer_callback(
            query
        )

        # --------------------------------------------------------
        # Home
        # --------------------------------------------------------

        if data == "home":

            user = update.effective_user

            paid = (
                db.is_paid_user(
                    user.id
                )
                if user
                else False
            )

            text = (
                "🏠 **MAIN MENU**\n\n"
                "नीचे अपना option चुनें:"
            )

            return await telegram_utils.edit_message(
                context.bot,
                query.message.chat_id,
                query.message.message_id,
                text,
                parse_mode="Markdown",
                reply_markup=self.main_keyboard(
                    paid
                ),
            )

        # --------------------------------------------------------
        # Command menu
        # --------------------------------------------------------

        if data == "menu:commands":
            user = update.effective_user
            is_admin = bool(user and CONFIG.is_admin(user))
            paid = bool(user and db.is_paid_user(user.id))
            text = (
                "📋 **COMMAND MENU**\n\n"
                "👤 /start — Main Menu\n"
                "/menu — Main Menu\n"
                "/help — Help\n"
                "/index — Test Index\n"
                "/extract — Extract Test\n"
                "/price — Premium Plans\n"
                "/trial — Free Trial\n"
                "/userinfo — My Account\n"
                "/report — Report\n"
                "/commands — Command Menu"
            )
            if is_admin:
                text += "\n\n🛠️ **ADMIN**\n/admin — Admin Panel\n/stats — Statistics\n/upload — Upload Test\n/seed — Demo Test"
            return await telegram_utils.edit_message(
                context.bot, query.message.chat_id, query.message.message_id,
                text, parse_mode="Markdown",
                reply_markup=self.main_keyboard(paid=paid, is_admin=is_admin),
            )

        # --------------------------------------------------------
        # Trial
        # --------------------------------------------------------

        if data == "menu:trial":

            return await self.show_trial(
                update,
                context,
            )

        if data == "trial:activate":

            return await self.activate_trial(
                update,
                context,
            )

        # --------------------------------------------------------
        # User info
        # --------------------------------------------------------

        if data == "menu:userinfo":

            return await self.user_info(
                update,
                context,
            )

        # --------------------------------------------------------
        # Price
        # --------------------------------------------------------

        if data == "menu:price":

            return await self.show_price(
                update,
                context,
            )

        # --------------------------------------------------------
        # Premium / legacy purchase menu
        # --------------------------------------------------------

        if data in ("menu:premium", "menu:purchase"):

            return await self.premium_menu(
                update,
                context,
            )

        # --------------------------------------------------------
        # Purchase
        # --------------------------------------------------------

        if data.startswith(
            "purchase:"
        ):

            plan = data[
                len("purchase:"):
            ]

            return await self.purchase(
                update,
                context,
                plan,
            )

        # --------------------------------------------------------
        # Channels
        # --------------------------------------------------------

        if data == "menu:channels":

            return await self.show_channels(
                update,
                context,
            )

        # --------------------------------------------------------
        # Report
        # --------------------------------------------------------

        if data == "menu:report":

            return await self.report_menu(
                update,
                context,
            )

    # ============================================================
    # MESSAGE ROUTER
    # ============================================================

    async def handle_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> bool:

        # --------------------------------------------------------
        # Report
        # --------------------------------------------------------

        if context.user_data.get(
            "awaiting_report",
            False,
        ):

            return await self.receive_report(
                update,
                context,
            )

        # --------------------------------------------------------
        # Payment screenshot
        # --------------------------------------------------------

        payment_id = context.user_data.get(
            "payment_id"
        )

        if payment_id:

            message = update.effective_message

            if message:

                if (
                    message.photo
                    or message.document
                ):

                    await self.handle_payment_screenshot(
                        update,
                        context,
                    )

                    return True

        return False

    # ============================================================
    # HELPERS
    # ============================================================

    async def _reply_menu(
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
    def _safe_callback(
        value: str,
    ) -> str:

        value = str(
            value or ""
        )

        # Telegram callback_data byte limit
        value = (
            value
            .replace(
                ":",
                "_",
            )
            .replace(
                "|",
                "_",
            )
        )

        return value[:40]


# ================================================================
# SINGLE INSTANCE
# ================================================================

user_handlers = UserHandlers()

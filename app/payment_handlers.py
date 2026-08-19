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

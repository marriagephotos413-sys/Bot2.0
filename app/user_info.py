import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.helpers import (
    display_name,
    format_datetime,
    username_or_id,
)
from app.keyboards import user_info_keyboard
from app.user_management import user_manager


logger = logging.getLogger(
    "telegram-test-series-bot.user-info"
)


# ============================================================
# USER INFO SERVICE
# ============================================================

class UserInfoService:
    """
    User की complete information तैयार करने वाला service.

    इसमें:
    - Basic Telegram information
    - Paid status
    - Trial status
    - Ban status
    - Activity
    - Extraction statistics
    - Registration / last seen
    शामिल हो सकते हैं।
    """

    # ========================================================
    # GET USER
    # ========================================================

    async def get_user(
        self,
        user_id: int,
    ) -> Optional[Dict[str, Any]]:

        return await user_manager.get_user(
            int(user_id)
        )

    # ========================================================
    # BUILD INFO
    # ========================================================

    async def build_info(
        self,
        user_id: int,
    ) -> Optional[Dict[str, Any]]:

        user = await self.get_user(
            user_id
        )

        if not user:
            return None

        return self._normalize_user(
            user
        )

    # ========================================================
    # NORMALIZE
    # ========================================================

    def _normalize_user(
        self,
        user: Dict[str, Any],
    ) -> Dict[str, Any]:

        user_id = user.get(
            "user_id",
            user.get(
                "id",
                0,
            ),
        )

        is_paid = bool(
            user.get(
                "is_paid",
                user.get(
                    "paid",
                    False,
                ),
            )
        )

        is_banned = bool(
            user.get(
                "is_banned",
                user.get(
                    "banned",
                    False,
                ),
            )
        )

        trial_active = bool(
            user.get(
                "trial_active",
                False,
            )
        )

        return {
            "user_id": user_id,

            "username": user.get(
                "username"
            ),

            "first_name": user.get(
                "first_name"
            ),

            "last_name": user.get(
                "last_name"
            ),

            "language_code": user.get(
                "language_code"
            ),

            "is_bot": bool(
                user.get(
                    "is_bot",
                    False,
                )
            ),

            "is_paid": is_paid,

            "paid_plan": user.get(
                "paid_plan"
            ),

            "paid_at": user.get(
                "paid_at"
            ),

            "paid_expires_at": user.get(
                "paid_expires_at"
            ),

            "is_banned": is_banned,

            "ban_reason": user.get(
                "ban_reason"
            ),

            "banned_at": user.get(
                "banned_at"
            ),

            "trial_used": bool(
                user.get(
                    "trial_used",
                    False,
                )
            ),

            "trial_active": trial_active,

            "trial_started_at": user.get(
                "trial_started_at"
            ),

            "trial_expires_at": user.get(
                "trial_expires_at"
            ),

            "registered_at": user.get(
                "registered_at",
                user.get(
                    "created_at"
                ),
            ),

            "last_seen": user.get(
                "last_seen"
            ),

            "total_extractions": int(
                user.get(
                    "total_extractions",
                    0,
                )
                or 0
            ),

            "successful_extractions": int(
                user.get(
                    "successful_extractions",
                    0,
                )
                or 0
            ),

            "failed_extractions": int(
                user.get(
                    "failed_extractions",
                    0,
                )
                or 0
            ),

            "total_tests": int(
                user.get(
                    "total_tests",
                    0,
                )
                or 0
            ),

            "metadata": user.get(
                "metadata",
                {},
            ),
        }

    # ========================================================
    # DISPLAY TEXT
    # ========================================================

    async def format_info(
        self,
        user_id: int,
    ) -> str:

        info = await self.build_info(
            user_id
        )

        if not info:

            return (
                "❌ User नहीं मिला।"
            )

        user_id = info[
            "user_id"
        ]

        username = info.get(
            "username"
        )

        name = (
            f"{info.get('first_name') or ''} "
            f"{info.get('last_name') or ''}"
        ).strip()

        if not name:
            name = "Not Available"

        username_text = (
            f"@{username}"
            if username
            else "Not Available"
        )

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        paid_status = (
            "🟢 PAID"
            if info["is_paid"]
            else "🔴 FREE"
        )

        ban_status = (
            "🚫 BANNED"
            if info["is_banned"]
            else "🟢 ACTIVE"
        )

        trial_status = (
            "🟢 ACTIVE"
            if info["trial_active"]
            else "⚪ INACTIVE"
        )

        # ----------------------------------------------------
        # Dates
        # ----------------------------------------------------

        registered_at = format_datetime(
            info.get(
                "registered_at"
            )
        )

        last_seen = format_datetime(
            info.get(
                "last_seen"
            )
        )

        paid_expires = format_datetime(
            info.get(
                "paid_expires_at"
            )
        )

        trial_expires = format_datetime(
            info.get(
                "trial_expires_at"
            )
        )

        # ----------------------------------------------------
        # Stats
        # ----------------------------------------------------

        total_extractions = info[
            "total_extractions"
        ]

        successful = info[
            "successful_extractions"
        ]

        failed = info[
            "failed_extractions"
        ]

        total_tests = info[
            "total_tests"
        ]

        return (
            "👤 <b>USER INFORMATION</b>\n"
            "\n"
            f"🆔 <b>ID:</b> "
            f"<code>{user_id}</code>\n"
            f"👤 <b>Name:</b> "
            f"{name}\n"
            f"🔗 <b>Username:</b> "
            f"{username_text}\n"
            f"🌐 <b>Language:</b> "
            f"{info.get('language_code') or 'N/A'}\n"
            "\n"
            f"💎 <b>Plan:</b> "
            f"{paid_status}\n"
            f"📦 <b>Paid Plan:</b> "
            f"{info.get('paid_plan') or 'N/A'}\n"
            f"📅 <b>Paid Expiry:</b> "
            f"{paid_expires}\n"
            "\n"
            f"🎁 <b>Trial:</b> "
            f"{trial_status}\n"
            f"📅 <b>Trial Expiry:</b> "
            f"{trial_expires}\n"
            "\n"
            f"🛡 <b>Account:</b> "
            f"{ban_status}\n"
            f"📝 <b>Ban Reason:</b> "
            f"{info.get('ban_reason') or 'N/A'}\n"
            "\n"
            "📊 <b>STATISTICS</b>\n"
            f"📚 Total Tests: "
            f"<b>{total_tests}</b>\n"
            f"🚀 Total Extract: "
            f"<b>{total_extractions}</b>\n"
            f"✅ Successful: "
            f"<b>{successful}</b>\n"
            f"❌ Failed: "
            f"<b>{failed}</b>\n"
            "\n"
            "🕐 <b>ACCOUNT</b>\n"
            f"📅 Registered: "
            f"{registered_at}\n"
            f"👀 Last Seen: "
            f"{last_seen}"
        )

    # ========================================================
    # ADMIN INFO
    # ========================================================

    async def format_admin_info(
        self,
        user_id: int,
    ) -> str:

        info = await self.build_info(
            user_id
        )

        if not info:

            return (
                "❌ User नहीं मिला।"
            )

        base = await self.format_info(
            user_id
        )

        metadata = info.get(
            "metadata",
            {},
        )

        if not isinstance(
            metadata,
            dict,
        ):

            metadata = {}

        extra_lines = []

        for key in (
            "source",
            "referral",
            "last_command",
            "last_test_id",
            "last_exam",
        ):

            value = metadata.get(
                key
            )

            if value not in (
                None,
                "",
            ):

                extra_lines.append(
                    f"🔹 <b>{key}:</b> "
                    f"{value}"
                )

        if extra_lines:

            base += (
                "\n\n"
                "⚙️ <b>EXTRA DATA</b>\n"
                + "\n".join(
                    extra_lines
                )
            )

        return base

    # ========================================================
    # KEYBOARD
    # ========================================================

    def keyboard(
        self,
        user_id: int,
    ):

        return user_info_keyboard(
            int(user_id)
        )


# ============================================================
# GLOBAL SERVICE
# ============================================================

user_info_service = UserInfoService()


# ============================================================
# TELEGRAM HANDLER
# ============================================================

async def show_user_info(
    update,
    context,
    user_id: Optional[int] = None,
    admin: bool = False,
):

    try:

        if user_id is None:

            user = update.effective_user

            if not user:

                return

            user_id = user.id

        user_id = int(
            user_id
        )

        if admin:

            text = await (
                user_info_service
                .format_admin_info(
                    user_id
                )
            )

        else:

            text = await (
                user_info_service
                .format_info(
                    user_id
                )
            )

        keyboard = (
            user_info_service
            .keyboard(
                user_id
            )
            if admin
            else None
        )

        # ----------------------------------------------------
        # Callback
        # ----------------------------------------------------

        if update.callback_query:

            query = (
                update.callback_query
            )

            try:

                await query.answer()

            except Exception:

                pass

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

            return

        # ----------------------------------------------------
        # Normal message
        # ----------------------------------------------------

        if update.effective_message:

            await update.effective_message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

    except Exception:

        logger.exception(
            "Failed to show user info."
        )

        try:

            if update.effective_message:

                await update.effective_message.reply_text(
                    "❌ User information load नहीं हो सकी।"
                )

        except Exception:

            logger.debug(
                "Could not send user-info error.",
                exc_info=True,
            )


# ============================================================
# QUICK HELPERS
# ============================================================

async def get_user_info(
    user_id: int,
):

    return await user_info_service.build_info(
        int(user_id)
    )


async def get_user_info_text(
    user_id: int,
):

    return await user_info_service.format_info(
        int(user_id)
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "UserInfoService",
    "user_info_service",
    "show_user_info",
    "get_user_info",
    "get_user_info_text",
]

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.helpers import (
    format_datetime,
    safe_int,
)
from app.keyboards import (
    paid_user_keyboard,
)
from app.user_management import (
    user_manager,
)


logger = logging.getLogger(
    "telegram-test-series-bot.paid-users"
)


# ============================================================
# PAID USER SERVICE
# ============================================================

class PaidUserService:
    """
    Paid-user management.

    Features:
    - Add paid user
    - Remove paid user
    - Check paid status
    - Paid user list
    - Expiry handling
    - Paid statistics
    """

    # ========================================================
    # ADD PAID
    # ========================================================

    async def add(
        self,
        user_id: int,
        plan: str = "premium",
        days: Optional[int] = None,
        payment_id: Optional[str] = None,
        admin_id: Optional[int] = None,
    ) -> bool:

        try:

            return await user_manager.add_paid_user(
                user_id=int(user_id),
                plan=plan,
                days=days,
                payment_id=payment_id,
                admin_id=admin_id,
            )

        except Exception:

            logger.exception(
                "Failed to add paid user %s.",
                user_id,
            )

            return False

    # ========================================================
    # REMOVE PAID
    # ========================================================

    async def remove(
        self,
        user_id: int,
        admin_id: Optional[int] = None,
    ) -> bool:

        try:

            return await user_manager.remove_paid_user(
                user_id=int(user_id),
                admin_id=admin_id,
            )

        except Exception:

            logger.exception(
                "Failed to remove paid user %s.",
                user_id,
            )

            return False

    # ========================================================
    # CHECK
    # ========================================================

    async def is_paid(
        self,
        user_id: int,
    ) -> bool:

        try:

            return await user_manager.is_paid(
                int(user_id)
            )

        except Exception:

            logger.exception(
                "Paid check failed."
            )

            return False

    # ========================================================
    # GET PAID USER
    # ========================================================

    async def get(
        self,
        user_id: int,
    ) -> Optional[Dict[str, Any]]:

        try:

            user = await user_manager.get_user(
                int(user_id)
            )

            if not user:
                return None

            if not bool(
                user.get(
                    "is_paid",
                    user.get(
                        "paid",
                        False,
                    ),
                )
            ):

                return None

            return user

        except Exception:

            logger.exception(
                "Failed to get paid user."
            )

            return None

    # ========================================================
    # FORMAT USER
    # ========================================================

    async def format_user(
        self,
        user_id: int,
    ) -> str:

        user = await self.get(
            user_id
        )

        if not user:

            return (
                "❌ यह user paid list में नहीं है।"
            )

        name = (
            f"{user.get('first_name') or ''} "
            f"{user.get('last_name') or ''}"
        ).strip()

        if not name:
            name = "N/A"

        username = user.get(
            "username"
        )

        username_text = (
            f"@{username}"
            if username
            else "N/A"
        )

        plan = user.get(
            "paid_plan",
            "premium",
        )

        paid_at = format_datetime(
            user.get(
                "paid_at"
            )
        )

        expires_at = format_datetime(
            user.get(
                "paid_expires_at"
            )
        )

        return (
            "💎 <b>PAID USER</b>\n"
            "\n"
            f"🆔 <b>User ID:</b> "
            f"<code>{int(user_id)}</code>\n"
            f"👤 <b>Name:</b> "
            f"{name}\n"
            f"🔗 <b>Username:</b> "
            f"{username_text}\n"
            "\n"
            f"💎 <b>Plan:</b> "
            f"{plan}\n"
            f"📅 <b>Paid At:</b> "
            f"{paid_at}\n"
            f"⏳ <b>Expiry:</b> "
            f"{expires_at}"
        )

    # ========================================================
    # LIST
    # ========================================================

    async def list(
        self,
        limit: int = 100,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:

        try:

            users = await user_manager.list_users(
                limit=safe_int(
                    limit,
                    100,
                ),
                skip=safe_int(
                    skip,
                    0,
                ),
                paid_only=True,
            )

            return list(
                users or []
            )

        except Exception:

            logger.exception(
                "Failed to list paid users."
            )

            return []

    # ========================================================
    # COUNT
    # ========================================================

    async def count(
        self,
    ) -> int:

        try:

            return await user_manager.count_paid_users()

        except Exception:

            logger.exception(
                "Failed to count paid users."
            )

            return 0

    # ========================================================
    # STATISTICS
    # ========================================================

    async def statistics(
        self,
    ) -> Dict[str, Any]:

        users = await self.list(
            limit=1000
        )

        now = datetime.now(
            timezone.utc
        )

        active = 0
        expired = 0
        lifetime = 0

        for user in users:

            expires_at = user.get(
                "paid_expires_at"
            )

            if not expires_at:

                lifetime += 1

                continue

            if isinstance(
                expires_at,
                str,
            ):

                try:

                    expires_at = (
                        datetime.fromisoformat(
                            expires_at
                        )
                    )

                except ValueError:

                    lifetime += 1
                    continue

            if expires_at.tzinfo is None:

                expires_at = (
                    expires_at.replace(
                        tzinfo=timezone.utc
                    )
                )

            if expires_at > now:

                active += 1

            else:

                expired += 1

        return {
            "total": len(users),
            "active": active,
            "expired": expired,
            "lifetime": lifetime,
        }

    # ========================================================
    # SEND USER INFO
    # ========================================================

    async def send_user(
        self,
        update,
        user_id: int,
    ):

        try:

            text = await self.format_user(
                user_id
            )

            keyboard = paid_user_keyboard(
                int(user_id)
            )

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

            if update.effective_message:

                await update.effective_message.reply_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )

        except Exception:

            logger.exception(
                "Failed to send paid user information."
            )

    # ========================================================
    # FORMAT LIST
    # ========================================================

    async def format_list(
        self,
        limit: int = 50,
        skip: int = 0,
    ) -> str:

        users = await self.list(
            limit=limit,
            skip=skip,
        )

        if not users:

            return (
                "💎 <b>PAID USERS</b>\n\n"
                "कोई paid user नहीं मिला।"
            )

        lines = [
            "💎 <b>PAID USERS</b>",
            "",
        ]

        for index, user in enumerate(
            users,
            start=skip + 1,
        ):

            user_id = user.get(
                "user_id",
                user.get(
                    "id",
                    "-",
                ),
            )

            username = user.get(
                "username"
            )

            name = (
                f"{user.get('first_name') or ''} "
                f"{user.get('last_name') or ''}"
            ).strip()

            if not name:
                name = "N/A"

            username_text = (
                f"@{username}"
                if username
                else "N/A"
            )

            plan = user.get(
                "paid_plan",
                "premium",
            )

            lines.append(
                (
                    f"<b>{index}.</b> "
                    f"👤 {name}\n"
                    f"🆔 <code>{user_id}</code>\n"
                    f"🔗 {username_text}\n"
                    f"💎 {plan}"
                )
            )

        lines.append("")
        lines.append(
            f"📊 Showing: <b>{len(users)}</b>"
        )

        return "\n".join(
            lines
        )

    # ========================================================
    # PAID FIRST
    # ========================================================

    async def priority_for_user(
        self,
        user_id: int,
    ) -> int:

        """
        Extraction queue में paid user को highest priority.

        Lower number = higher priority.
        """

        try:

            paid = await self.is_paid(
                user_id
            )

            if paid:

                return 1

            trial = await user_manager.trial_active(
                user_id
            )

            if trial:

                return 5

            return 10

        except Exception:

            logger.exception(
                "Could not calculate user priority."
            )

            return 10


# ============================================================
# GLOBAL SERVICE
# ============================================================

paid_user_service = PaidUserService()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def add_paid_user(
    user_id: int,
    plan: str = "premium",
    days: Optional[int] = None,
    payment_id: Optional[str] = None,
    admin_id: Optional[int] = None,
):

    return await paid_user_service.add(
        user_id=user_id,
        plan=plan,
        days=days,
        payment_id=payment_id,
        admin_id=admin_id,
    )


async def remove_paid_user(
    user_id: int,
    admin_id: Optional[int] = None,
):

    return await paid_user_service.remove(
        user_id=user_id,
        admin_id=admin_id,
    )


async def is_paid_user(
    user_id: int,
):

    return await paid_user_service.is_paid(
        user_id
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "PaidUserService",
    "paid_user_service",
    "add_paid_user",
    "remove_paid_user",
    "is_paid_user",
]

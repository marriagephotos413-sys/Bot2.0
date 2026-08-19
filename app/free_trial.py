import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.config import CONFIG
from app.helpers import format_datetime
from app.keyboards import (
    admin_trial_keyboard,
    trial_keyboard,
)
from app.user_management import user_manager


logger = logging.getLogger(
    "telegram-test-series-bot.free-trial"
)


# ============================================================
# FREE TRIAL SERVICE
# ============================================================

class FreeTrialService:
    """
    Free Trial Management.

    Features:
    - New user trial
    - Trial lock / unlock
    - Trial status
    - Trial expiry
    - Trial usage check
    - Admin control
    """

    def __init__(
        self,
        default_days: Optional[int] = None,
    ):

        self.default_days = (
            default_days
            if default_days is not None
            else CONFIG.FREE_TRIAL_DAYS
        )

        self.locked = False

    # ========================================================
    # STATUS
    # ========================================================

    def is_locked(self) -> bool:

        return self.locked

    def lock(self) -> None:

        self.locked = True

        logger.info(
            "Free trial locked."
        )

    def unlock(self) -> None:

        self.locked = False

        logger.info(
            "Free trial unlocked."
        )

    # ========================================================
    # GET USER
    # ========================================================

    async def get_user(
        self,
        user_id: int,
    ) -> Optional[Dict[str, Any]]:

        try:

            return await user_manager.get_user(
                int(user_id)
            )

        except Exception:

            logger.exception(
                "Failed to load user %s.",
                user_id,
            )

            return None

    # ========================================================
    # CHECK TRIAL ELIGIBILITY
    # ========================================================

    async def can_start(
        self,
        user_id: int,
    ) -> bool:

        if self.locked:

            return False

        user = await self.get_user(
            user_id
        )

        if not user:

            # New user can use trial after registration.
            return True

        # Paid user को free trial की जरूरत नहीं।

        if bool(
            user.get(
                "is_paid",
                user.get(
                    "paid",
                    False,
                ),
            )
        ):

            return False

        # Trial already used.

        if bool(
            user.get(
                "trial_used",
                False,
            )
        ):

            return False

        # Active trial भी दोबारा start नहीं होना चाहिए।

        if bool(
            user.get(
                "trial_active",
                False,
            )
        ):

            return False

        return True

    # ========================================================
    # START TRIAL
    # ========================================================

    async def start(
        self,
        user_id: int,
        days: Optional[int] = None,
    ) -> bool:

        user_id = int(
            user_id
        )

        if self.locked:

            return False

        allowed = await self.can_start(
            user_id
        )

        if not allowed:

            return False

        trial_days = (
            days
            if days is not None
            else self.default_days
        )

        trial_days = max(
            1,
            int(trial_days),
        )

        try:

            result = await user_manager.start_trial(
                user_id,
                days=trial_days,
            )

            if result:

                logger.info(
                    (
                        "Free trial started "
                        "for user=%s "
                        "days=%s"
                    ),
                    user_id,
                    trial_days,
                )

            return bool(
                result
            )

        except Exception:

            logger.exception(
                "Failed to start trial."
            )

            return False

    # ========================================================
    # TRIAL STATUS
    # ========================================================

    async def status(
        self,
        user_id: int,
    ) -> Dict[str, Any]:

        user = await self.get_user(
            user_id
        )

        if not user:

            return {
                "exists": False,
                "active": False,
                "used": False,
                "locked": self.locked,
                "expires_at": None,
            }

        active = False

        try:

            active = await user_manager.trial_active(
                int(user_id)
            )

        except Exception:

            logger.exception(
                "Trial status check failed."
            )

        return {
            "exists": True,
            "active": active,
            "used": bool(
                user.get(
                    "trial_used",
                    False,
                )
            ),
            "locked": self.locked,
            "started_at": user.get(
                "trial_started_at"
            ),
            "expires_at": user.get(
                "trial_expires_at"
            ),
        }

    # ========================================================
    # EXPIRY
    # ========================================================

    async def check_expired(
        self,
        user_id: int,
    ) -> bool:

        user = await self.get_user(
            user_id
        )

        if not user:

            return False

        if not user.get(
            "trial_active",
            False,
        ):

            return False

        expires_at = user.get(
            "trial_expires_at"
        )

        if not expires_at:

            return False

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

                return False

        if expires_at.tzinfo is None:

            expires_at = (
                expires_at.replace(
                    tzinfo=timezone.utc
                )
            )

        if (
            datetime.now(
                timezone.utc
            )
            >= expires_at
        ):

            database = user_manager._get_db()

            if database:

                method = getattr(
                    database,
                    "update_user",
                    None,
                )

                if method:

                    result = method(
                        int(user_id),
                        {
                            "trial_active": False,
                            "updated_at": datetime.now(
                                timezone.utc
                            ),
                        },
                    )

                    if hasattr(
                        result,
                        "__await__",
                    ):

                        await result

            return True

        return False

    # ========================================================
    # FORMAT STATUS
    # ========================================================

    async def format_status(
        self,
        user_id: int,
    ) -> str:

        data = await self.status(
            user_id
        )

        if not data["exists"]:

            return (
                "🎁 <b>FREE TRIAL</b>\n\n"
                "आपका account अभी register नहीं है।\n"
                "पहले /start करें।"
            )

        if data["active"]:

            return (
                "🎁 <b>FREE TRIAL ACTIVE</b>\n\n"
                "🟢 Status: Active\n"
                f"📅 Started: "
                f"{format_datetime(data.get('started_at'))}\n"
                f"⏳ Expires: "
                f"{format_datetime(data.get('expires_at'))}"
            )

        if data["used"]:

            return (
                "🎁 <b>FREE TRIAL</b>\n\n"
                "🔴 आपका free trial पहले ही use हो चुका है।\n\n"
                "💎 Premium plan लेने के लिए pricing देखें।"
            )

        if data["locked"]:

            return (
                "🔒 <b>FREE TRIAL LOCKED</b>\n\n"
                "अभी free trial temporarily बंद है।"
            )

        return (
            "🎁 <b>FREE TRIAL AVAILABLE</b>\n\n"
            f"⏳ Trial Duration: "
            f"{self.default_days} दिन\n\n"
            "नीचे button दबाकर trial शुरू करें।"
        )

    # ========================================================
    # START FROM TELEGRAM
    # ========================================================

    async def handle_start(
        self,
        update,
        context,
    ):

        user = update.effective_user

        if not user:

            return

        user_id = user.id

        started = await self.start(
            user_id
        )

        if started:

            text = (
                "🎉 <b>FREE TRIAL STARTED</b>\n\n"
                f"⏳ आपको "
                f"<b>{self.default_days} दिन</b> "
                "का free trial मिल गया है।\n\n"
                "अब आप available tests extract कर सकते हैं।"
            )

        else:

            text = await self.format_status(
                user_id
            )

        if update.callback_query:

            query = update.callback_query

            try:

                await query.answer()

            except Exception:

                pass

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=trial_keyboard(),
            )

            return

        if update.effective_message:

            await update.effective_message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=trial_keyboard(),
            )

    # ========================================================
    # ADMIN STATUS
    # ========================================================

    def admin_status_text(self) -> str:

        status = (
            "🔴 LOCKED"
            if self.locked
            else "🟢 UNLOCKED"
        )

        return (
            "🎁 <b>FREE TRIAL SETTINGS</b>\n\n"
            f"📌 Status: {status}\n"
            f"⏳ Duration: "
            f"{self.default_days} days"
        )

    # ========================================================
    # ADMIN LOCK
    # ========================================================

    async def admin_lock(
        self,
    ) -> bool:

        self.lock()

        return True

    # ========================================================
    # ADMIN UNLOCK
    # ========================================================

    async def admin_unlock(
        self,
    ) -> bool:

        self.unlock()

        return True

    # ========================================================
    # ADMIN SET DAYS
    # ========================================================

    def set_days(
        self,
        days: int,
    ) -> int:

        self.default_days = max(
            1,
            int(days),
        )

        return self.default_days

    # ========================================================
    # ADMIN PANEL
    # ========================================================

    async def show_admin_panel(
        self,
        update,
    ):

        text = self.admin_status_text()

        keyboard = admin_trial_keyboard()

        if update.callback_query:

            query = update.callback_query

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

    # ========================================================
    # ADMIN LOCK / UNLOCK MESSAGE
    # ========================================================

    async def admin_action_message(
        self,
        update,
        locked: bool,
    ):

        if locked:

            text = (
                "🔒 <b>FREE TRIAL LOCKED</b>\n\n"
                "नए users अब free trial start नहीं कर पाएंगे।"
            )

        else:

            text = (
                "🔓 <b>FREE TRIAL UNLOCKED</b>\n\n"
                "Free trial फिर से available है।"
            )

        if update.callback_query:

            query = update.callback_query

            try:

                await query.answer()

            except Exception:

                pass

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=admin_trial_keyboard(),
            )

            return

        if update.effective_message:

            await update.effective_message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=admin_trial_keyboard(),
            )


# ============================================================
# GLOBAL INSTANCE
# ============================================================

free_trial = FreeTrialService()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def start_free_trial(
    user_id: int,
    days: Optional[int] = None,
) -> bool:

    return await free_trial.start(
        user_id,
        days=days,
    )


async def can_start_trial(
    user_id: int,
) -> bool:

    return await free_trial.can_start(
        user_id
    )


async def trial_status(
    user_id: int,
):

    return await free_trial.status(
        user_id
    )


def lock_free_trial():

    free_trial.lock()


def unlock_free_trial():

    free_trial.unlock()


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "FreeTrialService",
    "free_trial",
    "start_free_trial",
    "can_start_trial",
    "trial_status",
    "lock_free_trial",
    "unlock_free_trial",
]

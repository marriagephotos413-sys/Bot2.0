import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


logger = logging.getLogger(
    "telegram-test-series-bot.user-management"
)


# ============================================================
# USER MANAGEMENT
# ============================================================

class UserManagement:
    """
    User management service.

    MongoDB में user-related operations handle करता है:

    - Register / update user
    - User info
    - Ban
    - Unban
    - Paid status
    - Trial status
    - User list
    - Activity tracking
    """

    def __init__(
        self,
        database=None,
    ):

        self.db = database

    # ========================================================
    # DATABASE
    # ========================================================

    def _get_db(self):

        if self.db is not None:
            return self.db

        try:

            from app.database import db

            return db

        except Exception:

            logger.exception(
                "Database instance unavailable."
            )

            return None

    # ========================================================
    # USER PAYLOAD
    # ========================================================

    @staticmethod
    def build_user_payload(
        user: Any,
    ) -> Dict[str, Any]:

        now = datetime.now(
            timezone.utc
        )

        return {
            "user_id": getattr(
                user,
                "id",
                None,
            ),
            "username": getattr(
                user,
                "username",
                None,
            ),
            "first_name": getattr(
                user,
                "first_name",
                None,
            ),
            "last_name": getattr(
                user,
                "last_name",
                None,
            ),
            "language_code": getattr(
                user,
                "language_code",
                None,
            ),
            "is_bot": bool(
                getattr(
                    user,
                    "is_bot",
                    False,
                )
            ),
            "last_seen": now,
            "updated_at": now,
        }

    # ========================================================
    # REGISTER USER
    # ========================================================

    async def register_user(
        self,
        user: Any,
    ) -> Optional[Dict[str, Any]]:

        if not user:
            return None

        user_id = getattr(
            user,
            "id",
            None,
        )

        if not user_id:
            return None

        database = self._get_db()

        if database is None:
            return None

        payload = self.build_user_payload(
            user
        )

        try:

            # Preferred database method.

            method = getattr(
                database,
                "upsert_user",
                None,
            )

            if method:

                result = method(
                    payload
                )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return result

            # Alternative implementation.

            method = getattr(
                database,
                "create_or_update_user",
                None,
            )

            if method:

                result = method(
                    payload
                )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return result

            logger.warning(
                "No user upsert method found."
            )

        except Exception:

            logger.exception(
                "User registration failed for %s.",
                user_id,
            )

        return None

    # ========================================================
    # GET USER
    # ========================================================

    async def get_user(
        self,
        user_id: int,
    ) -> Optional[Dict[str, Any]]:

        database = self._get_db()

        if database is None:
            return None

        user_id = int(
            user_id
        )

        try:

            for method_name in (
                "get_user",
                "find_user",
                "get_user_by_id",
            ):

                method = getattr(
                    database,
                    method_name,
                    None,
                )

                if not method:
                    continue

                result = method(
                    user_id
                )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                if result is not None:

                    if isinstance(
                        result,
                        dict,
                    ):

                        return result

                    try:

                        return dict(
                            result
                        )

                    except Exception:

                        return {
                            "user_id": user_id,
                            "data": result,
                        }

        except Exception:

            logger.exception(
                "Failed to get user %s.",
                user_id,
            )

        return None

    # ========================================================
    # USER EXISTS
    # ========================================================

    async def user_exists(
        self,
        user_id: int,
    ) -> bool:

        user = await self.get_user(
            user_id
        )

        return user is not None

    # ========================================================
    # BAN USER
    # ========================================================

    async def ban_user(
        self,
        user_id: int,
        reason: str = "",
        admin_id: Optional[int] = None,
    ) -> bool:

        database = self._get_db()

        if database is None:
            return False

        user_id = int(
            user_id
        )

        now = datetime.now(
            timezone.utc
        )

        try:

            for method_name in (
                "ban_user",
                "set_user_banned",
                "update_user",
            ):

                method = getattr(
                    database,
                    method_name,
                    None,
                )

                if not method:
                    continue

                if method_name == "ban_user":

                    result = method(
                        user_id,
                        reason=reason,
                        admin_id=admin_id,
                    )

                elif method_name == "set_user_banned":

                    result = method(
                        user_id,
                        True,
                    )

                else:

                    result = method(
                        user_id,
                        {
                            "is_banned": True,
                            "ban_reason": reason,
                            "banned_by": admin_id,
                            "banned_at": now,
                            "updated_at": now,
                        },
                    )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return (
                    bool(result)
                    if result is not None
                    else True
                )

        except Exception:

            logger.exception(
                "Failed to ban user %s.",
                user_id,
            )

        return False

    # ========================================================
    # UNBAN USER
    # ========================================================

    async def unban_user(
        self,
        user_id: int,
        admin_id: Optional[int] = None,
    ) -> bool:

        database = self._get_db()

        if database is None:
            return False

        user_id = int(
            user_id
        )

        now = datetime.now(
            timezone.utc
        )

        try:

            for method_name in (
                "unban_user",
                "set_user_banned",
                "update_user",
            ):

                method = getattr(
                    database,
                    method_name,
                    None,
                )

                if not method:
                    continue

                if method_name == "unban_user":

                    result = method(
                        user_id,
                        admin_id=admin_id,
                    )

                elif method_name == "set_user_banned":

                    result = method(
                        user_id,
                        False,
                    )

                else:

                    result = method(
                        user_id,
                        {
                            "is_banned": False,
                            "unbanned_by": admin_id,
                            "unbanned_at": now,
                            "updated_at": now,
                        },
                    )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return (
                    bool(result)
                    if result is not None
                    else True
                )

        except Exception:

            logger.exception(
                "Failed to unban user %s.",
                user_id,
            )

        return False

    # ========================================================
    # CHECK BAN
    # ========================================================

    async def is_banned(
        self,
        user_id: int,
    ) -> bool:

        user = await self.get_user(
            user_id
        )

        if not user:
            return False

        return bool(
            user.get(
                "is_banned",
                user.get(
                    "banned",
                    False,
                ),
            )
        )

    # ========================================================
    # ADD PAID USER
    # ========================================================

    async def add_paid_user(
        self,
        user_id: int,
        plan: str = "premium",
        days: Optional[int] = None,
        payment_id: Optional[str] = None,
        admin_id: Optional[int] = None,
    ) -> bool:

        database = self._get_db()

        if database is None:
            return False

        user_id = int(
            user_id
        )

        now = datetime.now(
            timezone.utc
        )

        expires_at = None

        if days is not None:

            expires_at = (
                now
                + timedelta(
                    days=max(
                        0,
                        int(days),
                    )
                )
            )

        data = {
            "is_paid": True,
            "paid": True,
            "paid_plan": plan,
            "paid_at": now,
            "paid_expires_at": expires_at,
            "payment_id": payment_id,
            "paid_by": admin_id,
            "updated_at": now,
        }

        try:

            for method_name in (
                "add_paid_user",
                "set_paid_user",
                "update_user",
            ):

                method = getattr(
                    database,
                    method_name,
                    None,
                )

                if not method:
                    continue

                if method_name == "add_paid_user":

                    result = method(
                        user_id,
                        data,
                    )

                elif method_name == "set_paid_user":

                    result = method(
                        user_id,
                        True,
                        data,
                    )

                else:

                    result = method(
                        user_id,
                        data,
                    )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return (
                    bool(result)
                    if result is not None
                    else True
                )

        except Exception:

            logger.exception(
                "Failed to add paid user %s.",
                user_id,
            )

        return False

    # ========================================================
    # REMOVE PAID USER
    # ========================================================

    async def remove_paid_user(
        self,
        user_id: int,
        admin_id: Optional[int] = None,
    ) -> bool:

        database = self._get_db()

        if database is None:
            return False

        user_id = int(
            user_id
        )

        now = datetime.now(
            timezone.utc
        )

        data = {
            "is_paid": False,
            "paid": False,
            "paid_plan": None,
            "paid_expires_at": None,
            "paid_removed_at": now,
            "paid_removed_by": admin_id,
            "updated_at": now,
        }

        try:

            for method_name in (
                "remove_paid_user",
                "set_paid_user",
                "update_user",
            ):

                method = getattr(
                    database,
                    method_name,
                    None,
                )

                if not method:
                    continue

                if method_name == "remove_paid_user":

                    result = method(
                        user_id,
                        admin_id=admin_id,
                    )

                elif method_name == "set_paid_user":

                    result = method(
                        user_id,
                        False,
                        data,
                    )

                else:

                    result = method(
                        user_id,
                        data,
                    )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return (
                    bool(result)
                    if result is not None
                    else True
                )

        except Exception:

            logger.exception(
                "Failed to remove paid user %s.",
                user_id,
            )

        return False

    # ========================================================
    # PAID STATUS
    # ========================================================

    async def is_paid(
        self,
        user_id: int,
    ) -> bool:

        user = await self.get_user(
            user_id
        )

        if not user:
            return False

        paid = bool(
            user.get(
                "is_paid",
                user.get(
                    "paid",
                    False,
                ),
            )
        )

        if not paid:
            return False

        expires_at = user.get(
            "paid_expires_at"
        )

        if expires_at:

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

                    expires_at = None

            if expires_at:

                if (
                    expires_at.tzinfo
                    is None
                ):

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

                    return False

        return True

    # ========================================================
    # FREE TRIAL
    # ========================================================

    async def start_trial(
        self,
        user_id: int,
        days: int = 3,
    ) -> bool:

        database = self._get_db()

        if database is None:
            return False

        user_id = int(
            user_id
        )

        now = datetime.now(
            timezone.utc
        )

        expires_at = (
            now
            + timedelta(
                days=max(
                    1,
                    int(days),
                )
            )
        )

        data = {
            "trial_used": True,
            "trial_active": True,
            "trial_started_at": now,
            "trial_expires_at": expires_at,
            "updated_at": now,
        }

        try:

            method = getattr(
                database,
                "update_user",
                None,
            )

            if method:

                result = method(
                    user_id,
                    data,
                )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return (
                    bool(result)
                    if result is not None
                    else True
                )

        except Exception:

            logger.exception(
                "Failed to start trial for %s.",
                user_id,
            )

        return False

    # ========================================================
    # TRIAL STATUS
    # ========================================================

    async def trial_active(
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

        return (
            datetime.now(
                timezone.utc
            )
            < expires_at
        )

    # ========================================================
    # USER ACTIVITY
    # ========================================================

    async def record_activity(
        self,
        user_id: int,
        activity: str,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> bool:

        database = self._get_db()

        if database is None:
            return False

        now = datetime.now(
            timezone.utc
        )

        data = {
            "activity": activity,
            "metadata": metadata or {},
            "created_at": now,
        }

        try:

            for method_name in (
                "record_user_activity",
                "add_user_activity",
            ):

                method = getattr(
                    database,
                    method_name,
                    None,
                )

                if not method:
                    continue

                result = method(
                    user_id,
                    data,
                )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return (
                    bool(result)
                    if result is not None
                    else True
                )

        except Exception:

            logger.exception(
                "Activity recording failed."
            )

        return False

    # ========================================================
    # USER LIST
    # ========================================================

    async def list_users(
        self,
        limit: int = 100,
        skip: int = 0,
        paid_only: bool = False,
        banned_only: bool = False,
    ) -> List[Dict[str, Any]]:

        database = self._get_db()

        if database is None:
            return []

        limit = max(
            1,
            min(
                int(limit),
                1000,
            ),
        )

        skip = max(
            0,
            int(skip),
        )

        try:

            if paid_only:

                method = getattr(
                    database,
                    "list_paid_users",
                    None,
                )

                if method:

                    result = method(
                        limit=limit,
                        skip=skip,
                    )

                    if hasattr(
                        result,
                        "__await__",
                    ):

                        result = await result

                    return list(
                        result or []
                    )

            if banned_only:

                method = getattr(
                    database,
                    "list_banned_users",
                    None,
                )

                if method:

                    result = method(
                        limit=limit,
                        skip=skip,
                    )

                    if hasattr(
                        result,
                        "__await__",
                    ):

                        result = await result

                    return list(
                        result or []
                    )

            method = getattr(
                database,
                "list_users",
                None,
            )

            if method:

                result = method(
                    limit=limit,
                    skip=skip,
                )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return list(
                    result or []
                )

        except Exception:

            logger.exception(
                "Failed to list users."
            )

        return []

    # ========================================================
    # COUNTS
    # ========================================================

    async def count_users(
        self,
    ) -> int:

        database = self._get_db()

        if database is None:
            return 0

        try:

            method = getattr(
                database,
                "count_users",
                None,
            )

            if method:

                result = method()

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return int(
                    result or 0
                )

        except Exception:

            logger.exception(
                "User count failed."
            )

        return 0

    async def count_paid_users(
        self,
    ) -> int:

        database = self._get_db()

        if database is None:
            return 0

        try:

            method = getattr(
                database,
                "count_paid_users",
                None,
            )

            if method:

                result = method()

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return int(
                    result or 0
                )

        except Exception:

            logger.exception(
                "Paid user count failed."
            )

        return 0

    async def count_banned_users(
        self,
    ) -> int:

        database = self._get_db()

        if database is None:
            return 0

        try:

            method = getattr(
                database,
                "count_banned_users",
                None,
            )

            if method:

                result = method()

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return int(
                    result or 0
                )

        except Exception:

            logger.exception(
                "Banned user count failed."
            )

        return 0


# ============================================================
# GLOBAL INSTANCE
# ============================================================

user_manager = UserManagement()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def register_user(
    user: Any,
):

    return await user_manager.register_user(
        user
    )


async def get_user(
    user_id: int,
):

    return await user_manager.get_user(
        user_id
    )


async def ban_user(
    user_id: int,
    reason: str = "",
    admin_id: Optional[int] = None,
):

    return await user_manager.ban_user(
        user_id,
        reason=reason,
        admin_id=admin_id,
    )


async def unban_user(
    user_id: int,
    admin_id: Optional[int] = None,
):

    return await user_manager.unban_user(
        user_id,
        admin_id=admin_id,
    )


async def is_banned(
    user_id: int,
):

    return await user_manager.is_banned(
        user_id
    )


async def is_paid(
    user_id: int,
):

    return await user_manager.is_paid(
        user_id
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "UserManagement",
    "user_manager",
    "register_user",
    "get_user",
    "ban_user",
    "unban_user",
    "is_banned",
    "is_paid",
]

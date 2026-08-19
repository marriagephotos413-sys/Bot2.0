import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Optional

from telegram import Update
from telegram.ext import ContextTypes

from app.rate_limiter import (
    check_user_rate_limit,
    rate_limit_message,
)


logger = logging.getLogger(
    "telegram-test-series-bot.middleware"
)


Handler = Callable[
    [Update, ContextTypes.DEFAULT_TYPE],
    Awaitable[Any],
]


# ============================================================
# USER ID
# ============================================================

def get_user_id(
    update: Update,
) -> Optional[int]:

    if not update:
        return None

    user = update.effective_user

    if not user:
        return None

    return user.id


# ============================================================
# ADMIN CHECK
# ============================================================

def is_admin(
    user_id: Optional[int],
) -> bool:

    if not user_id:
        return False

    try:

        from app.config import CONFIG

        return int(user_id) in CONFIG.ADMIN_IDS

    except Exception:

        logger.exception(
            "Admin check failed."
        )

        return False


# ============================================================
# BAN CHECK
# ============================================================

async def is_user_banned(
    user_id: int,
) -> bool:

    """
    MongoDB में user की ban status check करता है।

    Database implementation अलग module में है,
    इसलिए यहाँ flexible method lookup रखा गया है।
    """

    try:

        from app.database import db

        # अलग-अलग database implementations को support करने
        # के लिए common method names check किए जाते हैं।

        for method_name in (
            "is_user_banned",
            "get_user",
            "find_user",
        ):

            method = getattr(
                db,
                method_name,
                None,
            )

            if not method:
                continue

            try:

                result = method(
                    user_id
                )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

            except TypeError:

                continue

            if method_name == "is_user_banned":

                return bool(
                    result
                )

            if isinstance(
                result,
                dict,
            ):

                return bool(
                    result.get(
                        "is_banned",
                        result.get(
                            "banned",
                            False,
                        ),
                    )
                )

            if result is not None:

                return bool(
                    getattr(
                        result,
                        "is_banned",
                        getattr(
                            result,
                            "banned",
                            False,
                        ),
                    )
                )

            return False

    except Exception:

        logger.exception(
            "Ban status check failed."
        )

    return False


# ============================================================
# USER REGISTRATION
# ============================================================

async def ensure_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:

    """
    User को database में register/update करने की कोशिश करता है।
    """

    user = update.effective_user

    if not user:
        return False

    try:

        from app.database import db

        payload = {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "language_code": user.language_code,
        }

        # Common method names support.

        for method_name in (
            "upsert_user",
            "create_or_update_user",
            "save_user",
            "register_user",
        ):

            method = getattr(
                db,
                method_name,
                None,
            )

            if not method:
                continue

            try:

                result = method(
                    payload
                )

                if hasattr(
                    result,
                    "__await__",
                ):

                    await result

                return True

            except TypeError:

                try:

                    result = method(
                        user.id,
                        payload,
                    )

                    if hasattr(
                        result,
                        "__await__",
                    ):

                        await result

                    return True

                except Exception:

                    continue

    except Exception:

        logger.exception(
            "User registration failed."
        )

    return False


# ============================================================
# RATE LIMIT
# ============================================================

async def check_request_limit(
    update: Update,
) -> bool:

    user_id = get_user_id(
        update
    )

    if not user_id:

        return True

    # Admin bypass

    if is_admin(
        user_id
    ):

        return True

    result = await check_user_rate_limit(
        user_id
    )

    if result.allowed:

        return True

    try:

        if update.callback_query:

            await update.callback_query.answer(
                (
                    f"⏳ Too many requests.\n"
                    f"Please wait {result.retry_after}s."
                ),
                show_alert=True,
            )

        elif update.effective_message:

            await update.effective_message.reply_text(
                rate_limit_message(
                    result
                )
            )

    except Exception:

        logger.exception(
            "Could not send rate limit message."
        )

    return False


# ============================================================
# BAN MESSAGE
# ============================================================

async def send_ban_message(
    update: Update,
) -> None:

    text = (
        "🚫 <b>Access Denied</b>\n\n"
        "आपका account इस Bot से blocked है।"
    )

    try:

        if update.callback_query:

            await update.callback_query.answer(
                "🚫 आपका account blocked है।",
                show_alert=True,
            )

            return

        if update.effective_message:

            await update.effective_message.reply_text(
                text,
                parse_mode="HTML",
            )

    except Exception:

        logger.exception(
            "Failed to send ban message."
        )


# ============================================================
# COMMON ACCESS CHECK
# ============================================================

async def check_access(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    check_rate_limit: bool = True,
    check_ban: bool = True,
    register: bool = True,
) -> bool:

    user_id = get_user_id(
        update
    )

    if not user_id:

        return False

    # --------------------------------------------------------
    # Register / update user
    # --------------------------------------------------------

    if register:

        await ensure_user(
            update,
            context,
        )

    # --------------------------------------------------------
    # Ban check
    # --------------------------------------------------------

    if (
        check_ban
        and not is_admin(user_id)
    ):

        banned = await is_user_banned(
            user_id
        )

        if banned:

            await send_ban_message(
                update
            )

            return False

    # --------------------------------------------------------
    # Rate limit
    # --------------------------------------------------------

    if (
        check_rate_limit
        and not is_admin(user_id)
    ):

        allowed = await check_request_limit(
            update
        )

        if not allowed:

            return False

    return True


# ============================================================
# DECORATOR
# ============================================================

def protected(
    *,
    check_rate_limit: bool = True,
    check_ban: bool = True,
    register: bool = True,
):
    """
    Handler protection decorator.

    Example:

        @protected()
        async def my_handler(update, context):
            ...
    """

    def decorator(
        function: Handler,
    ):

        @wraps(function)
        async def wrapper(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            *args,
            **kwargs,
        ):

            try:

                allowed = await check_access(
                    update,
                    context,
                    check_rate_limit=check_rate_limit,
                    check_ban=check_ban,
                    register=register,
                )

                if not allowed:

                    return None

                return await function(
                    update,
                    context,
                    *args,
                    **kwargs,
                )

            except Exception:

                logger.exception(
                    "Protected handler failed: %s",
                    function.__name__,
                )

                raise

        return wrapper

    return decorator


# ============================================================
# ADMIN DECORATOR
# ============================================================

def admin_only():

    def decorator(
        function: Handler,
    ):

        @wraps(function)
        async def wrapper(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            *args,
            **kwargs,
        ):

            user_id = get_user_id(
                update
            )

            if not is_admin(
                user_id
            ):

                try:

                    if update.callback_query:

                        await update.callback_query.answer(
                            "⛔ Admin only.",
                            show_alert=True,
                        )

                    elif update.effective_message:

                        await update.effective_message.reply_text(
                            "⛔ यह command केवल Admin के लिए है।"
                        )

                except Exception:

                    logger.exception(
                        "Admin denial message failed."
                    )

                return None

            return await function(
                update,
                context,
                *args,
                **kwargs,
            )

        return wrapper

    return decorator


# ============================================================
# CALLBACK ACKNOWLEDGEMENT
# ============================================================

async def acknowledge_callback(
    update: Update,
    text: Optional[str] = None,
    show_alert: bool = False,
) -> None:

    query = update.callback_query

    if not query:

        return

    try:

        await query.answer(
            text=text,
            show_alert=show_alert,
        )

    except Exception:

        logger.debug(
            "Callback acknowledgement failed.",
            exc_info=True,
        )


# ============================================================
# SAFE HANDLER
# ============================================================

def safe_handler(
    fallback_message: str = (
        "⚠️ Temporary error आया। "
        "कृपया थोड़ी देर बाद फिर try करें।"
    ),
):

    def decorator(
        function: Handler,
    ):

        @wraps(function)
        async def wrapper(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            *args,
            **kwargs,
        ):

            try:

                return await function(
                    update,
                    context,
                    *args,
                    **kwargs,
                )

            except Exception:

                logger.exception(
                    "Handler error: %s",
                    function.__name__,
                )

                try:

                    if update.effective_message:

                        await update.effective_message.reply_text(
                            fallback_message
                        )

                    elif update.callback_query:

                        await update.callback_query.answer(
                            fallback_message,
                            show_alert=True,
                        )

                except Exception:

                    logger.debug(
                        "Fallback message failed.",
                        exc_info=True,
                    )

                return None

        return wrapper

    return decorator


# ============================================================
# COMBINED PROTECTION
# ============================================================

def user_protected(
    *,
    rate_limit: bool = True,
    ban_check: bool = True,
):
    """
    Normal user handlers के लिए combined decorator.

    इसमें:
        - User registration
        - Ban check
        - Rate limit
        - Error protection
    शामिल है।
    """

    def decorator(
        function: Handler,
    ):

        @wraps(function)
        async def wrapper(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            *args,
            **kwargs,
        ):

            allowed = await check_access(
                update,
                context,
                check_rate_limit=rate_limit,
                check_ban=ban_check,
                register=True,
            )

            if not allowed:

                return None

            try:

                return await function(
                    update,
                    context,
                    *args,
                    **kwargs,
                )

            except Exception:

                logger.exception(
                    "User handler failed: %s",
                    function.__name__,
                )

                try:

                    if update.effective_message:

                        await update.effective_message.reply_text(
                            (
                                "⚠️ अभी server पर load/error है।\n"
                                "Please wait करके दोबारा try करें।"
                            )
                        )

                except Exception:

                    logger.debug(
                        "Could not send handler error.",
                        exc_info=True,
                    )

                return None

        return wrapper

    return decorator


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "get_user_id",
    "is_admin",
    "is_user_banned",
    "ensure_user",
    "check_request_limit",
    "send_ban_message",
    "check_access",
    "protected",
    "admin_only",
    "acknowledge_callback",
    "safe_handler",
    "user_protected",
]

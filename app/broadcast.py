import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from telegram import Bot, Update
from telegram.error import (
    BadRequest,
    Forbidden,
    NetworkError,
    RetryAfter,
    TelegramError,
)

from app.helpers import (
    format_duration,
    safe_int,
    truncate,
)
from app.user_management import user_manager


logger = logging.getLogger(
    "telegram-test-series-bot.broadcast"
)


# ============================================================
# BROADCAST SERVICE
# ============================================================

class BroadcastService:
    """
    Broadcast manager.

    Features:
    - All users broadcast
    - Paid users broadcast
    - Free users broadcast
    - Banned users skip
    - Deleted/blocked accounts cleanup
    - Telegram flood control handling
    - Progress tracking
    - Pause between messages
    - Failed user tracking
    - RetryAfter support
    """

    def __init__(
        self,
        bot: Optional[Bot] = None,
        batch_size: int = 20,
        delay: float = 0.08,
    ):

        self.bot = bot

        self.batch_size = max(
            1,
            int(batch_size),
        )

        self.delay = max(
            0.01,
            float(delay),
        )

        self.running = False
        self.cancel_requested = False

        self.current_job_id: Optional[str] = None

        self.total = 0
        self.sent = 0
        self.failed = 0
        self.blocked = 0

        self.started_at: Optional[
            datetime
        ] = None

        self.finished_at: Optional[
            datetime
        ] = None

        self.failed_users: List[
            Dict[str, Any]
        ] = []

    # ========================================================
    # SET BOT
    # ========================================================

    def set_bot(
        self,
        bot: Bot,
    ) -> None:

        self.bot = bot

    # ========================================================
    # RESET
    # ========================================================

    def reset(self) -> None:

        self.running = False
        self.cancel_requested = False

        self.current_job_id = None

        self.total = 0
        self.sent = 0
        self.failed = 0
        self.blocked = 0

        self.started_at = None
        self.finished_at = None

        self.failed_users.clear()

    # ========================================================
    # USER FETCH
    # ========================================================

    async def _get_users(
        self,
        target: str,
        limit: int = 100000,
    ) -> List[Dict[str, Any]]:

        target = (
            str(target)
            .strip()
            .lower()
        )

        if target == "paid":

            return await user_manager.list_users(
                limit=min(
                    safe_int(
                        limit,
                        100000,
                    ),
                    100000,
                ),
                skip=0,
                paid_only=True,
            )

        if target == "free":

            users = await user_manager.list_users(
                limit=min(
                    safe_int(
                        limit,
                        100000,
                    ),
                    100000,
                ),
                skip=0,
                paid_only=False,
            )

            result = []

            for user in users:

                is_paid = bool(
                    user.get(
                        "is_paid",
                        user.get(
                            "paid",
                            False,
                        ),
                    )
                )

                if not is_paid:

                    result.append(
                        user
                    )

            return result

        return await user_manager.list_users(
            limit=min(
                safe_int(
                    limit,
                    100000,
                ),
                100000,
            ),
            skip=0,
        )

    # ========================================================
    # SEND MESSAGE
    # ========================================================

    async def _send(
        self,
        user_id: int,
        text: str,
        *,
        parse_mode: Optional[str] = None,
        disable_web_page_preview: bool = True,
    ) -> bool:

        if not self.bot:

            raise RuntimeError(
                "Bot instance is not configured."
            )

        while True:

            try:

                await self.bot.send_message(
                    chat_id=int(user_id),
                    text=text,
                    parse_mode=parse_mode,
                    disable_web_page_preview=(
                        disable_web_page_preview
                    ),
                )

                return True

            except RetryAfter as exc:

                retry_after = max(
                    1,
                    int(
                        getattr(
                            exc,
                            "retry_after",
                            1,
                        )
                    ),
                )

                logger.warning(
                    (
                        "Telegram flood limit. "
                        "Waiting %s seconds."
                    ),
                    retry_after,
                )

                await asyncio.sleep(
                    retry_after
                )

            except Forbidden:

                self.blocked += 1

                return False

            except BadRequest as exc:

                logger.warning(
                    "Bad request for user %s: %s",
                    user_id,
                    exc,
                )

                return False

            except NetworkError as exc:

                logger.warning(
                    (
                        "Network error for "
                        "user %s: %s"
                    ),
                    user_id,
                    exc,
                )

                await asyncio.sleep(
                    2
                )

            except TelegramError as exc:

                logger.warning(
                    (
                        "Telegram error for "
                        "user %s: %s"
                    ),
                    user_id,
                    exc,
                )

                return False

            except Exception as exc:

                logger.exception(
                    (
                        "Unexpected broadcast "
                        "error for user %s."
                    ),
                    user_id,
                )

                return False

    # ========================================================
    # BROADCAST
    # ========================================================

    async def send(
        self,
        text: str,
        target: str = "all",
        *,
        parse_mode: Optional[str] = "HTML",
        job_id: Optional[str] = None,
        limit: int = 100000,
    ) -> Dict[str, Any]:

        if self.running:

            raise RuntimeError(
                "Another broadcast is already running."
            )

        if not text or not text.strip():

            raise ValueError(
                "Broadcast message is empty."
            )

        self.reset()

        self.running = True
        self.cancel_requested = False

        self.current_job_id = (
            job_id
            or (
                f"broadcast-"
                f"{int(datetime.now().timestamp())}"
            )
        )

        self.started_at = datetime.now(
            timezone.utc
        )

        users = await self._get_users(
            target,
            limit=limit,
        )

        self.total = len(
            users
        )

        logger.info(
            (
                "Broadcast started. "
                "job=%s target=%s total=%s"
            ),
            self.current_job_id,
            target,
            self.total,
        )

        try:

            for index, user in enumerate(
                users,
                start=1,
            ):

                if self.cancel_requested:

                    logger.warning(
                        "Broadcast cancelled."
                    )

                    break

                user_id = user.get(
                    "user_id",
                    user.get(
                        "id"
                    ),
                )

                if not user_id:

                    self.failed += 1

                    continue

                success = await self._send(
                    int(user_id),
                    text,
                    parse_mode=parse_mode,
                )

                if success:

                    self.sent += 1

                else:

                    self.failed += 1

                    self.failed_users.append(
                        {
                            "user_id": int(
                                user_id
                            ),
                            "reason": (
                                "send_failed"
                            ),
                        }
                    )

                # ------------------------------------------------
                # Small delay prevents unnecessary Telegram load.
                # ------------------------------------------------

                await asyncio.sleep(
                    self.delay
                )

                # ------------------------------------------------
                # Batch pause.
                # ------------------------------------------------

                if (
                    index
                    % self.batch_size
                    == 0
                ):

                    await asyncio.sleep(
                        0.5
                    )

        finally:

            self.running = False

            self.finished_at = datetime.now(
                timezone.utc
            )

        result = self.result()

        logger.info(
            (
                "Broadcast finished. "
                "job=%s sent=%s failed=%s blocked=%s"
            ),
            self.current_job_id,
            self.sent,
            self.failed,
            self.blocked,
        )

        return result

    # ========================================================
    # CANCEL
    # ========================================================

    def cancel(self) -> bool:

        if not self.running:

            return False

        self.cancel_requested = True

        logger.warning(
            "Broadcast cancellation requested."
        )

        return True

    # ========================================================
    # STATUS
    # ========================================================

    def progress(self) -> float:

        if self.total <= 0:

            return 0.0

        return (
            self.sent
            + self.failed
        ) / self.total * 100

    # ========================================================
    # RESULT
    # ========================================================

    def result(self) -> Dict[str, Any]:

        started = (
            self.started_at
        )

        finished = (
            self.finished_at
        )

        duration = 0

        if started:

            end = (
                finished
                or datetime.now(
                    timezone.utc
                )
            )

            duration = int(
                (
                    end - started
                ).total_seconds()
            )

        return {
            "job_id": self.current_job_id,
            "running": self.running,
            "cancelled": self.cancel_requested,
            "total": self.total,
            "sent": self.sent,
            "failed": self.failed,
            "blocked": self.blocked,
            "progress": round(
                self.progress(),
                2,
            ),
            "duration": duration,
            "duration_text": format_duration(
                duration
            ),
            "failed_users": list(
                self.failed_users
            ),
        }

    # ========================================================
    # STATUS TEXT
    # ========================================================

    def status_text(
        self,
    ) -> str:

        data = self.result()

        if data["running"]:

            status = "🟢 RUNNING"

        elif data["cancelled"]:

            status = "🟡 CANCELLED"

        else:

            status = "✅ COMPLETED"

        return (
            "📢 <b>BROADCAST STATUS</b>\n"
            "\n"
            f"📌 Status: {status}\n"
            f"🆔 Job: "
            f"<code>{data['job_id']}</code>\n"
            "\n"
            f"👥 Total: "
            f"<b>{data['total']}</b>\n"
            f"✅ Sent: "
            f"<b>{data['sent']}</b>\n"
            f"❌ Failed: "
            f"<b>{data['failed']}</b>\n"
            f"🚫 Blocked: "
            f"<b>{data['blocked']}</b>\n"
            f"📊 Progress: "
            f"<b>{data['progress']}%</b>\n"
            f"⏱ Duration: "
            f"<b>{data['duration_text']}</b>"
        )


# ============================================================
# GLOBAL SERVICE
# ============================================================

broadcast_service = BroadcastService()


# ============================================================
# SET BOT
# ============================================================

def set_broadcast_bot(
    bot: Bot,
) -> None:

    broadcast_service.set_bot(
        bot
    )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

async def broadcast_message(
    text: str,
    target: str = "all",
    *,
    bot: Optional[Bot] = None,
    parse_mode: str = "HTML",
    job_id: Optional[str] = None,
) -> Dict[str, Any]:

    if bot:

        broadcast_service.set_bot(
            bot
        )

    return await broadcast_service.send(
        text=text,
        target=target,
        parse_mode=parse_mode,
        job_id=job_id,
    )


# ============================================================
# STATUS
# ============================================================

def broadcast_status() -> Dict[str, Any]:

    return broadcast_service.result()


def broadcast_status_text() -> str:

    return broadcast_service.status_text()


def cancel_broadcast() -> bool:

    return broadcast_service.cancel()


# ============================================================
# TELEGRAM ADMIN PREVIEW
# ============================================================

async def show_broadcast_status(
    update: Update,
    context,
):

    try:

        text = broadcast_service.status_text()

        if update.callback_query:

            query = update.callback_query

            try:

                await query.answer()

            except Exception:

                pass

            await query.edit_message_text(
                text,
                parse_mode="HTML",
            )

            return

        if update.effective_message:

            await update.effective_message.reply_text(
                text,
                parse_mode="HTML",
            )

    except Exception:

        logger.exception(
            "Failed to show broadcast status."
        )


# ============================================================
# BROADCAST PREVIEW
# ============================================================

def build_preview(
    text: str,
    target: str,
) -> str:

    target_names = {
        "all": "👥 All Users",
        "paid": "💎 Paid Users",
        "free": "🆓 Free Users",
    }

    target_text = target_names.get(
        target.lower(),
        target,
    )

    return (
        "📢 <b>BROADCAST PREVIEW</b>\n"
        "\n"
        f"🎯 Target: "
        f"<b>{target_text}</b>\n"
        "\n"
        "📝 <b>Message:</b>\n"
        f"{truncate(text, 3500)}"
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "BroadcastService",
    "broadcast_service",
    "set_broadcast_bot",
    "broadcast_message",
    "broadcast_status",
    "broadcast_status_text",
    "cancel_broadcast",
    "show_broadcast_status",
    "build_preview",
]

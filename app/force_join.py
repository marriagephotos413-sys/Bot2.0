import logging
from typing import Any, Dict, List, Optional

from telegram import Update
from telegram.error import TelegramError

from app.config import CONFIG
from app.helpers import clean_text
from app.keyboards import force_join_keyboard


logger = logging.getLogger(
    "telegram-test-series-bot.force-join"
)


# ============================================================
# FORCE JOIN SERVICE
# ============================================================

class ForceJoinService:
    """
    Force Join management.

    Features:
    - Multiple required channels
    - Add channel
    - Remove channel
    - List channels
    - Check user membership
    - Verify all required channels
    - Admin management
    """

    def __init__(self):

        self.channels: Dict[
            str,
            Dict[str, Any]
        ] = {}

        self._load_from_environment()

    # ========================================================
    # LOAD ENV
    # ========================================================

    def _load_from_environment(self):

        channels = getattr(
            CONFIG,
            "FORCE_JOIN_CHANNELS",
            [],
        )

        if not channels:
            return

        for index, channel in enumerate(
            channels,
            start=1,
        ):

            channel = clean_text(
                channel
            )

            if not channel:
                continue

            channel_id = (
                f"env_{index}"
            )

            self.channels[
                channel_id
            ] = {
                "id": channel_id,
                "channel": channel,
                "title": channel,
                "url": (
                    channel
                    if channel.startswith(
                        "http"
                    )
                    else None
                ),
                "enabled": True,
                "source": "environment",
            }

    # ========================================================
    # NORMALIZE CHANNEL
    # ========================================================

    @staticmethod
    def normalize_channel(
        channel: Any,
    ) -> str:

        value = clean_text(
            channel
        )

        if value.startswith(
            "https://t.me/"
        ):

            return (
                "@"
                + value.split(
                    "https://t.me/",
                    1,
                )[1].strip(
                    "/"
                )
            )

        if value.startswith(
            "http://t.me/"
        ):

            return (
                "@"
                + value.split(
                    "http://t.me/",
                    1,
                )[1].strip(
                    "/"
                )
            )

        return value

    # ========================================================
    # ADD CHANNEL
    # ========================================================

    def add_channel(
        self,
        channel: str,
        title: Optional[str] = None,
        url: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        channel = self.normalize_channel(
            channel
        )

        if not channel:

            raise ValueError(
                "Channel is required."
            )

        if channel_id is None:

            safe_id = (
                channel
                .replace(
                    "@",
                    "",
                )
                .replace(
                    "-",
                    "_",
                )
                .replace(
                    " ",
                    "_",
                )
            )

            channel_id = (
                f"channel_{safe_id}"
            )

        data = {
            "id": channel_id,
            "channel": channel,
            "title": (
                clean_text(title)
                or channel
            ),
            "url": (
                url
                or (
                    f"https://t.me/"
                    f"{channel.lstrip('@')}"
                    if channel.startswith("@")
                    else None
                )
            ),
            "enabled": True,
            "source": "admin",
        }

        self.channels[
            channel_id
        ] = data

        logger.info(
            "Force join channel added: %s",
            channel,
        )

        return data

    # ========================================================
    # REMOVE CHANNEL
    # ========================================================

    def remove_channel(
        self,
        channel_id: str,
    ) -> bool:

        channel_id = clean_text(
            channel_id
        )

        if channel_id not in self.channels:

            return False

        del self.channels[
            channel_id
        ]

        logger.info(
            "Force join channel removed: %s",
            channel_id,
        )

        return True

    # ========================================================
    # ENABLE
    # ========================================================

    def enable_channel(
        self,
        channel_id: str,
    ) -> bool:

        channel = self.channels.get(
            channel_id
        )

        if not channel:
            return False

        channel["enabled"] = True

        return True

    # ========================================================
    # DISABLE
    # ========================================================

    def disable_channel(
        self,
        channel_id: str,
    ) -> bool:

        channel = self.channels.get(
            channel_id
        )

        if not channel:
            return False

        channel["enabled"] = False

        return True

    # ========================================================
    # LIST
    # ========================================================

    def list_channels(
        self,
        enabled_only: bool = True,
    ) -> List[Dict[str, Any]]:

        channels = list(
            self.channels.values()
        )

        if enabled_only:

            channels = [
                channel
                for channel in channels
                if channel.get(
                    "enabled",
                    True,
                )
            ]

        return channels

    # ========================================================
    # GET CHANNEL
    # ========================================================

    def get_channel(
        self,
        channel_id: str,
    ) -> Optional[Dict[str, Any]]:

        return self.channels.get(
            str(channel_id)
        )

    # ========================================================
    # CHECK MEMBERSHIP
    # ========================================================

    async def check_channel(
        self,
        bot,
        user_id: int,
        channel: str,
    ) -> bool:

        try:

            member = await bot.get_chat_member(
                chat_id=channel,
                user_id=int(user_id),
            )

            status = str(
                member.status
            ).lower()

            # Telegram member statuses:
            #
            # creator
            # administrator
            # member
            # restricted
            #
            # left / kicked = not joined

            if status in (
                "creator",
                "administrator",
                "member",
            ):

                return True

            # Restricted user अगर Telegram के अनुसार
            # chat में member है तो उसे allow किया जा सकता है।

            if status == "restricted":

                return bool(
                    getattr(
                        member,
                        "is_member",
                        False,
                    )
                )

            return False

        except TelegramError as exc:

            logger.warning(
                (
                    "Could not check membership "
                    "for user=%s channel=%s: %s"
                ),
                user_id,
                channel,
                exc,
            )

            return False

        except Exception:

            logger.exception(
                "Membership check failed."
            )

            return False

    # ========================================================
    # CHECK ALL
    # ========================================================

    async def check_user(
        self,
        bot,
        user_id: int,
    ) -> Dict[str, Any]:

        channels = self.list_channels(
            enabled_only=True
        )

        if not channels:

            return {
                "allowed": True,
                "joined": [],
                "missing": [],
                "total": 0,
            }

        joined = []
        missing = []

        for channel in channels:

            channel_value = channel.get(
                "channel"
            )

            if not channel_value:
                continue

            is_member = (
                await self.check_channel(
                    bot,
                    user_id,
                    channel_value,
                )
            )

            if is_member:

                joined.append(
                    channel
                )

            else:

                missing.append(
                    channel
                )

        return {
            "allowed": (
                len(missing) == 0
            ),
            "joined": joined,
            "missing": missing,
            "total": len(channels),
        }

    # ========================================================
    # BUILD JOIN KEYBOARD
    # ========================================================

    def keyboard(
        self,
        missing: Optional[
            List[Dict[str, Any]]
        ] = None,
    ):

        channels = (
            missing
            if missing is not None
            else self.list_channels()
        )

        return force_join_keyboard(
            channels
        )

    # ========================================================
    # FORCE JOIN MESSAGE
    # ========================================================

    def message(
        self,
        missing: Optional[
            List[Dict[str, Any]]
        ] = None,
    ) -> str:

        channels = (
            missing
            if missing is not None
            else self.list_channels()
        )

        if not channels:

            return ""

        lines = [
            "🔐 <b>JOIN REQUIRED CHANNELS</b>",
            "",
            (
                "Bot use करने से पहले "
                "नीचे दिए गए सभी channels join करें।"
            ),
            "",
        ]

        for index, channel in enumerate(
            channels,
            start=1,
        ):

            title = channel.get(
                "title",
                channel.get(
                    "channel",
                    "Channel",
                ),
            )

            lines.append(
                f"{index}. 📢 {title}"
            )

        lines.extend(
            [
                "",
                "इसके बाद नीचे "
                "<b>VERIFY JOIN</b> button दबाएँ।",
            ]
        )

        return "\n".join(
            lines
        )

    # ========================================================
    # VERIFY FROM TELEGRAM
    # ========================================================

    async def verify(
        self,
        update: Update,
        context,
    ) -> bool:

        user = update.effective_user

        if not user:
            return False

        bot = context.bot

        result = await self.check_user(
            bot,
            user.id,
        )

        if result["allowed"]:

            if update.callback_query:

                try:

                    await update.callback_query.answer(
                        "✅ Join verification successful!",
                        show_alert=True,
                    )

                except Exception:

                    pass

            return True

        if update.callback_query:

            try:

                await update.callback_query.answer(
                    "❌ सभी required channels join करें।",
                    show_alert=True,
                )

            except Exception:

                pass

            try:

                await update.callback_query.edit_message_text(
                    self.message(
                        result["missing"]
                    ),
                    parse_mode="HTML",
                    reply_markup=self.keyboard(
                        result["missing"]
                    ),
                )

            except Exception:

                logger.debug(
                    "Could not edit force-join message.",
                    exc_info=True,
                )

            return False

        if update.effective_message:

            await update.effective_message.reply_text(
                self.message(
                    result["missing"]
                ),
                parse_mode="HTML",
                reply_markup=self.keyboard(
                    result["missing"]
                ),
            )

        return False

    # ========================================================
    # ADMIN LIST TEXT
    # ========================================================

    def admin_text(
        self,
    ) -> str:

        channels = self.list_channels(
            enabled_only=False
        )

        if not channels:

            return (
                "🔐 <b>FORCE JOIN</b>\n\n"
                "कोई channel configured नहीं है।"
            )

        lines = [
            "🔐 <b>FORCE JOIN CHANNELS</b>",
            "",
        ]

        for index, channel in enumerate(
            channels,
            start=1,
        ):

            status = (
                "🟢 ON"
                if channel.get(
                    "enabled",
                    True,
                )
                else "🔴 OFF"
            )

            lines.append(
                (
                    f"<b>{index}.</b> "
                    f"{channel.get('title')}\n"
                    f"🆔 <code>{channel.get('id')}</code>\n"
                    f"📢 {channel.get('channel')}\n"
                    f"📌 {status}"
                )
            )

            lines.append("")

        return "\n".join(
            lines
        )

    # ========================================================
    # ADMIN ADD
    # ========================================================

    async def admin_add(
        self,
        channel: str,
        title: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:

        return self.add_channel(
            channel=channel,
            title=title,
            url=url,
        )

    # ========================================================
    # ADMIN REMOVE
    # ========================================================

    async def admin_remove(
        self,
        channel_id: str,
    ) -> bool:

        return self.remove_channel(
            channel_id
        )


# ============================================================
# GLOBAL SERVICE
# ============================================================

force_join_service = (
    ForceJoinService()
)


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def check_force_join(
    bot,
    user_id: int,
) -> Dict[str, Any]:

    return await force_join_service.check_user(
        bot,
        user_id,
    )


async def verify_force_join(
    update: Update,
    context,
) -> bool:

    return await force_join_service.verify(
        update,
        context,
    )


def add_force_join_channel(
    channel: str,
    title: Optional[str] = None,
    url: Optional[str] = None,
):

    return force_join_service.add_channel(
        channel,
        title=title,
        url=url,
    )


def remove_force_join_channel(
    channel_id: str,
):

    return force_join_service.remove_channel(
        channel_id
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "ForceJoinService",
    "force_join_service",
    "check_force_join",
    "verify_force_join",
    "add_force_join_channel",
    "remove_force_join_channel",
]

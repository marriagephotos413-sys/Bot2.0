import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from telegram import Bot, Update
from telegram.error import TelegramError

from app.config import CONFIG
from app.helpers import clean_text
from app.keyboards import channels_keyboard


logger = logging.getLogger(
    "telegram-test-series-bot.channels"
)


# ============================================================
# CHANNEL SERVICE
# ============================================================

class ChannelService:
    """
    Bot channel management.

    Channels:
    - Database Channel
    - Payment Verification Channel
    - User Activity Channel
    - Paid User Channel
    - Force Join Channels

    Features:
    - Add channel
    - Remove channel
    - Enable / disable
    - Channel info
    - Telegram channel validation
    - Message destination management
    """

    CHANNEL_TYPES = {
        "database": "DATABASE_CHANNEL_ID",
        "payment": "PAYMENT_VERIFY_CHANNEL_ID",
        "activity": "USER_ACTIVITY_CHANNEL_ID",
        "paid_user": "PAID_USER_CHANNEL_ID",
    }

    def __init__(self):

        self.channels: Dict[
            str,
            Dict[str, Any]
        ] = {}

        self._load_environment_channels()

    # ========================================================
    # LOAD ENV CHANNELS
    # ========================================================

    def _load_environment_channels(self):

        for channel_type, env_name in (
            self.CHANNEL_TYPES.items()
        ):

            value = getattr(
                CONFIG,
                env_name,
                None,
            )

            if value in (
                None,
                "",
                0,
                "0",
            ):

                continue

            self.channels[
                channel_type
            ] = {
                "type": channel_type,
                "channel_id": value,
                "title": channel_type.replace(
                    "_",
                    " "
                ).title(),
                "enabled": True,
                "source": "environment",
                "updated_at": datetime.now(
                    timezone.utc
                ),
            }

    # ========================================================
    # NORMALIZE ID
    # ========================================================

    @staticmethod
    def normalize_channel_id(
        value: Any,
    ) -> Any:

        if value is None:
            return None

        value = str(
            value
        ).strip()

        if not value:
            return None

        # Telegram numeric channel IDs
        if value.lstrip("-").isdigit():

            try:

                return int(
                    value
                )

            except ValueError:

                return value

        # @channelusername
        if value.startswith("@"):

            return value

        # t.me URL
        if "t.me/" in value:

            return (
                "@"
                + value.split(
                    "t.me/",
                    1,
                )[1].strip(
                    "/"
                )
            )

        return value

    # ========================================================
    # ADD / SET CHANNEL
    # ========================================================

    def set_channel(
        self,
        channel_type: str,
        channel_id: Any,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:

        channel_type = clean_text(
            channel_type
        ).lower()

        if channel_type not in self.CHANNEL_TYPES:

            raise ValueError(
                (
                    "Invalid channel type. "
                    f"Allowed: "
                    f"{', '.join(self.CHANNEL_TYPES)}"
                )
            )

        channel_id = (
            self.normalize_channel_id(
                channel_id
            )
        )

        if channel_id is None:

            raise ValueError(
                "Channel ID is required."
            )

        data = {
            "type": channel_type,
            "channel_id": channel_id,
            "title": (
                clean_text(title)
                or channel_type.replace(
                    "_",
                    " "
                ).title()
            ),
            "enabled": True,
            "source": "admin",
            "updated_at": datetime.now(
                timezone.utc
            ),
        }

        self.channels[
            channel_type
        ] = data

        logger.info(
            (
                "Channel configured: "
                "type=%s id=%s"
            ),
            channel_type,
            channel_id,
        )

        return data

    # ========================================================
    # GET CHANNEL
    # ========================================================

    def get_channel(
        self,
        channel_type: str,
    ) -> Optional[Dict[str, Any]]:

        return self.channels.get(
            str(
                channel_type
            ).lower()
        )

    # ========================================================
    # REMOVE CHANNEL
    # ========================================================

    def remove_channel(
        self,
        channel_type: str,
    ) -> bool:

        channel_type = str(
            channel_type
        ).lower()

        if channel_type not in self.channels:

            return False

        del self.channels[
            channel_type
        ]

        logger.info(
            "Channel removed: %s",
            channel_type,
        )

        return True

    # ========================================================
    # ENABLE
    # ========================================================

    def enable_channel(
        self,
        channel_type: str,
    ) -> bool:

        channel = self.get_channel(
            channel_type
        )

        if not channel:

            return False

        channel["enabled"] = True
        channel["updated_at"] = datetime.now(
            timezone.utc
        )

        return True

    # ========================================================
    # DISABLE
    # ========================================================

    def disable_channel(
        self,
        channel_type: str,
    ) -> bool:

        channel = self.get_channel(
            channel_type
        )

        if not channel:

            return False

        channel["enabled"] = False
        channel["updated_at"] = datetime.now(
            timezone.utc
        )

        return True

    # ========================================================
    # LIST
    # ========================================================

    def list_channels(
        self,
        enabled_only: bool = False,
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
    # GET DESTINATION
    # ========================================================

    def destination(
        self,
        channel_type: str,
    ) -> Optional[Any]:

        channel = self.get_channel(
            channel_type
        )

        if not channel:

            return None

        if not channel.get(
            "enabled",
            True,
        ):

            return None

        return channel.get(
            "channel_id"
        )

    # ========================================================
    # VALIDATE TELEGRAM CHANNEL
    # ========================================================

    async def validate_channel(
        self,
        bot: Bot,
        channel_type: str,
    ) -> Dict[str, Any]:

        channel = self.get_channel(
            channel_type
        )

        if not channel:

            return {
                "valid": False,
                "type": channel_type,
                "reason": "Channel not configured.",
            }

        channel_id = channel.get(
            "channel_id"
        )

        try:

            chat = await bot.get_chat(
                chat_id=channel_id
            )

            return {
                "valid": True,
                "type": channel_type,
                "channel_id": channel_id,
                "id": chat.id,
                "title": chat.title,
                "username": chat.username,
                "type": chat.type,
                "invite_link": getattr(
                    chat,
                    "invite_link",
                    None,
                ),
            }

        except TelegramError as exc:

            logger.warning(
                (
                    "Channel validation failed "
                    "type=%s id=%s error=%s"
                ),
                channel_type,
                channel_id,
                exc,
            )

            return {
                "valid": False,
                "type": channel_type,
                "channel_id": channel_id,
                "reason": str(exc),
            }

        except Exception as exc:

            logger.exception(
                "Unexpected channel validation error."
            )

            return {
                "valid": False,
                "type": channel_type,
                "channel_id": channel_id,
                "reason": str(exc),
            }

    # ========================================================
    # ADMIN TEXT
    # ========================================================

    def admin_text(
        self,
    ) -> str:

        channels = self.list_channels()

        if not channels:

            return (
                "📢 <b>BOT CHANNELS</b>\n\n"
                "अभी कोई channel configured नहीं है।"
            )

        lines = [
            "📢 <b>BOT CHANNELS</b>",
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

            channel_type = channel.get(
                "type",
                "unknown",
            )

            title = channel.get(
                "title",
                channel_type,
            )

            channel_id = channel.get(
                "channel_id"
            )

            lines.append(
                (
                    f"<b>{index}. {title}</b>\n"
                    f"🧩 Type: "
                    f"<code>{channel_type}</code>\n"
                    f"🆔 ID: "
                    f"<code>{channel_id}</code>\n"
                    f"📌 Status: {status}"
                )
            )

            lines.append("")

        return "\n".join(
            lines
        )

    # ========================================================
    # USER DISPLAY
    # ========================================================

    def user_text(
        self,
    ) -> str:

        channels = self.list_channels(
            enabled_only=True
        )

        if not channels:

            return (
                "📢 अभी कोई channel available नहीं है।"
            )

        lines = [
            "📢 <b>OUR CHANNELS</b>",
            "",
        ]

        for channel in channels:

            title = channel.get(
                "title",
                "Channel",
            )

            channel_id = channel.get(
                "channel_id"
            )

            if isinstance(
                channel_id,
                str,
            ) and channel_id.startswith(
                "@"
            ):

                link = (
                    f"https://t.me/"
                    f"{channel_id[1:]}"
                )

                lines.append(
                    f"📢 <a href=\"{link}\">"
                    f"{title}</a>"
                )

            else:

                lines.append(
                    f"📢 {title}"
                )

        return "\n".join(
            lines
        )

    # ========================================================
    # TELEGRAM HANDLER
    # ========================================================

    async def show(
        self,
        update: Update,
        context,
    ):

        try:

            text = self.user_text()

            keyboard = channels_keyboard(
                self.list_channels(
                    enabled_only=True
                )
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
                    disable_web_page_preview=True,
                    reply_markup=keyboard,
                )

                return

            if update.effective_message:

                await update.effective_message.reply_text(
                    text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=keyboard,
                )

        except Exception:

            logger.exception(
                "Failed to show channels."
            )

    # ========================================================
    # ADMIN SET
    # ========================================================

    async def admin_set(
        self,
        channel_type: str,
        channel_id: Any,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:

        return self.set_channel(
            channel_type=channel_type,
            channel_id=channel_id,
            title=title,
        )

    # ========================================================
    # ADMIN REMOVE
    # ========================================================

    async def admin_remove(
        self,
        channel_type: str,
    ) -> bool:

        return self.remove_channel(
            channel_type
        )


# ============================================================
# GLOBAL INSTANCE
# ============================================================

channel_service = ChannelService()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def set_bot_channel(
    channel_type: str,
    channel_id: Any,
    title: Optional[str] = None,
):

    return channel_service.set_channel(
        channel_type,
        channel_id,
        title=title,
    )


def remove_bot_channel(
    channel_type: str,
):

    return channel_service.remove_channel(
        channel_type
    )


def get_bot_channel(
    channel_type: str,
):

    return channel_service.get_channel(
        channel_type
    )


def get_channel_destination(
    channel_type: str,
):

    return channel_service.destination(
        channel_type
    )


async def validate_bot_channel(
    bot: Bot,
    channel_type: str,
):

    return await channel_service.validate_channel(
        bot,
        channel_type,
    )


# ============================================================
# CHANNEL SHORTCUTS
# ============================================================

def database_channel():
    return channel_service.destination(
        "database"
    )


def payment_channel():
    return channel_service.destination(
        "payment"
    )


def activity_channel():
    return channel_service.destination(
        "activity"
    )


def paid_user_channel():
    return channel_service.destination(
        "paid_user"
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "ChannelService",
    "channel_service",
    "set_bot_channel",
    "remove_bot_channel",
    "get_bot_channel",
    "get_channel_destination",
    "validate_bot_channel",
    "database_channel",
    "payment_channel",
    "activity_channel",
    "paid_user_channel",
]

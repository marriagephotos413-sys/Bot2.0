import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from telegram import Update

from app.config import CONFIG
from app.helpers import clean_text
from app.keyboards import welcome_keyboard


logger = logging.getLogger(
    "telegram-test-series-bot.welcome"
)


# ============================================================
# WELCOME SERVICE
# ============================================================

class WelcomeService:
    """
    Welcome message management.

    Features:
    - Custom welcome text
    - Welcome link
    - Welcome button
    - Text + link together
    - Enable / disable welcome
    - Admin update
    - User-specific welcome
    """

    DEFAULT_TEXT = (
        "👋 <b>WELCOME TO TEST SERIES BOT</b>\n\n"
        "📚 यहाँ आपको SSC, RRB, UPSC और अन्य "
        "competitive exams के Mock Tests और PYQs मिलेंगे।\n\n"
        "👇 नीचे दिए गए options से शुरुआत करें।"
    )

    def __init__(self):

        self.enabled = True

        self.text = (
            getattr(
                CONFIG,
                "WELCOME_MESSAGE",
                None,
            )
            or self.DEFAULT_TEXT
        )

        self.link = (
            getattr(
                CONFIG,
                "WELCOME_LINK",
                None,
            )
            or ""
        )

        self.button_text = (
            getattr(
                CONFIG,
                "WELCOME_BUTTON_TEXT",
                None,
            )
            or "🚀 Start Test Series"
        )

        self.updated_at = datetime.now(
            timezone.utc
        )

    # ========================================================
    # GET SETTINGS
    # ========================================================

    def get_settings(
        self,
    ) -> Dict[str, Any]:

        return {
            "enabled": self.enabled,
            "text": self.text,
            "link": self.link,
            "button_text": self.button_text,
            "updated_at": self.updated_at,
        }

    # ========================================================
    # SET MESSAGE
    # ========================================================

    def set_message(
        self,
        text: str,
    ) -> Dict[str, Any]:

        text = clean_text(
            text
        )

        if not text:

            raise ValueError(
                "Welcome message empty नहीं हो सकता।"
            )

        self.text = text

        self.updated_at = datetime.now(
            timezone.utc
        )

        logger.info(
            "Welcome message updated."
        )

        return self.get_settings()

    # ========================================================
    # SET LINK
    # ========================================================

    def set_link(
        self,
        link: str,
        button_text: Optional[str] = None,
    ) -> Dict[str, Any]:

        link = clean_text(
            link
        )

        if link and not (
            link.startswith(
                "https://"
            )
            or link.startswith(
                "http://"
            )
        ):

            raise ValueError(
                "Link http:// या https:// से शुरू होना चाहिए।"
            )

        self.link = link

        if button_text is not None:

            button_text = clean_text(
                button_text
            )

            if button_text:

                self.button_text = (
                    button_text
                )

        self.updated_at = datetime.now(
            timezone.utc
        )

        logger.info(
            "Welcome link updated."
        )

        return self.get_settings()

    # ========================================================
    # SET BOTH
    # ========================================================

    def set_both(
        self,
        text: str,
        link: str,
        button_text: Optional[str] = None,
    ) -> Dict[str, Any]:

        self.set_message(
            text
        )

        self.set_link(
            link,
            button_text=button_text,
        )

        return self.get_settings()

    # ========================================================
    # ENABLE
    # ========================================================

    def enable(self) -> None:

        self.enabled = True

        self.updated_at = datetime.now(
            timezone.utc
        )

        logger.info(
            "Welcome message enabled."
        )

    # ========================================================
    # DISABLE
    # ========================================================

    def disable(self) -> None:

        self.enabled = False

        self.updated_at = datetime.now(
            timezone.utc
        )

        logger.info(
            "Welcome message disabled."
        )

    # ========================================================
    # RESET DEFAULT
    # ========================================================

    def reset(self) -> Dict[str, Any]:

        self.enabled = True
        self.text = self.DEFAULT_TEXT
        self.link = ""
        self.button_text = (
            "🚀 Start Test Series"
        )

        self.updated_at = datetime.now(
            timezone.utc
        )

        logger.info(
            "Welcome settings reset."
        )

        return self.get_settings()

    # ========================================================
    # BUILD TEXT
    # ========================================================

    def build_text(
        self,
        user=None,
    ) -> str:

        text = self.text

        if user:

            first_name = getattr(
                user,
                "first_name",
                None,
            )

            username = getattr(
                user,
                "username",
                None,
            )

            if first_name:

                text = text.replace(
                    "{name}",
                    str(
                        first_name
                    ),
                )

            else:

                text = text.replace(
                    "{name}",
                    "Student",
                )

            if username:

                text = text.replace(
                    "{username}",
                    f"@{username}",
                )

            else:

                text = text.replace(
                    "{username}",
                    "",
                )

            text = text.replace(
                "{user_id}",
                str(
                    getattr(
                        user,
                        "id",
                        "",
                    )
                ),
            )

        return text

    # ========================================================
    # BUILD KEYBOARD
    # ========================================================

    def build_keyboard(self):

        if not self.link:

            return welcome_keyboard(
                []
            )

        return welcome_keyboard(
            [
                {
                    "text": self.button_text,
                    "url": self.link,
                }
            ]
        )

    # ========================================================
    # SEND WELCOME
    # ========================================================

    async def send(
        self,
        update: Update,
        context,
        *,
        user=None,
    ) -> bool:

        if not self.enabled:

            return False

        message = (
            update.effective_message
        )

        if not message:

            return False

        user = (
            user
            or update.effective_user
        )

        text = self.build_text(
            user
        )

        keyboard = (
            self.build_keyboard()
        )

        try:

            await message.reply_text(
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=keyboard,
            )

            return True

        except Exception:

            logger.exception(
                "Failed to send welcome message."
            )

            return False

    # ========================================================
    # PREVIEW
    # ========================================================

    def preview(
        self,
    ) -> str:

        return (
            "👁 <b>WELCOME PREVIEW</b>\n\n"
            f"{self.text}"
        )

    # ========================================================
    # ADMIN TEXT
    # ========================================================

    def admin_text(
        self,
    ) -> str:

        status = (
            "🟢 ENABLED"
            if self.enabled
            else "🔴 DISABLED"
        )

        link = (
            self.link
            if self.link
            else "Not configured"
        )

        return (
            "👋 <b>WELCOME SETTINGS</b>\n\n"
            f"📌 Status: <b>{status}</b>\n"
            "\n"
            "📝 <b>Message:</b>\n"
            f"{self.text}\n"
            "\n"
            f"🔗 Link: <code>{link}</code>\n"
            f"🔘 Button: "
            f"<b>{self.button_text}</b>"
        )

    # ========================================================
    # ADMIN SEND PREVIEW
    # ========================================================

    async def show_admin(
        self,
        update: Update,
        context,
    ):

        text = self.admin_text()

        try:

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
                )

                return

            if update.effective_message:

                await update.effective_message.reply_text(
                    text,
                    parse_mode="HTML",
                )

        except Exception:

            logger.exception(
                "Failed to show welcome settings."
            )


# ============================================================
# GLOBAL INSTANCE
# ============================================================

welcome_service = WelcomeService()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def set_welcome_message(
    text: str,
):

    return welcome_service.set_message(
        text
    )


def set_welcome_link(
    link: str,
    button_text: Optional[str] = None,
):

    return welcome_service.set_link(
        link,
        button_text=button_text,
    )


def set_welcome(
    text: str,
    link: str,
    button_text: Optional[str] = None,
):

    return welcome_service.set_both(
        text,
        link,
        button_text,
    )


def enable_welcome():

    welcome_service.enable()


def disable_welcome():

    welcome_service.disable()


def reset_welcome():

    return welcome_service.reset()


# ============================================================
# TELEGRAM HANDLER
# ============================================================

async def send_welcome(
    update: Update,
    context,
):

    return await welcome_service.send(
        update,
        context,
    )


async def show_welcome_settings(
    update: Update,
    context,
):

    await welcome_service.show_admin(
        update,
        context,
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "WelcomeService",
    "welcome_service",
    "set_welcome_message",
    "set_welcome_link",
    "set_welcome",
    "enable_welcome",
    "disable_welcome",
    "reset_welcome",
    "send_welcome",
    "show_welcome_settings",
]

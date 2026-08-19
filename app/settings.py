import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.config import CONFIG
from app.helpers import clean_text


logger = logging.getLogger(
    "telegram-test-series-bot.settings"
)


# ============================================================
# SETTINGS SERVICE
# ============================================================

class SettingsService:
    """
    Central bot settings manager.

    Settings handled here:
    - Bot name
    - Bot username
    - Support username
    - Admin contact
    - Welcome message state
    - Free-trial state
    - Maintenance mode
    - Test extraction enable/disable
    - Test upload enable/disable
    - Paid-first priority
    - Queue/load protection
    - User wait message
    - GitHub test source
    - Database channel
    - Payment verification channel
    - Activity channels

    IMPORTANT:
    Test JSON MongoDB में store नहीं होता।
    Actual test JSON GitHub की tcs.html में रहेगा।
    MongoDB केवल users/settings/metadata/statistics आदि
    के लिए use होगा।
    """

    # ========================================================
    # DEFAULT SETTINGS
    # ========================================================

    DEFAULTS = {
        "bot_name": "Test Series Bot",

        "support_username": "",

        "admin_contact": "",

        "maintenance_mode": False,

        "test_extraction_enabled": True,

        "test_upload_enabled": True,

        "paid_first_priority": True,

        "load_protection_enabled": True,

        "user_wait_message": (
            "⏳ <b>Please Wait...</b>\n\n"
            "Server पर अभी load ज्यादा है।\n"
            "आपका request queue में लगा दिया गया है।\n\n"
            "कृपया थोड़ी देर प्रतीक्षा करें।"
        ),

        "max_concurrent_jobs": 5,

        "max_user_concurrent_jobs": 1,

        "upload_batch_size": 5,

        "extraction_batch_size": 10,

        "maintenance_message": (
            "🛠 <b>BOT MAINTENANCE</b>\n\n"
            "अभी bot maintenance में है।\n"
            "कृपया कुछ समय बाद दोबारा प्रयास करें।"
        ),

        "paid_priority_message": (
            "💎 आपका request Premium Priority Queue "
            "में process किया जा रहा है।"
        ),

        "github_branch": "main",

        "github_test_file": "tcs.html",

        "auto_github_update": True,

        "live_progress_enabled": True,

        "failed_upload_retry_enabled": True,

        "auto_backup_enabled": False,

        "updated_at": None,
    }

    # ========================================================
    # INIT
    # ========================================================

    def __init__(self):

        self.settings: Dict[
            str,
            Any
        ] = dict(
            self.DEFAULTS
        )

        self._load_environment()

    # ========================================================
    # ENVIRONMENT
    # ========================================================

    def _load_environment(self):

        env_map = {
            "bot_name": "BOT_NAME",
            "support_username": "SUPPORT_USERNAME",
            "admin_contact": "ADMIN_CONTACT",
            "user_wait_message": "USER_WAIT_MESSAGE",
            "maintenance_message": "MAINTENANCE_MESSAGE",
            "paid_priority_message": "PAID_PRIORITY_MESSAGE",
            "github_branch": "GITHUB_BRANCH",
            "github_test_file": "GITHUB_TEST_FILE",
        }

        for setting_name, env_name in env_map.items():

            value = os.getenv(
                env_name
            )

            if value is None:
                continue

            value = clean_text(
                value
            )

            if value:

                self.settings[
                    setting_name
                ] = value

        # ----------------------------------------------------
        # Boolean ENV
        # ----------------------------------------------------

        boolean_env = {
            "maintenance_mode": "MAINTENANCE_MODE",
            "test_extraction_enabled": "TEST_EXTRACTION_ENABLED",
            "test_upload_enabled": "TEST_UPLOAD_ENABLED",
            "paid_first_priority": "PAID_FIRST_PRIORITY",
            "load_protection_enabled": "LOAD_PROTECTION_ENABLED",
            "auto_github_update": "AUTO_GITHUB_UPDATE",
            "live_progress_enabled": "LIVE_PROGRESS_ENABLED",
            "failed_upload_retry_enabled": "FAILED_UPLOAD_RETRY_ENABLED",
            "auto_backup_enabled": "AUTO_BACKUP_ENABLED",
        }

        for setting_name, env_name in boolean_env.items():

            value = os.getenv(
                env_name
            )

            if value is None:
                continue

            self.settings[
                setting_name
            ] = self._to_bool(
                value
            )

        # ----------------------------------------------------
        # Integer ENV
        # ----------------------------------------------------

        integer_env = {
            "max_concurrent_jobs": "MAX_CONCURRENT_JOBS",
            "max_user_concurrent_jobs": "MAX_USER_CONCURRENT_JOBS",
            "upload_batch_size": "UPLOAD_BATCH_SIZE",
            "extraction_batch_size": "EXTRACTION_BATCH_SIZE",
        }

        for setting_name, env_name in integer_env.items():

            value = os.getenv(
                env_name
            )

            if value is None:
                continue

            try:

                self.settings[
                    setting_name
                ] = max(
                    1,
                    int(value),
                )

            except ValueError:

                logger.warning(
                    (
                        "Invalid integer environment "
                        "value: %s"
                    ),
                    env_name,
                )

    # ========================================================
    # BOOL
    # ========================================================

    @staticmethod
    def _to_bool(
        value: Any,
    ) -> bool:

        if isinstance(
            value,
            bool,
        ):

            return value

        return str(
            value
        ).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
            "enabled",
        )

    # ========================================================
    # GET
    # ========================================================

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:

        return self.settings.get(
            key,
            default,
        )

    # ========================================================
    # SET
    # ========================================================

    def set(
        self,
        key: str,
        value: Any,
    ) -> Any:

        if not key:

            raise ValueError(
                "Setting key required."
            )

        self.settings[
            str(key)
        ] = value

        self.settings[
            "updated_at"
        ] = datetime.now(
            timezone.utc
        )

        logger.info(
            "Setting updated: %s",
            key,
        )

        return value

    # ========================================================
    # UPDATE MULTIPLE
    # ========================================================

    def update(
        self,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:

        for key, value in values.items():

            self.set(
                key,
                value,
            )

        return self.all()

    # ========================================================
    # GET ALL
    # ========================================================

    def all(
        self,
    ) -> Dict[str, Any]:

        return dict(
            self.settings
        )

    # ========================================================
    # RESET
    # ========================================================

    def reset(
        self,
        key: Optional[str] = None,
    ):

        if key:

            if key in self.DEFAULTS:

                self.settings[
                    key
                ] = self.DEFAULTS[
                    key
                ]

            else:

                raise KeyError(
                    f"Unknown setting: {key}"
                )

        else:

            self.settings = dict(
                self.DEFAULTS
            )

            self._load_environment()

        self.settings[
            "updated_at"
        ] = datetime.now(
            timezone.utc
        )

        return self.all()

    # ========================================================
    # MAINTENANCE
    # ========================================================

    def maintenance_enabled(
        self,
    ) -> bool:

        return bool(
            self.get(
                "maintenance_mode",
                False,
            )
        )

    def enable_maintenance(
        self,
        message: Optional[str] = None,
    ):

        self.set(
            "maintenance_mode",
            True,
        )

        if message:

            self.set(
                "maintenance_message",
                message,
            )

    def disable_maintenance(
        self,
    ):

        self.set(
            "maintenance_mode",
            False,
        )

    def maintenance_message(
        self,
    ) -> str:

        return str(
            self.get(
                "maintenance_message",
                self.DEFAULTS[
                    "maintenance_message"
                ],
            )
        )

    # ========================================================
    # TEST EXTRACTION
    # ========================================================

    def extraction_enabled(
        self,
    ) -> bool:

        return bool(
            self.get(
                "test_extraction_enabled",
                True,
            )
        )

    def enable_extraction(
        self,
    ):

        self.set(
            "test_extraction_enabled",
            True,
        )

    def disable_extraction(
        self,
    ):

        self.set(
            "test_extraction_enabled",
            False,
        )

    # ========================================================
    # TEST UPLOAD
    # ========================================================

    def upload_enabled(
        self,
    ) -> bool:

        return bool(
            self.get(
                "test_upload_enabled",
                True,
            )
        )

    def enable_upload(
        self,
    ):

        self.set(
            "test_upload_enabled",
            True,
        )

    def disable_upload(
        self,
    ):

        self.set(
            "test_upload_enabled",
            False,
        )

    # ========================================================
    # PAID PRIORITY
    # ========================================================

    def paid_first(
        self,
    ) -> bool:

        return bool(
            self.get(
                "paid_first_priority",
                True,
            )
        )

    def enable_paid_priority(
        self,
    ):

        self.set(
            "paid_first_priority",
            True,
        )

    def disable_paid_priority(
        self,
    ):

        self.set(
            "paid_first_priority",
            False,
        )

    # ========================================================
    # LOAD PROTECTION
    # ========================================================

    def load_protection(
        self,
    ) -> bool:

        return bool(
            self.get(
                "load_protection_enabled",
                True,
            )
        )

    def max_jobs(
        self,
    ) -> int:

        return max(
            1,
            int(
                self.get(
                    "max_concurrent_jobs",
                    5,
                )
            ),
        )

    def max_user_jobs(
        self,
    ) -> int:

        return max(
            1,
            int(
                self.get(
                    "max_user_concurrent_jobs",
                    1,
                )
            ),
        )

    # ========================================================
    # WAIT MESSAGE
    # ========================================================

    def wait_message(
        self,
    ) -> str:

        return str(
            self.get(
                "user_wait_message",
                self.DEFAULTS[
                    "user_wait_message"
                ],
            )
        )

    def set_wait_message(
        self,
        message: str,
    ):

        message = clean_text(
            message
        )

        if not message:

            raise ValueError(
                "Wait message empty नहीं हो सकता।"
            )

        return self.set(
            "user_wait_message",
            message,
        )

    # ========================================================
    # LIVE PROGRESS
    # ========================================================

    def live_progress(
        self,
    ) -> bool:

        return bool(
            self.get(
                "live_progress_enabled",
                True,
            )
        )

    def enable_live_progress(
        self,
    ):

        self.set(
            "live_progress_enabled",
            True,
        )

    def disable_live_progress(
        self,
    ):

        self.set(
            "live_progress_enabled",
            False,
        )

    # ========================================================
    # RETRY
    # ========================================================

    def retry_enabled(
        self,
    ) -> bool:

        return bool(
            self.get(
                "failed_upload_retry_enabled",
                True,
            )
        )

    def enable_retry(
        self,
    ):

        self.set(
            "failed_upload_retry_enabled",
            True,
        )

    def disable_retry(
        self,
    ):

        self.set(
            "failed_upload_retry_enabled",
            False,
        )

    # ========================================================
    # GITHUB
    # ========================================================

    def github_branch(
        self,
    ) -> str:

        return str(
            self.get(
                "github_branch",
                "main",
            )
        )

    def github_test_file(
        self,
    ) -> str:

        return str(
            self.get(
                "github_test_file",
                "tcs.html",
            )
        )

    def github_auto_update(
        self,
    ) -> bool:

        return bool(
            self.get(
                "auto_github_update",
                True,
            )
        )

    # ========================================================
    # BOT INFO
    # ========================================================

    def bot_name(
        self,
    ) -> str:

        return str(
            self.get(
                "bot_name",
                "Test Series Bot",
            )
        )

    def support_username(
        self,
    ) -> str:

        return str(
            self.get(
                "support_username",
                "",
            )
        )

    def admin_contact(
        self,
    ) -> str:

        return str(
            self.get(
                "admin_contact",
                "",
            )
        )

    # ========================================================
    # ADMIN TEXT
    # ========================================================

    def admin_text(
        self,
    ) -> str:

        maintenance = (
            "🟢 OFF"
            if not self.maintenance_enabled()
            else "🔴 ON"
        )

        extraction = (
            "🟢 ON"
            if self.extraction_enabled()
            else "🔴 OFF"
        )

        upload = (
            "🟢 ON"
            if self.upload_enabled()
            else "🔴 OFF"
        )

        paid_priority = (
            "🟢 ON"
            if self.paid_first()
            else "🔴 OFF"
        )

        load_protection = (
            "🟢 ON"
            if self.load_protection()
            else "🔴 OFF"
        )

        live_progress = (
            "🟢 ON"
            if self.live_progress()
            else "🔴 OFF"
        )

        retry = (
            "🟢 ON"
            if self.retry_enabled()
            else "🔴 OFF"
        )

        github_update = (
            "🟢 ON"
            if self.github_auto_update()
            else "🔴 OFF"
        )

        return (
            "⚙️ <b>BOT SETTINGS</b>\n"
            "\n"
            f"🤖 Bot: "
            f"<b>{self.bot_name()}</b>\n"
            f"🛠 Maintenance: "
            f"<b>{maintenance}</b>\n"
            f"📥 Test Extraction: "
            f"<b>{extraction}</b>\n"
            f"📤 Test Upload: "
            f"<b>{upload}</b>\n"
            f"💎 Paid First: "
            f"<b>{paid_priority}</b>\n"
            f"🛡 Load Protection: "
            f"<b>{load_protection}</b>\n"
            f"📊 Live Progress: "
            f"<b>{live_progress}</b>\n"
            f"🔁 Failed Retry: "
            f"<b>{retry}</b>\n"
            "\n"
            "⚡ <b>QUEUE</b>\n"
            f"Max Jobs: "
            f"<b>{self.max_jobs()}</b>\n"
            f"Per User: "
            f"<b>{self.max_user_jobs()}</b>\n"
            "\n"
            "🐙 <b>GITHUB</b>\n"
            f"Branch: "
            f"<code>{self.github_branch()}</code>\n"
            f"Test File: "
            f"<code>{self.github_test_file()}</code>\n"
            f"Auto Update: "
            f"<b>{github_update}</b>"
        )

    # ========================================================
    # USER WAIT TEXT
    # ========================================================

    def build_wait_message(
        self,
        paid_user: bool = False,
    ) -> str:

        if paid_user and self.paid_first():

            return (
                "💎 <b>PREMIUM PRIORITY</b>\n\n"
                f"{self.get('paid_priority_message')}"
            )

        return self.wait_message()

    # ========================================================
    # SNAPSHOT
    # ========================================================

    def snapshot(
        self,
    ) -> Dict[str, Any]:

        return {
            "settings": self.all(),
            "created_at": datetime.now(
                timezone.utc
            ),
        }


# ============================================================
# GLOBAL INSTANCE
# ============================================================

settings_service = SettingsService()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def get_setting(
    key: str,
    default: Any = None,
):

    return settings_service.get(
        key,
        default,
    )


def set_setting(
    key: str,
    value: Any,
):

    return settings_service.set(
        key,
        value,
    )


def get_all_settings():

    return settings_service.all()


def is_maintenance():

    return settings_service.maintenance_enabled()


def is_extraction_enabled():

    return settings_service.extraction_enabled()


def is_upload_enabled():

    return settings_service.upload_enabled()


def paid_first_enabled():

    return settings_service.paid_first()


def load_protection_enabled():

    return settings_service.load_protection()


def live_progress_enabled():

    return settings_service.live_progress()


def retry_enabled():

    return settings_service.retry_enabled()


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "SettingsService",
    "settings_service",
    "get_setting",
    "set_setting",
    "get_all_settings",
    "is_maintenance",
    "is_extraction_enabled",
    "is_upload_enabled",
    "paid_first_enabled",
    "load_protection_enabled",
    "live_progress_enabled",
    "retry_enabled",
]

import os
from typing import List


# ============================================================
# ENV HELPERS
# ============================================================

def _get_list(
    value: str,
) -> List[str]:

    if not value:
        return []

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def _get_int(
    value: str,
    default: int = 0,
) -> int:

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_bool(
    value: str,
    default: bool = False,
) -> bool:

    if value is None:
        return default

    return str(value).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


# ============================================================
# CONFIG
# ============================================================

class Config:
    """
    Central application configuration.

    Secrets हमेशा environment variables से लिए जाते हैं।

    IMPORTANT:
    -------------------------------
    Old code:
        CONFIG.MONGO_URL

    New/other code:
        CONFIG.mongo_url

    दोनों supported हैं।
    """

    # ========================================================
    # TELEGRAM
    # ========================================================

    BOT_TOKEN = os.getenv(
        "BOT_TOKEN",
        "",
    ).strip()

    API_ID = _get_int(
        os.getenv(
            "API_ID",
            "0",
        ),
        0,
    )

    API_HASH = os.getenv(
        "API_HASH",
        "",
    ).strip()

    # ========================================================
    # MONGODB
    # ========================================================

    MONGO_URL = os.getenv(
        "MONGO_URL",
        "",
    ).strip()

    MONGO_DATABASE = os.getenv(
        "MONGO_DATABASE",
        "telegram_test_bot",
    ).strip() or "telegram_test_bot"

    # ========================================================
    # ADMIN
    # ========================================================

    ADMIN_IDS = [
        int(user_id)
        for user_id in _get_list(
            os.getenv(
                "ADMIN_IDS",
                "",
            )
        )
        if user_id.isdigit()
    ]

    # ========================================================
    # GITHUB
    # ========================================================
    #
    # GitHub अब startup के लिए REQUIRED नहीं है.
    #
    # TCS में JSON embedded/self-contained रखा जा सकता है.
    #
    # अगर future में GitHub integration enable करना हो
    # तो values यहाँ से मिल जाएंगी.
    # ========================================================

    GITHUB_TOKEN = os.getenv(
        "GITHUB_TOKEN",
        "",
    ).strip()

    GITHUB_OWNER = os.getenv(
        "GITHUB_OWNER",
        "",
    ).strip()

    GITHUB_REPO = os.getenv(
        "GITHUB_REPO",
        "",
    ).strip()

    GITHUB_BRANCH = os.getenv(
        "GITHUB_BRANCH",
        "main",
    ).strip() or "main"

    GITHUB_TEST_FILE = os.getenv(
        "GITHUB_TEST_FILE",
        "tcs.html",
    ).strip() or "tcs.html"

    # ========================================================
    # CHANNELS
    # ========================================================
    #
    # इन्हें ENV से भी दिया जा सकता है,
    # लेकिन bot/MongoDB commands से भी manage किया जा सकता है.
    # ========================================================

    DATABASE_CHANNEL_ID = _get_int(
        os.getenv(
            "DATABASE_CHANNEL_ID",
            "0",
        ),
        0,
    )

    PAYMENT_VERIFY_CHANNEL_ID = _get_int(
        os.getenv(
            "PAYMENT_VERIFY_CHANNEL_ID",
            "0",
        ),
        0,
    )

    USER_ACTIVITY_CHANNEL_ID = _get_int(
        os.getenv(
            "USER_ACTIVITY_CHANNEL_ID",
            "0",
        ),
        0,
    )

    PAID_USER_CHANNEL_ID = _get_int(
        os.getenv(
            "PAID_USER_CHANNEL_ID",
            "0",
        ),
        0,
    )

    FORCE_JOIN_CHANNELS = _get_list(
        os.getenv(
            "FORCE_JOIN_CHANNELS",
            "",
        )
    )

    # ========================================================
    # SERVER
    # ========================================================

    HOST = os.getenv(
        "HOST",
        "0.0.0.0",
    ).strip() or "0.0.0.0"

    PORT = _get_int(
        os.getenv(
            "PORT",
            "10000",
        ),
        10000,
    )

    # ========================================================
    # QUEUE
    # ========================================================

    WORKER_COUNT = _get_int(
        os.getenv(
            "WORKER_COUNT",
            "4",
        ),
        4,
    )

    MAX_QUEUE_SIZE = _get_int(
        os.getenv(
            "MAX_QUEUE_SIZE",
            "1000",
        ),
        1000,
    )

    MAX_USER_QUEUE = _get_int(
        os.getenv(
            "MAX_USER_QUEUE",
            "3",
        ),
        3,
    )

    # ========================================================
    # PAID / FREE PRIORITY
    # ========================================================

    PAID_FIRST_PRIORITY = _get_bool(
        os.getenv(
            "PAID_FIRST_PRIORITY",
            "true",
        ),
        True,
    )

    LOAD_PROTECTION_ENABLED = _get_bool(
        os.getenv(
            "LOAD_PROTECTION_ENABLED",
            "true",
        ),
        True,
    )

    # ========================================================
    # FREE TRIAL
    # ========================================================

    FREE_TRIAL_DAYS = _get_int(
        os.getenv(
            "FREE_TRIAL_DAYS",
            "3",
        ),
        3,
    )

    # ========================================================
    # PRICING
    # ========================================================

    TEST_PRICE = os.getenv(
        "TEST_PRICE",
        "0",
    ).strip()

    # ========================================================
    # APP
    # ========================================================

    ENVIRONMENT = os.getenv(
        "ENVIRONMENT",
        "production",
    ).strip() or "production"

    DEBUG = _get_bool(
        os.getenv(
            "DEBUG",
            "false",
        ),
        False,
    )

    # ========================================================
    # TEST SYSTEM
    # ========================================================

    TEST_EXTRACTION_ENABLED = _get_bool(
        os.getenv(
            "TEST_EXTRACTION_ENABLED",
            "true",
        ),
        True,
    )

    TEST_UPLOAD_ENABLED = _get_bool(
        os.getenv(
            "TEST_UPLOAD_ENABLED",
            "true",
        ),
        True,
    )

    AUTO_GITHUB_UPDATE = _get_bool(
        os.getenv(
            "AUTO_GITHUB_UPDATE",
            "false",
        ),
        False,
    )

    # ========================================================
    # GOOGLE SHEET
    # ========================================================

    GOOGLE_SHEET_URL = os.getenv(
        "GOOGLE_SHEET_URL",
        "",
    ).strip()

    GOOGLE_SCRIPT_URL = os.getenv(
        "GOOGLE_SCRIPT_URL",
        "",
    ).strip()

    # ========================================================
    # TELEGRAM LIMITS
    # ========================================================

    TELEGRAM_MESSAGE_LIMIT = 4096

    TELEGRAM_CAPTION_LIMIT = 1024

    # ========================================================
    # RATE LIMIT
    # ========================================================

    USER_RATE_LIMIT = _get_int(
        os.getenv(
            "USER_RATE_LIMIT",
            "10",
        ),
        10,
    )

    USER_RATE_WINDOW = _get_int(
        os.getenv(
            "USER_RATE_WINDOW",
            "60",
        ),
        60,
    )

    # ========================================================
    # LOGGING
    # ========================================================

    LOG_LEVEL = os.getenv(
        "LOG_LEVEL",
        "INFO",
    ).upper().strip()

    # ========================================================
    # BACKWARD COMPATIBILITY
    # ========================================================
    #
    # database.py CONFIG.mongo_url use करता है.
    # बाकी पुराना code CONFIG.MONGO_URL use कर सकता है.
    #
    # दोनों same ENV value से आएंगे.
    # ========================================================

    @property
    def mongo_url(self):
        return self.MONGO_URL

    @property
    def mongo_database(self):
        return self.MONGO_DATABASE

    @property
    def bot_token(self):
        return self.BOT_TOKEN

    @property
    def api_id(self):
        return self.API_ID

    @property
    def api_hash(self):
        return self.API_HASH

    @property
    def admin_ids(self):
        return self.ADMIN_IDS

    @property
    def github_token(self):
        return self.GITHUB_TOKEN

    @property
    def github_owner(self):
        return self.GITHUB_OWNER

    @property
    def github_repo(self):
        return self.GITHUB_REPO

    @property
    def github_branch(self):
        return self.GITHUB_BRANCH

    @property
    def port(self):
        return self.PORT

    @property
    def host(self):
        return self.HOST


# ============================================================
# GLOBAL CONFIG OBJECT
# ============================================================

CONFIG = Config()


# ============================================================
# VALIDATION
# ============================================================

def validate_config() -> None:
    """
    Required production configuration check.

    GitHub intentionally required नहीं है.
    """

    required = {
        "BOT_TOKEN": CONFIG.BOT_TOKEN,
        "MONGO_URL": CONFIG.MONGO_URL,
        "API_ID": CONFIG.API_ID,
        "API_HASH": CONFIG.API_HASH,
        "ADMIN_IDS": CONFIG.ADMIN_IDS,
    }

    missing = [
        key
        for key, value in required.items()
        if not value
    ]

    if missing:

        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
        )


# ============================================================
# SAFE CONFIG SUMMARY
# ============================================================

def config_summary() -> dict:
    """
    Safe configuration summary.

    Secrets कभी return नहीं करता.
    """

    return {
        "environment": CONFIG.ENVIRONMENT,
        "mongo_configured": bool(
            CONFIG.MONGO_URL
        ),
        "telegram_configured": bool(
            CONFIG.BOT_TOKEN
        ),
        "api_configured": bool(
            CONFIG.API_ID
            and CONFIG.API_HASH
        ),
        "admin_count": len(
            CONFIG.ADMIN_IDS
        ),
        "github_configured": bool(
            CONFIG.GITHUB_TOKEN
            and CONFIG.GITHUB_OWNER
            and CONFIG.GITHUB_REPO
        ),
        "google_sheet_configured": bool(
            CONFIG.GOOGLE_SHEET_URL
            or CONFIG.GOOGLE_SCRIPT_URL
        ),
        "test_extraction_enabled": (
            CONFIG.TEST_EXTRACTION_ENABLED
        ),
        "test_upload_enabled": (
            CONFIG.TEST_UPLOAD_ENABLED
        ),
        "port": CONFIG.PORT,
    }

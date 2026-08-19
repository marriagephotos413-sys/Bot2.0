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

    All sensitive values are read from environment variables.

    Both uppercase and lowercase configuration attributes
    are supported for compatibility with existing modules.
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
    # GitHub values are OPTIONAL.
    #
    # If GitHub upload is enabled, these values are used.
    #
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

    GITHUB_TEMPLATE_PATH = os.getenv(
        "GITHUB_TEMPLATE_PATH",
        "tcs.html",
    ).strip() or "tcs.html"

    GITHUB_TESTS_DIRECTORY = os.getenv(
        "GITHUB_TESTS_DIRECTORY",
        "published",
    ).strip().strip("/") or "published"

    # ========================================================
    # CHANNELS
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
    # COMPATIBILITY / PROCESSING
    # ========================================================

    BROADCAST_DELAY = float(
        os.getenv(
            "BROADCAST_DELAY",
            "0.05",
        ) or "0.05"
    )

    EXTRACT_MAX_RETRIES = _get_int(
        os.getenv(
            "EXTRACT_MAX_RETRIES",
            "2",
        ),
        2,
    )

    SEND_EXTRACTED_HTML = _get_bool(
        os.getenv(
            "SEND_EXTRACTED_HTML",
            "false",
        ),
        False,
    )

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
    def github_test_file(self):
        return self.GITHUB_TEST_FILE

    @property
    def github_template_path(self):
        return self.GITHUB_TEMPLATE_PATH

    @property
    def github_tests_directory(self):
        return self.GITHUB_TESTS_DIRECTORY

    @property
    def database_channel_id(self):
        return self.DATABASE_CHANNEL_ID

    @property
    def payment_verify_channel_id(self):
        return self.PAYMENT_VERIFY_CHANNEL_ID

    @property
    def user_activity_channel_id(self):
        return self.USER_ACTIVITY_CHANNEL_ID

    @property
    def paid_user_channel_id(self):
        return self.PAID_USER_CHANNEL_ID

    @property
    def force_join_channels(self):
        return self.FORCE_JOIN_CHANNELS

    @property
    def host(self):
        return self.HOST

    @property
    def port(self):
        return self.PORT

    @property
    def worker_count(self):
        return self.WORKER_COUNT

    @property
    def max_queue_size(self):
        return self.MAX_QUEUE_SIZE

    @property
    def max_user_queue(self):
        return self.MAX_USER_QUEUE

    @property
    def paid_first_priority(self):
        return self.PAID_FIRST_PRIORITY

    @property
    def load_protection_enabled(self):
        return self.LOAD_PROTECTION_ENABLED

    @property
    def free_trial_days(self):
        return self.FREE_TRIAL_DAYS

    @property
    def test_price(self):
        return self.TEST_PRICE

    @property
    def environment(self):
        return self.ENVIRONMENT

    @property
    def debug(self):
        return self.DEBUG

    @property
    def test_extraction_enabled(self):
        return self.TEST_EXTRACTION_ENABLED

    @property
    def test_upload_enabled(self):
        return self.TEST_UPLOAD_ENABLED

    @property
    def auto_github_update(self):
        return self.AUTO_GITHUB_UPDATE

    @property
    def broadcast_delay(self):
        return self.BROADCAST_DELAY

    @property
    def extract_max_retries(self):
        return self.EXTRACT_MAX_RETRIES

    @property
    def send_extracted_html(self):
        return self.SEND_EXTRACTED_HTML

    @property
    def google_sheet_url(self):
        return self.GOOGLE_SHEET_URL

    @property
    def google_script_url(self):
        return self.GOOGLE_SCRIPT_URL

    @property
    def user_rate_limit(self):
        return self.USER_RATE_LIMIT

    @property
    def user_rate_window(self):
        return self.USER_RATE_WINDOW

    @property
    def log_level(self):
        return self.LOG_LEVEL


# ============================================================
# GLOBAL CONFIG OBJECT
# ============================================================

CONFIG = Config()


# ============================================================
# VALIDATION
# ============================================================

def validate_config() -> None:
    """
    Validate only truly required configuration.

    GitHub is intentionally NOT required here.
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

import os
from typing import List


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


class Config:
    """
    Central application configuration.

    Secrets हमेशा environment variables से लिए जाते हैं।
    GitHub पर actual secrets नहीं रखने हैं।
    """

    # ========================================================
    # TELEGRAM
    # ========================================================

    BOT_TOKEN = os.getenv(
        "BOT_TOKEN",
        "",
    )

    API_ID = _get_int(
        os.getenv(
            "API_ID",
            "0",
        )
    )

    API_HASH = os.getenv(
        "API_HASH",
        "",
    )

    # ========================================================
    # MONGODB
    # ========================================================

    MONGO_URL = os.getenv(
        "MONGO_URL",
        "",
    )

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

    GITHUB_TOKEN = os.getenv(
        "GITHUB_TOKEN",
        "",
    )

    GITHUB_OWNER = os.getenv(
        "GITHUB_OWNER",
        "",
    )

    GITHUB_REPO = os.getenv(
        "GITHUB_REPO",
        "",
    )

    GITHUB_BRANCH = os.getenv(
        "GITHUB_BRANCH",
        "main",
    )

    # ========================================================
    # CHANNELS
    # ========================================================

    DATABASE_CHANNEL_ID = _get_int(
        os.getenv(
            "DATABASE_CHANNEL_ID",
            "0",
        )
    )

    PAYMENT_VERIFY_CHANNEL_ID = _get_int(
        os.getenv(
            "PAYMENT_VERIFY_CHANNEL_ID",
            "0",
        )
    )

    USER_ACTIVITY_CHANNEL_ID = _get_int(
        os.getenv(
            "USER_ACTIVITY_CHANNEL_ID",
            "0",
        )
    )

    PAID_USER_CHANNEL_ID = _get_int(
        os.getenv(
            "PAID_USER_CHANNEL_ID",
            "0",
        )
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
    )

    # ========================================================
    # APP
    # ========================================================

    ENVIRONMENT = os.getenv(
        "ENVIRONMENT",
        "production",
    )

    DEBUG = (
        os.getenv(
            "DEBUG",
            "false",
        ).lower()
        in (
            "1",
            "true",
            "yes",
        )
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
    """

    required = {
        "BOT_TOKEN": CONFIG.BOT_TOKEN,
        "MONGO_URL": CONFIG.MONGO_URL,
        "GITHUB_TOKEN": CONFIG.GITHUB_TOKEN,
        "GITHUB_OWNER": CONFIG.GITHUB_OWNER,
        "GITHUB_REPO": CONFIG.GITHUB_REPO,
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

import os
from dataclasses import dataclass
from typing import Set

from dotenv import load_dotenv

load_dotenv()


def _get_int_set(value: str) -> Set[int]:
    """
    Comma-separated Telegram user IDs:
    123456789,987654321
    """
    result = set()

    for item in (value or "").split(","):
        item = item.strip()

        if not item:
            continue

        try:
            result.add(int(item))
        except ValueError:
            continue

    return result


def _required(name: str) -> str:
    """
    Required environment variable.
    """
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Required environment variable is missing: {name}"
        )

    return value


@dataclass(frozen=True)
class Config:

    # ============================================================
    # TELEGRAM
    # ============================================================

    bot_token: str

    # Telegram API ID / API HASH
    # इन्हें Telethon वाले advanced Telegram operations के लिए रखा गया है।
    api_id: int
    api_hash: str

    # Bot admins
    admin_ids: Set[int]

    # ============================================================
    # DATABASE
    # ============================================================
    
    mongo_url = os.getenv("MONGO_URL")

    # ============================================================
    # GITHUB
    # ============================================================

    github_token: str
    github_owner: str
    github_repo: str
    github_branch: str

    # GitHub में TCS template की location
    github_template_path: str

    # Published tests की directory
    github_tests_directory: str

    # ============================================================
    # RENDER / SERVER
    # ============================================================

    host: str
    port: int

    # ============================================================
    # QUEUE
    # ============================================================

    # एक worker कितने jobs process करेगा
    worker_count: int

    # Paid users के कितने priority workers
    paid_worker_count: int

    # Free users के कितने normal workers
    free_worker_count: int

    # ============================================================
    # FILE LIMITS
    # ============================================================

    # Single HTML upload maximum size
    max_test_file_mb: int

    # Bulk upload maximum files
    max_bulk_files: int

    # ============================================================
    # BOT SETTINGS
    # ============================================================

    # User को load message कितने seconds बाद दिखाना है
    load_warning_seconds: int

    # Failed job automatic retry count
    max_retry_count: int

    # ============================================================
    # UPTIME / HEALTH
    # ============================================================

    health_path: str

    # ============================================================
    # LOGGING
    # ============================================================

    log_level: str


def load_config() -> Config:

    # ------------------------------------------------------------
    # Basic Telegram credentials
    # ------------------------------------------------------------

    bot_token = _required("BOT_TOKEN")

    api_id_raw = _required("API_ID")

    try:
        api_id = int(api_id_raw)
    except ValueError:
        raise RuntimeError("API_ID must be a number.")

    api_hash = _required("API_HASH")

    admin_ids = _get_int_set(
        os.getenv("ADMIN_IDS", "")
    )

    if not admin_ids:
        raise RuntimeError(
            "ADMIN_IDS is empty. Add at least one Telegram user ID."
        )

    # ------------------------------------------------------------
    # MongoDB
    # ------------------------------------------------------------

    mongo_url = _required("MONGO_URL")

    mongo_database = os.getenv(
        "MONGO_DATABASE",
        "telegram_test_bot"
    ).strip()

    # ------------------------------------------------------------
    # GitHub
    # ------------------------------------------------------------

    github_token = _required("GITHUB_TOKEN")

    github_owner = _required("GITHUB_OWNER")

    github_repo = _required("GITHUB_REPO")

    github_branch = os.getenv(
        "GITHUB_BRANCH",
        "main"
    ).strip()

    # तुम्हारी original TCS UI इस template में रहेगी।
    github_template_path = os.getenv(
        "GITHUB_TEMPLATE_PATH",
        "templates/tcs.html"
    ).strip()

    # Generated tests इस folder में जाएंगे।
    github_tests_directory = os.getenv(
        "GITHUB_TESTS_DIRECTORY",
        "published"
    ).strip().strip("/")

    # ------------------------------------------------------------
    # Render
    # ------------------------------------------------------------

    host = os.getenv(
        "HOST",
        "0.0.0.0"
    ).strip()

    try:
        port = int(
            os.getenv(
                "PORT",
                "10000"
            )
        )
    except ValueError:
        port = 10000

    # ------------------------------------------------------------
    # Queue configuration
    # ------------------------------------------------------------

    try:
        worker_count = int(
            os.getenv(
                "WORKER_COUNT",
                "4"
            )
        )
    except ValueError:
        worker_count = 4

    try:
        paid_worker_count = int(
            os.getenv(
                "PAID_WORKER_COUNT",
                "3"
            )
        )
    except ValueError:
        paid_worker_count = 3

    try:
        free_worker_count = int(
            os.getenv(
                "FREE_WORKER_COUNT",
                "1"
            )
        )
    except ValueError:
        free_worker_count = 1

    # कम से कम 1 worker
    worker_count = max(1, worker_count)
    paid_worker_count = max(1, paid_worker_count)
    free_worker_count = max(1, free_worker_count)

    # ------------------------------------------------------------
    # File limits
    # ------------------------------------------------------------

    try:
        max_test_file_mb = int(
            os.getenv(
                "MAX_TEST_FILE_MB",
                "50"
            )
        )
    except ValueError:
        max_test_file_mb = 50

    try:
        max_bulk_files = int(
            os.getenv(
                "MAX_BULK_FILES",
                "500"
            )
        )
    except ValueError:
        max_bulk_files = 500

    # ------------------------------------------------------------
    # Load / Retry
    # ------------------------------------------------------------

    try:
        load_warning_seconds = int(
            os.getenv(
                "LOAD_WARNING_SECONDS",
                "5"
            )
        )
    except ValueError:
        load_warning_seconds = 5

    try:
        max_retry_count = int(
            os.getenv(
                "MAX_RETRY_COUNT",
                "3"
            )
        )
    except ValueError:
        max_retry_count = 3

    # ------------------------------------------------------------
    # Health
    # ------------------------------------------------------------

    health_path = os.getenv(
        "HEALTH_PATH",
        "/health"
    ).strip()

    if not health_path.startswith("/"):
        health_path = "/" + health_path

    # ------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------

    log_level = os.getenv(
        "LOG_LEVEL",
        "INFO"
    ).upper().strip()

    return Config(
        bot_token=bot_token,
        api_id=api_id,
        api_hash=api_hash,
        admin_ids=admin_ids,

        mongo_url=mongo_url,
        mongo_database=mongo_database,

        github_token=github_token,
        github_owner=github_owner,
        github_repo=github_repo,
        github_branch=github_branch,

        github_template_path=github_template_path,
        github_tests_directory=github_tests_directory,

        host=host,
        port=port,

        worker_count=worker_count,
        paid_worker_count=paid_worker_count,
        free_worker_count=free_worker_count,

        max_test_file_mb=max_test_file_mb,
        max_bulk_files=max_bulk_files,

        load_warning_seconds=load_warning_seconds,
        max_retry_count=max_retry_count,

        health_path=health_path,
        log_level=log_level,
    )


# पूरे project में यही single config object use होगा।
CONFIG = load_config()

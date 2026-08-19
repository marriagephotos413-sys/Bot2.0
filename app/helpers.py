import asyncio
import html
import re
import time
from datetime import datetime, timezone
from typing import Any, Iterable, List, Optional


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(
    value: Any,
) -> str:
    """
    किसी भी value को clean string में convert करता है।
    """

    if value is None:
        return ""

    text = str(value)

    text = (
        text
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    return text.strip()


def normalize_spaces(
    value: Any,
) -> str:

    text = clean_text(value)

    return re.sub(
        r"[ \t]+",
        " ",
        text,
    ).strip()


def normalize_lines(
    value: Any,
) -> str:

    text = clean_text(value)

    lines = []

    for line in text.splitlines():

        line = normalize_spaces(line)

        if line:
            lines.append(line)

    return "\n".join(lines)


def truncate(
    value: Any,
    limit: int = 4000,
    suffix: str = "...",
) -> str:

    text = clean_text(value)

    if len(text) <= limit:
        return text

    if limit <= len(suffix):
        return text[:limit]

    return (
        text[: limit - len(suffix)]
        + suffix
    )


# ============================================================
# TELEGRAM TEXT
# ============================================================

def escape_html(
    value: Any,
) -> str:

    return html.escape(
        clean_text(value),
        quote=False,
    )


def escape_markdown(
    value: Any,
) -> str:

    """
    Telegram MarkdownV2 compatible escaping.
    """

    text = clean_text(value)

    special = r"_*[]()~`>#+-=|{}.!\\"

    result = []

    for char in text:

        if char in special:
            result.append("\\")
        
        result.append(char)

    return "".join(result)


def split_message(
    text: Any,
    limit: int = 4096,
) -> List[str]:

    """
    Long Telegram message को safe chunks में divide करता है।
    """

    text = clean_text(text)

    if not text:
        return []

    if len(text) <= limit:
        return [text]

    chunks = []

    current = ""

    for line in text.splitlines(
        keepends=True
    ):

        if len(current) + len(line) <= limit:

            current += line

        else:

            if current:
                chunks.append(
                    current.rstrip()
                )

            # बहुत लंबी single line
            while len(line) > limit:

                chunks.append(
                    line[:limit]
                )

                line = line[limit:]

            current = line

    if current:
        chunks.append(
            current.rstrip()
        )

    return chunks


# ============================================================
# ID HELPERS
# ============================================================

def safe_int(
    value: Any,
    default: int = 0,
) -> int:

    try:

        return int(
            str(value).strip()
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:

        return float(
            str(value).strip()
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


def unique_list(
    values: Iterable[Any],
) -> List[Any]:

    result = []

    seen = set()

    for value in values:

        key = str(value)

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


# ============================================================
# SLUG
# ============================================================

def slugify(
    value: Any,
    max_length: int = 100,
) -> str:

    text = clean_text(value).lower()

    text = re.sub(
        r"[^a-zA-Z0-9\u0900-\u097F_-]+",
        "-",
        text,
    )

    text = re.sub(
        r"-{2,}",
        "-",
        text,
    )

    text = text.strip(
        "-_"
    )

    if not text:
        text = "item"

    return text[
        :max_length
    ]


# ============================================================
# DATE / TIME
# ============================================================

def utc_now() -> datetime:

    return datetime.now(
        timezone.utc
    )


def timestamp() -> int:

    return int(
        time.time()
    )


def format_datetime(
    value: Optional[datetime],
    fmt: str = "%d-%m-%Y %H:%M:%S",
) -> str:

    if not value:
        return "-"

    try:

        return value.strftime(
            fmt
        )

    except Exception:

        return "-"


def format_duration(
    seconds: Any,
) -> str:

    seconds = max(
        0,
        safe_int(seconds),
    )

    hours, remainder = divmod(
        seconds,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    if hours:
        return (
            f"{hours}h "
            f"{minutes}m "
            f"{seconds}s"
        )

    if minutes:
        return (
            f"{minutes}m "
            f"{seconds}s"
        )

    return f"{seconds}s"


# ============================================================
# PERCENTAGE / PROGRESS
# ============================================================

def clamp(
    value: Any,
    minimum: float = 0,
    maximum: float = 100,
) -> float:

    value = safe_float(
        value
    )

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def progress_bar(
    percentage: Any,
    size: int = 10,
) -> str:

    percentage = clamp(
        percentage
    )

    size = max(
        1,
        safe_int(size, 10),
    )

    filled = round(
        (percentage / 100)
        * size
    )

    empty = size - filled

    return (
        "█" * filled
        + "░" * empty
    )


# ============================================================
# USERNAME
# ============================================================

def display_name(
    user: Any,
) -> str:

    if not user:
        return "User"

    first_name = clean_text(
        getattr(
            user,
            "first_name",
            "",
        )
    )

    last_name = clean_text(
        getattr(
            user,
            "last_name",
            "",
        )
    )

    username = clean_text(
        getattr(
            user,
            "username",
            "",
        )
    )

    if first_name or last_name:

        name = (
            f"{first_name} "
            f"{last_name}"
        ).strip()

        if username:
            return (
                f"{name} "
                f"(@{username})"
            )

        return name

    if username:
        return (
            f"@{username}"
        )

    user_id = getattr(
        user,
        "id",
        None,
    )

    if user_id:
        return f"User {user_id}"

    return "User"


def username_or_id(
    user: Any,
) -> str:

    username = clean_text(
        getattr(
            user,
            "username",
            "",
        )
    )

    if username:
        return f"@{username}"

    user_id = getattr(
        user,
        "id",
        None,
    )

    if user_id:
        return str(user_id)

    return "-"


# ============================================================
# TELEGRAM IDs
# ============================================================

def normalize_chat_id(
    value: Any,
) -> Optional[int]:

    if value is None:
        return None

    text = clean_text(value)

    if not text:
        return None

    if text.startswith(
        "@"
    ):
        return None

    try:
        return int(text)

    except (
        TypeError,
        ValueError,
    ):

        return None


# ============================================================
# BOOLEAN
# ============================================================

def to_bool(
    value: Any,
    default: bool = False,
) -> bool:

    if isinstance(
        value,
        bool,
    ):
        return value

    if value is None:
        return default

    value = clean_text(
        value
    ).lower()

    if value in (
        "1",
        "true",
        "yes",
        "y",
        "on",
        "enable",
        "enabled",
    ):
        return True

    if value in (
        "0",
        "false",
        "no",
        "n",
        "off",
        "disable",
        "disabled",
    ):
        return False

    return default


# ============================================================
# ASYNC HELPERS
# ============================================================

async def safe_sleep(
    seconds: float,
) -> None:

    try:

        await asyncio.sleep(
            max(
                0,
                float(seconds),
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return


async def retry_async(
    function,
    retries: int = 3,
    delay: float = 1.0,
    exceptions=(Exception,),
    *args,
    **kwargs,
):

    last_error = None

    for attempt in range(
        retries
    ):

        try:

            return await function(
                *args,
                **kwargs,
            )

        except exceptions as exc:

            last_error = exc

            if (
                attempt
                >= retries - 1
            ):
                raise

            await safe_sleep(
                delay
                * (attempt + 1)
            )

    raise last_error


# ============================================================
# ERROR HELPERS
# ============================================================

def error_text(
    error: Any,
    limit: int = 500,
) -> str:

    if error is None:
        return "Unknown error"

    return truncate(
        str(error),
        limit,
    )


# ============================================================
# TEST HELPERS
# ============================================================

def normalize_exam_name(
    exam: Any,
) -> str:

    value = normalize_spaces(
        exam
    )

    aliases = {
        "cgl": "SSC CGL",
        "ssc cgl": "SSC CGL",
        "chsl": "SSC CHSL",
        "ssc chsl": "SSC CHSL",
        "ssc gd": "SSC GD",
        "gd": "SSC GD",
        "mts": "SSC MTS",
        "ntpc": "RRB NTPC",
        "rrb ntpc": "RRB NTPC",
        "group d": "RRB Group D",
        "rrb group d": "RRB Group D",
        "alp": "RRB ALP",
        "upsc": "UPSC",
    }

    return aliases.get(
        value.lower(),
        value,
    )


def normalize_test_type(
    value: Any,
) -> str:

    value = normalize_spaces(
        value
    ).lower()

    if value in (
        "mock",
        "mock test",
        "mock-test",
        "मॉक",
        "मॉक टेस्ट",
    ):
        return "mock"

    if value in (
        "pyq",
        "previous",
        "previous paper",
        "previous year",
        "previous year paper",
        "previous-year",
    ):
        return "pyq"

    return (
        value
        or "other"
    )


def question_count(
    questions: Any,
) -> int:

    if not isinstance(
        questions,
        list,
    ):
        return 0

    return len(
        questions
    )


# ============================================================
# DICT HELPERS
# ============================================================

def first_value(
    data: Any,
    *keys: str,
    default: Any = None,
) -> Any:

    if not isinstance(
        data,
        dict,
    ):
        return default

    for key in keys:

        value = data.get(
            key
        )

        if value not in (
            None,
            "",
            [],
        ):

            return value

    return default


def merge_dicts(
    first: Optional[dict],
    second: Optional[dict],
) -> dict:

    result = {}

    if isinstance(
        first,
        dict,
    ):
        result.update(
            first
        )

    if isinstance(
        second,
        dict,
    ):
        result.update(
            second
        )

    return result


# ============================================================
# SECURITY
# ============================================================

def mask_secret(
    value: Any,
    visible: int = 4,
) -> str:

    text = clean_text(
        value
    )

    if not text:
        return ""

    if len(text) <= visible:
        return "*" * len(text)

    return (
        "*" * (
            len(text)
            - visible
        )
        + text[-visible:]
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "clean_text",
    "normalize_spaces",
    "normalize_lines",
    "truncate",
    "escape_html",
    "escape_markdown",
    "split_message",
    "safe_int",
    "safe_float",
    "unique_list",
    "slugify",
    "utc_now",
    "timestamp",
    "format_datetime",
    "format_duration",
    "clamp",
    "progress_bar",
    "display_name",
    "username_or_id",
    "normalize_chat_id",
    "to_bool",
    "safe_sleep",
    "retry_async",
    "error_text",
    "normalize_exam_name",
    "normalize_test_type",
    "question_count",
    "first_value",
    "merge_dicts",
    "mask_secret",
]

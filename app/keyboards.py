from typing import Iterable, List, Optional, Sequence, Tuple

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


# ============================================================
# TYPES
# ============================================================

ButtonSpec = Tuple[str, str]


# ============================================================
# GENERIC HELPERS
# ============================================================

def button(
    text: str,
    callback_data: Optional[str] = None,
    url: Optional[str] = None,
) -> InlineKeyboardButton:

    if url:
        return InlineKeyboardButton(
            text=text,
            url=url,
        )

    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data or "noop",
    )


def row(
    *buttons: InlineKeyboardButton,
) -> List[InlineKeyboardButton]:

    return list(buttons)


def markup(
    rows: Iterable[
        Iterable[InlineKeyboardButton]
    ],
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            list(item)
            for item in rows
        ]
    )


def back_button(
    callback: str = "home",
    text: str = "🔙 BACK",
) -> InlineKeyboardButton:

    return button(
        text,
        callback,
    )


def home_button() -> InlineKeyboardButton:

    return button(
        "🏠 HOME",
        "home",
    )


# ============================================================
# START / HOME
# ============================================================

def home_keyboard() -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "📚 TEST INDEX",
                    "index:categories",
                ),
            ),
            row(
                button(
                    "🚀 EXTRACT TEST",
                    "index:categories",
                ),
            ),
            row(
                button(
                    "💎 PREMIUM",
                    "pricing:show",
                ),
                button(
                    "🎁 FREE TRIAL",
                    "trial:show",
                ),
            ),
            row(
                button(
                    "📊 MY ACCOUNT",
                    "user:info",
                ),
                button(
                    "📢 CHANNELS",
                    "channels:list",
                ),
            ),
            row(
                button(
                    "❓ HELP",
                    "help",
                ),
        ]
    )


# ============================================================
# CATEGORY INDEX
# ============================================================

def category_keyboard(
    categories: Sequence[dict],
) -> InlineKeyboardMarkup:

    rows = []

    for category in categories:

        category_id = str(
            category.get(
                "id",
                category.get(
                    "category",
                    "other",
                ),
            )
        )

        title = str(
            category.get(
                "title",
                category_id.title(),
            )
        )

        icon = str(
            category.get(
                "icon",
                "📂",
            )
        )

        rows.append(
            row(
                button(
                    f"{icon} {title}",
                    f"category:{category_id}",
                )
            )
        )

    rows.append(
        row(
            home_button(),
        )
    )

    return markup(
        rows
    )


# ============================================================
# EXAM INDEX
# ============================================================

def exam_keyboard(
    exams: Sequence[dict],
    category: str,
) -> InlineKeyboardMarkup:

    rows = []

    for exam in exams:

        exam_id = str(
            exam.get(
                "id",
                exam.get(
                    "exam",
                    "other",
                ),
            )
        )

        title = str(
            exam.get(
                "title",
                exam_id,
            )
        )

        icon = str(
            exam.get(
                "icon",
                "📁",
            )
        )

        rows.append(
            row(
                button(
                    f"{icon} {title}",
                    f"exam:{category}:{exam_id}",
                )
            )
        )

    rows.append(
        row(
            back_button(
                "index:categories"
            ),
            home_button(),
        )
    )

    return markup(
        rows
    )


# ============================================================
# TEST TYPE
# ============================================================

def test_type_keyboard(
    category: str,
    exam: str,
) -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "📝 MOCK TEST",
                    f"type:{category}:{exam}:mock",
                ),
            ),
            row(
                button(
                    "📜 PYQ / PREVIOUS PAPER",
                    f"type:{category}:{exam}:pyq",
                ),
            ),
            row(
                button(
                    "📚 ALL TESTS",
                    f"type:{category}:{exam}:all",
                ),
            ),
            row(
                back_button(
                    f"category:{category}"
                ),
                home_button(),
            ),
        ]
    )


# ============================================================
# YEAR INDEX
# ============================================================

def year_keyboard(
    years: Sequence[str],
    category: str,
    exam: str,
    test_type: str,
) -> InlineKeyboardMarkup:

    rows = []

    for year in years:

        year_text = str(
            year
        )

        rows.append(
            row(
                button(
                    f"📅 {year_text}",
                    (
                        f"year:"
                        f"{category}:"
                        f"{exam}:"
                        f"{test_type}:"
                        f"{year_text}"
                    ),
                )
            )
        )

    rows.append(
        row(
            button(
                "📚 ALL YEARS",
                (
                    f"year:"
                    f"{category}:"
                    f"{exam}:"
                    f"{test_type}:all"
                ),
            )
        )
    )

    rows.append(
        row(
            back_button(
                f"exam:{category}:{exam}"
            ),
            home_button(),
        )
    )

    return markup(
        rows
    )


# ============================================================
# TEST LIST
# ============================================================

def test_list_keyboard(
    tests: Sequence[dict],
    category: str,
    exam: str,
    test_type: str,
    year: str,
    page: int = 1,
    total_pages: int = 1,
) -> InlineKeyboardMarkup:

    rows = []

    for test in tests:

        test_id = str(
            test.get(
                "test_id",
                test.get(
                    "id",
                    "",
                ),
            )
        )

        title = str(
            test.get(
                "title",
                "Test",
            )
        )

        count = test.get(
            "question_count",
            0,
        )

        label = (
            f"📝 {title}"
        )

        if count:
            label += (
                f" • {count} Q"
            )

        rows.append(
            row(
                button(
                    label,
                    f"test:{test_id}",
                )
            )
        )

    # --------------------------------------------------------
    # Pagination
    # --------------------------------------------------------

    navigation = []

    if page > 1:

        navigation.append(
            button(
                "⬅️ PREV",
                (
                    f"tests_page:"
                    f"{category}:"
                    f"{exam}:"
                    f"{test_type}:"
                    f"{year}:"
                    f"{page - 1}"
                ),
            )
        )

    navigation.append(
        button(
            f"📄 {page}/{total_pages}",
            "noop",
        )
    )

    if page < total_pages:

        navigation.append(
            button(
                "NEXT ➡️",
                (
                    f"tests_page:"
                    f"{category}:"
                    f"{exam}:"
                    f"{test_type}:"
                    f"{year}:"
                    f"{page + 1}"
                ),
            )
        )

    rows.append(
        navigation
    )

    rows.append(
        row(
            back_button(
                (
                    f"year:"
                    f"{category}:"
                    f"{exam}:"
                    f"{test_type}:"
                    f"all"
                )
            ),
            home_button(),
        )
    )

    return markup(
        rows
    )


# ============================================================
# TEST DETAILS
# ============================================================

def test_details_keyboard(
    test_id: str,
    is_paid: bool = False,
    can_extract: bool = True,
) -> InlineKeyboardMarkup:

    rows = []

    if can_extract:

        if is_paid:

            rows.append(
                row(
                    button(
                        "🚀 EXTRACT TEST",
                        f"extract:{test_id}",
                    )
                )
            )

        else:

            rows.append(
                row(
                    button(
                        "🚀 EXTRACT TEST",
                        f"extract:{test_id}",
                    )
                )
            )

    rows.append(
        row(
            button(
                "📊 TEST DETAILS",
                f"testinfo:{test_id}",
            )
        )
    )

    rows.append(
        row(
            button(
                "⚠️ REPORT TEST",
                f"report:test:{test_id}",
            )
        )
    )

    rows.append(
        row(
            home_button(),
        )
    )

    return markup(
        rows
    )


# ============================================================
# EXTRACT STATUS
# ============================================================

def extract_status_keyboard(
    job_id: str,
) -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "🔄 REFRESH STATUS",
                    f"extract:status:{job_id}",
                )
            ),
            row(
                button(
                    "❌ CANCEL",
                    f"extract:cancel:{job_id}",
                )
            ),
            row(
                home_button(),
            ),
        ]
    )


# ============================================================
# FAILED EXTRACTION
# ============================================================

def extraction_failed_keyboard(
    job_id: str,
) -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "🔁 RETRY",
                    f"extract:retry:{job_id}",
                )
            ),
            row(
                button(
                    "📚 TEST INDEX",
                    "index:categories",
                ),
            ),
            row(
                home_button(),
            ),
        ]
    )


# ============================================================
# ADMIN PANEL
# ============================================================

def admin_keyboard() -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "📊 BOT STATS",
                    "admin:stats",
                ),
                button(
                    "👥 USER LIST",
                    "admin:users",
                ),
            ),
            row(
                button(
                    "💎 PAID USERS",
                    "admin:paid_users",
                ),
                button(
                    "🚫 BAN USER",
                    "admin:ban",
                ),
            ),
            row(
                button(
                    "🔓 UNBAN USER",
                    "admin:unban",
                ),
                button(
                    "🎁 FREE TRIAL",
                    "admin:trial",
                ),
            ),
            row(
                button(
                    "🔒 TRIAL LOCK",
                    "admin:trial_lock",
                ),
                button(
                    "💰 PRICE",
                    "admin:price",
                ),
            ),
            row(
                button(
                    "📤 UPLOAD TEST",
                    "upload:start",
                ),
                button(
                    "📚 TEST DATABASE",
                    "admin:database",
                ),
            ),
            row(
                button(
                    "📢 BROADCAST",
                    "admin:broadcast",
                ),
            ),
            row(
                button(
                    "📈 REPORTS",
                    "admin:reports",
                ),
                button(
                    "📊 EXTRACTION STATS",
                    "admin:extraction_stats",
                ),
            ),
            row(
                button(
                    "🔐 FORCE JOIN",
                    "admin:force_join",
                ),
                button(
                    "⚙️ SETTINGS",
                    "admin:settings",
                ),
            ),
            row(
                button(
                    "💳 PAYMENTS",
                    "admin:payments",
                ),
                button(
                    "💾 BACKUP",
                    "admin:backup",
                ),
            ),
            row(
                home_button(),
            ),
        ]
    )


# ============================================================
# USER MANAGEMENT
# ============================================================

def user_management_keyboard(
    user_id: int,
    is_banned: bool = False,
    is_paid: bool = False,
) -> InlineKeyboardMarkup:

    rows = []

    if is_banned:

        rows.append(
            row(
                button(
                    "🔓 UNBAN",
                    f"admin:unban:{user_id}",
                )
            )
        )

    else:

        rows.append(
            row(
                button(
                    "🚫 BAN",
                    f"admin:ban:{user_id}",
                )
            )
        )

    if is_paid:

        rows.append(
            row(
                button(
                    "❌ REMOVE PAID",
                    f"admin:remove_paid:{user_id}",
                )
            )
        )

    else:

        rows.append(
            row(
                button(
                    "💎 MAKE PAID",
                    f"admin:add_paid:{user_id}",
                )
            )
        )

    rows.append(
        row(
            button(
                "👤 USER INFO",
                f"admin:userinfo:{user_id}",
            )
        )
    )

    rows.append(
        row(
            back_button(
                "admin:users"
            ),
            home_button(),
        )
    )

    return markup(
        rows
    )


# ============================================================
# PAID USER
# ============================================================

def paid_user_keyboard(
    user_id: int,
) -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "👤 USER INFO",
                    f"admin:userinfo:{user_id}",
                )
            ),
            row(
                button(
                    "❌ REMOVE PAID",
                    f"admin:remove_paid:{user_id}",
                )
            ),
            row(
                back_button(
                    "admin:paid_users"
                ),
                home_button(),
            ),
        ]
    )


# ============================================================
# PAYMENT VERIFICATION
# ============================================================

def payment_verification_keyboard(
    payment_id: str,
    user_id: int,
) -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "✅ APPROVE",
                    (
                        f"payment:approve:"
                        f"{payment_id}:"
                        f"{user_id}"
                    ),
                ),
                button(
                    "❌ REJECT",
                    (
                        f"payment:reject:"
                        f"{payment_id}:"
                        f"{user_id}"
                    ),
                ),
            ),
            row(
                button(
                    "👤 USER INFO",
                    f"admin:userinfo:{user_id}",
                )
            ),
        ]
    )


# ============================================================
# FORCE JOIN
# ============================================================

def force_join_keyboard(
    channels: Sequence[dict],
) -> InlineKeyboardMarkup:

    rows = []

    for channel in channels:

        title = str(
            channel.get(
                "title",
                "Join Channel",
            )
        )

        url = channel.get(
            "url"
        )

        if url:

            rows.append(
                row(
                    button(
                        f"📢 {title}",
                        url=url,
                    )
                )
            )

    rows.append(
        row(
            button(
                "✅ VERIFY JOIN",
                "forcejoin:verify",
            )
        )
    )

    return markup(
        rows
    )


# ============================================================
# ADMIN FORCE JOIN
# ============================================================

def force_join_admin_keyboard() -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "➕ ADD CHANNEL",
                    "admin:force_join:add",
                ),
                button(
                    "➖ REMOVE CHANNEL",
                    "admin:force_join:remove",
                ),
            ),
            row(
                button(
                    "📋 CHANNEL LIST",
                    "admin:force_join:list",
                )
            ),
            row(
                back_button(
                    "admin:panel"
                ),
                home_button(),
            ),
        ]
    )


# ============================================================
# BROADCAST
# ============================================================

def broadcast_keyboard() -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "👥 ALL USERS",
                    "broadcast:all",
                )
            ),
            row(
                button(
                    "💎 PAID USERS",
                    "broadcast:paid",
                ),
                button(
                    "🆓 FREE USERS",
                    "broadcast:free",
                ),
            ),
            row(
                button(
                    "❌ CANCEL",
                    "broadcast:cancel",
                )
            ),
        ]
    )


# ============================================================
# TRIAL
# ============================================================

def trial_keyboard() -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "🎁 START FREE TRIAL",
                    "trial:start",
                )
            ),
            row(
                button(
                    "💎 VIEW PREMIUM",
                    "pricing:show",
                )
            ),
            row(
                home_button(),
            ),
        ]
    )


def admin_trial_keyboard() -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "🎁 TRIAL STATUS",
                    "admin:trial:status",
                )
            ),
            row(
                button(
                    "🔒 LOCK TRIAL",
                    "admin:trial_lock",
                )
            ),
            row(
                button(
                    "🔓 UNLOCK TRIAL",
                    "admin:trial_unlock",
                )
            ),
            row(
                back_button(
                    "admin:panel"
                ),
            ),
        ]
    )


# ============================================================
# PRICING
# ============================================================

def pricing_keyboard(
    plans: Sequence[dict],
) -> InlineKeyboardMarkup:

    rows = []

    for plan in plans:

        plan_id = str(
            plan.get(
                "id",
                "",
            )
        )

        name = str(
            plan.get(
                "name",
                "Plan",
            )
        )

        price = plan.get(
            "price",
            0,
        )

        rows.append(
            row(
                button(
                    f"💎 {name} • ₹{price}",
                    f"pricing:buy:{plan_id}",
                )
            )
        )

    rows.append(
        row(
            home_button(),
        )
    )

    return markup(
        rows
    )


# ============================================================
# UPLOAD
# ============================================================

def upload_keyboard() -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "📄 MANUAL UPLOAD",
                    "upload:manual",
                )
            ),
            row(
                button(
                    "📚 BULK UPLOAD",
                    "upload:bulk",
                )
            ),
            row(
                button(
                    "📊 BATCH STATUS",
                    "upload:batch_status",
                )
            ),
            row(
                button(
                    "❌ CANCEL",
                    "upload:cancel",
                )
            ),
        ]
    )


def upload_confirmation_keyboard(
    upload_id: str,
) -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "✅ CONFIRM UPLOAD",
                    f"upload:confirm:{upload_id}",
                )
            ),
            row(
                button(
                    "✏️ EDIT DETAILS",
                    f"upload:edit:{upload_id}",
                )
            ),
            row(
                button(
                    "❌ REMOVE",
                    f"upload:remove:{upload_id}",
                )
            ),
        ]
    )


def upload_batch_keyboard() -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "▶️ START UPLOAD",
                    "upload:start_bulk",
                )
            ),
            row(
                button(
                    "📊 BATCH STATUS",
                    "upload:batch_status",
                )
            ),
            row(
                button(
                    "🔁 RETRY FAILED",
                    "upload:retry_failed",
                )
            ),
            row(
                button(
                    "❌ CANCEL",
                    "upload:cancel",
                )
            ),
        ]
    )


# ============================================================
# REPORTS
# ============================================================

def reports_keyboard() -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "📊 BOT REPORT",
                    "admin:report:bot",
                )
            ),
            row(
                button(
                    "📚 TEST EXTRACTION",
                    "admin:report:extraction",
                )
            ),
            row(
                button(
                    "🎯 EXAM-WISE",
                    "admin:report:exam",
                )
            ),
            row(
                button(
                    "📅 DAILY REPORT",
                    "admin:report:daily",
                )
            ),
            row(
                button(
                    "❌ FAILED TESTS",
                    "admin:report:failed",
                )
            ),
            row(
                back_button(
                    "admin:panel"
                ),
                home_button(),
            ),
        ]
    )


# ============================================================
# BACKUP
# ============================================================

def backup_keyboard() -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "💾 CREATE BACKUP",
                    "admin:backup:create",
                )
            ),
            row(
                button(
                    "📋 BACKUP HISTORY",
                    "admin:backup:list",
                )
            ),
            row(
                back_button(
                    "admin:panel"
                ),
                home_button(),
            ),
        ]
    )


# ============================================================
# SETTINGS
# ============================================================

def settings_keyboard() -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "👋 WELCOME MESSAGE",
                    "admin:welcome",
                )
            ),
            row(
                button(
                    "📢 CHANNEL SETTINGS",
                    "admin:channels",
                )
            ),
            row(
                button(
                    "💰 PRICE SETTINGS",
                    "admin:pricing",
                )
            ),
            row(
                button(
                    "🎁 TRIAL SETTINGS",
                    "admin:trial",
                )
            ),
            row(
                button(
                    "🔐 FORCE JOIN",
                    "admin:force_join",
                )
            ),
            row(
                back_button(
                    "admin:panel"
                ),
                home_button(),
            ),
        ]
    )


# ============================================================
# REPORT TEST
# ============================================================

def report_keyboard(
    test_id: str,
) -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "❌ TEST NOT WORKING",
                    f"report:broken:{test_id}",
                )
            ),
            row(
                button(
                    "⚠️ WRONG QUESTIONS",
                    f"report:questions:{test_id}",
                )
            ),
            row(
                button(
                    "📝 WRONG DETAILS",
                    f"report:details:{test_id}",
                )
            ),
            row(
                button(
                    "🔙 BACK",
                    f"test:{test_id}",
                ),
            ),
        ]
    )


# ============================================================
# USER INFO
# ============================================================

def user_info_keyboard(
    user_id: int,
) -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "🚫 BAN",
                    f"admin:ban:{user_id}",
                ),
                button(
                    "🔓 UNBAN",
                    f"admin:unban:{user_id}",
                ),
            ),
            row(
                button(
                    "💎 ADD PAID",
                    f"admin:add_paid:{user_id}",
                ),
                button(
                    "❌ REMOVE PAID",
                    f"admin:remove_paid:{user_id}",
                ),
            ),
            row(
                button(
                    "🎁 TRIAL",
                    f"admin:trial:user:{user_id}",
                )
            ),
            row(
                back_button(
                    "admin:users"
                ),
                home_button(),
            ),
        ]
    )


# ============================================================
# SEARCH
# ============================================================

def search_keyboard() -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "📚 SEARCH TEST",
                    "search:test",
                )
            ),
            row(
                button(
                    "🎯 SEARCH EXAM",
                    "search:exam",
                )
            ),
            row(
                button(
                    "📅 SEARCH YEAR",
                    "search:year",
                )
            ),
            row(
                home_button(),
            ),
        ]
    )


# ============================================================
# GENERIC CANCEL
# ============================================================

def cancel_keyboard(
    callback: str = "home",
) -> InlineKeyboardMarkup:

    return markup(
        [
            row(
                button(
                    "❌ CANCEL",
                    callback,
                )
            )
        ]
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "button",
    "row",
    "markup",
    "back_button",
    "home_button",
    "home_keyboard",
    "category_keyboard",
    "exam_keyboard",
    "test_type_keyboard",
    "year_keyboard",
    "test_list_keyboard",
    "test_details_keyboard",
    "extract_status_keyboard",
    "extraction_failed_keyboard",
    "admin_keyboard",
    "user_management_keyboard",
    "paid_user_keyboard",
    "payment_verification_keyboard",
    "force_join_keyboard",
    "force_join_admin_keyboard",
    "broadcast_keyboard",
    "trial_keyboard",
    "admin_trial_keyboard",
    "pricing_keyboard",
    "upload_keyboard",
    "upload_confirmation_keyboard",
    "upload_batch_keyboard",
    "reports_keyboard",
    "backup_keyboard",
    "settings_keyboard",
    "report_keyboard",
    "user_info_keyboard",
    "search_keyboard",
    "cancel_keyboard",
]

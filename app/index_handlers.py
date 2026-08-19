import logging
from typing import List, Tuple

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ContextTypes,
)

from .database import db
from .telegram_utils import telegram_utils

logger = logging.getLogger(__name__)


class IndexHandlers:
    """
    User Test Index.

    Flow:

        📚 Category
              ↓
        🎯 Exam
              ↓
        📝 Test Type
              ↓
        📅 Year
              ↓
        📚 Test List
              ↓
        📄 Test Details
              ↓
        🚀 Extract / Open Test
    """

    # ============================================================
    # COMMON
    # ============================================================

    @staticmethod
    def back_button(
        callback_data: str = "index:categories",
    ) -> List[InlineKeyboardButton]:

        return [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data=callback_data,
            )
        ]

    # ============================================================
    # CATEGORY
    # ============================================================

    async def show_categories(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        edit: bool = False,
    ):

        user = update.effective_user

        if not user:
            return

        # --------------------------------------------------------
        # Access check
        # --------------------------------------------------------

        if not await telegram_utils.check_user_access(
            update,
            context,
        ):
            return

        categories = db.get_categories()

        if not categories:

            text = (
                "📚 **Test Index**\n\n"
                "अभी कोई Test उपलब्ध नहीं है।"
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔄 Refresh",
                            callback_data="index:categories",
                        )
                    ]
                ]
            )

            await self._send_or_edit(
                update,
                context,
                text,
                keyboard,
                edit,
            )

            return

        # --------------------------------------------------------
        # Category buttons
        # --------------------------------------------------------

        rows = []

        for category in categories:

            rows.append(
                [
                    InlineKeyboardButton(
                        f"📚 {category}",
                        callback_data=(
                            f"index:category:{category}"
                        ),
                    )
                ]
            )

        rows.append(
            [
                InlineKeyboardButton(
                    "🔄 Refresh",
                    callback_data="index:categories",
                )
            ]
        )

        rows.append(
            [
                InlineKeyboardButton(
                    "🏠 Home",
                    callback_data="home",
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(
            rows
        )

        text = (
            "📚 **TEST INDEX**\n\n"
            "नीचे Category चुनें:"
        )

        await self._send_or_edit(
            update,
            context,
            text,
            keyboard,
            edit,
        )

    # ============================================================
    # EXAM
    # ============================================================

    async def show_exams(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        category: str,
    ):

        exams = db.get_exams(
            category
        )

        if not exams:

            return await self._edit_callback(
                update,
                "❌ इस Category में कोई Exam नहीं मिला।",
                InlineKeyboardMarkup(
                    [
                        self.back_button()
                    ]
                ),
            )

        rows = []

        for exam in exams:

            rows.append(
                [
                    InlineKeyboardButton(
                        f"🎯 {exam}",
                        callback_data=(
                            "index:exam:"
                            f"{self._pack(category)}:"
                            f"{self._pack(exam)}"
                        ),
                    )
                ]
            )

        rows.append(
            self.back_button()
        )

        keyboard = InlineKeyboardMarkup(
            rows
        )

        text = (
            f"📚 Category: **{category}**\n\n"
            "🎯 **Exam चुनें:**"
        )

        await self._edit_callback(
            update,
            text,
            keyboard,
        )

    # ============================================================
    # TEST TYPE
    # ============================================================

    async def show_test_types(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        category: str,
        exam: str,
    ):

        types = db.get_test_types(
            category,
            exam,
        )

        if not types:

            return await self._edit_callback(
                update,
                "❌ इस Exam में कोई Test Type नहीं मिला।",
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "⬅️ Back",
                                callback_data=(
                                    "index:category:"
                                    f"{self._pack(category)}"
                                ),
                            )
                        ]
                    ]
                ),
            )

        rows = []

        for test_type in types:

            icon = (
                "📄"
                if test_type.upper() == "PYQ"
                else "📝"
            )

            rows.append(
                [
                    InlineKeyboardButton(
                        f"{icon} {test_type}",
                        callback_data=(
                            "index:type:"
                            f"{self._pack(category)}:"
                            f"{self._pack(exam)}:"
                            f"{self._pack(test_type)}"
                        ),
                    )
                ]
            )

        rows.append(
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data=(
                        "index:category:"
                        f"{self._pack(category)}"
                    ),
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(
            rows
        )

        text = (
            f"📚 **{category}**\n"
            f"🎯 **{exam}**\n\n"
            "📝 **Test Type चुनें:**"
        )

        await self._edit_callback(
            update,
            text,
            keyboard,
        )

    # ============================================================
    # YEAR
    # ============================================================

    async def show_years(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        category: str,
        exam: str,
        test_type: str,
    ):

        years = db.get_years(
            category,
            exam,
            test_type,
        )

        if not years:

            return await self._edit_callback(
                update,
                "❌ इस section में Year उपलब्ध नहीं है।",
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "⬅️ Back",
                                callback_data=(
                                    "index:exam:"
                                    f"{self._pack(category)}:"
                                    f"{self._pack(exam)}"
                                ),
                            )
                        ]
                    ]
                ),
            )

        rows = []

        # --------------------------------------------------------
        # Year buttons
        # --------------------------------------------------------

        row = []

        for year in years:

            row.append(
                InlineKeyboardButton(
                    f"📅 {year}",
                    callback_data=(
                        "index:year:"
                        f"{self._pack(category)}:"
                        f"{self._pack(exam)}:"
                        f"{self._pack(test_type)}:"
                        f"{self._pack(year)}"
                    ),
                )
            )

            # 2 buttons per row
            if len(row) == 2:

                rows.append(
                    row
                )

                row = []

        if row:

            rows.append(
                row
            )

        rows.append(
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data=(
                        "index:exam:"
                        f"{self._pack(category)}:"
                        f"{self._pack(exam)}"
                    ),
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(
            rows
        )

        text = (
            f"📚 **{category}**\n"
            f"🎯 **{exam}**\n"
            f"📝 **{test_type}**\n\n"
            "📅 **Year चुनें:**"
        )

        await self._edit_callback(
            update,
            text,
            keyboard,
        )

    # ============================================================
    # TEST LIST
    # ============================================================

    async def show_tests(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        category: str,
        exam: str,
        test_type: str,
        year: str,
    ):

        test_list = db.get_tests(
            category,
            exam,
            test_type,
            year,
            limit=50,
        )

        if not test_list:

            return await self._edit_callback(
                update,
                "❌ इस Year में कोई Test नहीं मिला।",
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "⬅️ Back",
                                callback_data=(
                                    "index:type:"
                                    f"{self._pack(category)}:"
                                    f"{self._pack(exam)}:"
                                    f"{self._pack(test_type)}"
                                ),
                            )
                        ]
                    ]
                ),
            )

        rows = []

        for test in test_list:

            title = (
                test.get(
                    "title",
                    "Untitled Test",
                )
            )

            # Telegram callback_data limit के लिए
            # title के बजाय test_id use होगा।
            label = self._shorten(
                title,
                50,
            )

            rows.append(
                [
                    InlineKeyboardButton(
                        f"📄 {label}",
                        callback_data=(
                            "index:test:"
                            f"{test.get('test_id')}"
                        ),
                    )
                ]
            )

        rows.append(
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data=(
                        "index:year:"
                        f"{self._pack(category)}:"
                        f"{self._pack(exam)}:"
                        f"{self._pack(test_type)}:"
                        f"{self._pack(year)}"
                    ),
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(
            rows
        )

        text = (
            f"📚 **{category}**\n"
            f"🎯 **{exam}**\n"
            f"📝 **{test_type}**\n"
            f"📅 **{year}**\n\n"
            f"📚 **Tests: {len(test_list)}**\n\n"
            "नीचे Test चुनें:"
        )

        await self._edit_callback(
            update,
            text,
            keyboard,
        )

    # ============================================================
    # TEST DETAILS
    # ============================================================

    async def show_test_details(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        test_id: str,
    ):

        test = db.get_test(
            test_id
        )

        if not test:

            return await self._edit_callback(
                update,
                "❌ Test नहीं मिला।",
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📚 Test Index",
                                callback_data=(
                                    "index:categories"
                                ),
                            )
                        ]
                    ]
                ),
            )

        title = test.get(
            "title",
            "Untitled Test",
        )

        exam = test.get(
            "exam",
            "Other",
        )

        test_type = test.get(
            "type",
            test.get(
                "test_type",
                "Other",
            ),
        )

        year = test.get(
            "year",
            "Other",
        )

        question_count = test.get(
            "question_count",
            0,
        )

        language = test.get(
            "language",
            "Hindi",
        )

        shift = test.get(
            "shift",
            "",
        )

        extract_count = test.get(
            "extract_count",
            0,
        )

        # --------------------------------------------------------
        # Details
        # --------------------------------------------------------

        text = (
            "📚 **TEST DETAILS**\n\n"

            f"📝 **{title}**\n\n"

            f"🎯 Exam: **{exam}**\n"
            f"📂 Type: **{test_type}**\n"
            f"📅 Year: **{year}**\n"
            f"❓ Questions: **{question_count}**\n"
            f"🌐 Language: **{language}**\n"
        )

        if shift:

            text += (
                f"🔄 Shift: **{shift}**\n"
            )

        text += (
            f"📊 Extracted: **{extract_count}** times\n"
        )

        # --------------------------------------------------------
        # Buttons
        # --------------------------------------------------------

        rows = []

        # Test Extract
        rows.append(
            [
                InlineKeyboardButton(
                    "🚀 EXTRACT TEST",
                    callback_data=(
                        f"extract_test:{test_id}"
                    ),
                )
            ]
        )

        # Direct open if URL exists
        github_url = test.get(
            "github_url"
        )

        if github_url:

            rows.append(
                [
                    InlineKeyboardButton(
                        "🌐 OPEN TEST",
                        url=github_url,
                    )
                ]
            )

        rows.append(
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data=(
                        "index:categories"
                    ),
                ),
                InlineKeyboardButton(
                    "🏠 Home",
                    callback_data="home",
                ),
            ]
        )

        keyboard = InlineKeyboardMarkup(
            rows
        )

        await self._edit_callback(
            update,
            text,
            keyboard,
        )

    # ============================================================
    # EXTRACT TEST
    # ============================================================

    async def extract_test(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        test_id: str,
    ):

        user = update.effective_user

        if not user:

            return

        # --------------------------------------------------------
        # Access
        # --------------------------------------------------------

        if not await telegram_utils.check_user_access(
            update,
            context,
        ):

            return

        test = db.get_test(
            test_id
        )

        if not test:

            return await self._edit_callback(
                update,
                "❌ Test उपलब्ध नहीं है।",
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📚 Test Index",
                                callback_data=(
                                    "index:categories"
                                ),
                            )
                        ]
                    ]
                ),
            )

        # --------------------------------------------------------
        # Record extract
        #
        # Actual queue processing अगली layer में होगा।
        # --------------------------------------------------------

        is_paid = db.is_paid_user(
            user.id
        )

        priority_text = (
            "💎 Premium Priority"
            if is_paid
            else "🆓 Normal Queue"
        )

        text = (
            "⏳ **Test Extract Request**\n\n"
            f"📚 {test.get('title', 'Test')}\n"
            f"{priority_text}\n\n"
            "⚙️ आपका request queue में लगाया जा रहा है..."
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ Cancel",
                        callback_data=(
                            "extract_cancel:"
                            f"{test_id}"
                        ),
                    )
                ]
            ]
        )

        await self._edit_callback(
            update,
            text,
            keyboard,
        )

        # --------------------------------------------------------
        # Activity log
        # --------------------------------------------------------

        await telegram_utils.log_user_activity(
            context,
            user.id,
            "TEST_EXTRACT_REQUEST",
            (
                f"Test ID: {test_id}\n"
                f"Test: {test.get('title', '-')}"
            ),
        )

    # ============================================================
    # CALLBACK ROUTER
    # ============================================================

    async def handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        query = update.callback_query

        if not query:

            return

        data = query.data or ""

        await telegram_utils.answer_callback(
            query
        )

        # --------------------------------------------------------
        # Categories
        # --------------------------------------------------------

        if data == "index:categories":

            return await self.show_categories(
                update,
                context,
                edit=True,
            )

        # --------------------------------------------------------
        # Category
        # --------------------------------------------------------

        if data.startswith(
            "index:category:"
        ):

            category = self._unpack(
                data[
                    len("index:category:"):
                ]
            )

            return await self.show_exams(
                update,
                context,
                category,
            )

        # --------------------------------------------------------
        # Exam
        # --------------------------------------------------------

        if data.startswith(
            "index:exam:"
        ):

            parts = data.split(
                ":"
            )

            if len(parts) < 4:

                return

            category = self._unpack(
                parts[2]
            )

            exam = self._unpack(
                parts[3]
            )

            return await self.show_test_types(
                update,
                context,
                category,
                exam,
            )

        # --------------------------------------------------------
        # Type
        # --------------------------------------------------------

        if data.startswith(
            "index:type:"
        ):

            parts = data.split(
                ":"
            )

            if len(parts) < 5:

                return

            category = self._unpack(
                parts[2]
            )

            exam = self._unpack(
                parts[3]
            )

            test_type = self._unpack(
                parts[4]
            )

            return await self.show_years(
                update,
                context,
                category,
                exam,
                test_type,
            )

        # --------------------------------------------------------
        # Year
        # --------------------------------------------------------

        if data.startswith(
            "index:year:"
        ):

            parts = data.split(
                ":"
            )

            if len(parts) < 6:

                return

            category = self._unpack(
                parts[2]
            )

            exam = self._unpack(
                parts[3]
            )

            test_type = self._unpack(
                parts[4]
            )

            year = self._unpack(
                parts[5]
            )

            return await self.show_tests(
                update,
                context,
                category,
                exam,
                test_type,
                year,
            )

        # --------------------------------------------------------
        # Test
        # --------------------------------------------------------

        if data.startswith(
            "index:test:"
        ):

            test_id = data[
                len("index:test:"):
            ]

            return await self.show_test_details(
                update,
                context,
                test_id,
            )

        # --------------------------------------------------------
        # Extract
        # --------------------------------------------------------

        if data.startswith(
            "extract_test:"
        ):

            test_id = data[
                len("extract_test:")
            ]

            return await self.extract_test(
                update,
                context,
                test_id,
            )

        # --------------------------------------------------------
        # Cancel
        # --------------------------------------------------------

        if data.startswith(
            "extract_cancel:"
        ):

            return await self._edit_callback(
                update,
                "❌ Extract request cancel कर दिया गया।",
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📚 Test Index",
                                callback_data=(
                                    "index:categories"
                                ),
                            )
                        ]
                    ]
                ),
            )

    # ============================================================
    # SEND / EDIT HELPERS
    # ============================================================

    async def _send_or_edit(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        keyboard: InlineKeyboardMarkup,
        edit: bool = False,
    ):

        if edit and update.callback_query:

            try:

                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )

                return

            except Exception:

                pass

        message = update.effective_message

        if message:

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

    async def _edit_callback(
        self,
        update: Update,
        text: str,
        keyboard: InlineKeyboardMarkup,
    ):

        query = update.callback_query

        if not query:

            return

        try:

            await query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

        except Exception as exc:

            logger.warning(
                "Index message edit failed: %s",
                exc,
            )

    # ============================================================
    # PACK / UNPACK
    # ============================================================

    @staticmethod
    def _pack(
        value: str,
    ) -> str:

        """
        callback_data में ':' नहीं आना चाहिए।
        """

        value = str(
            value or ""
        )

        return (
            value
            .replace(
                "%",
                "%25",
            )
            .replace(
                ":",
                "%3A",
            )
            .replace(
                "|",
                "%7C",
            )
        )

    @staticmethod
    def _unpack(
        value: str,
    ) -> str:

        return (
            value
            .replace(
                "%7C",
                "|",
            )
            .replace(
                "%3A",
                ":",
            )
            .replace(
                "%25",
                "%",
            )
        )

    # ============================================================
    # SHORTEN
    # ============================================================

    @staticmethod
    def _shorten(
        text: str,
        length: int,
    ) -> str:

        text = str(
            text or ""
        )

        if len(text) <= length:

            return text

        return (
            text[: length - 3]
            + "..."
        )


# ================================================================
# SINGLE INSTANCE
# ================================================================

index_handlers = IndexHandlers()

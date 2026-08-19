import asyncio
import logging
from typing import Any, Dict, Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
)

from .config import CONFIG
from .database import db
from .github import github
from .telegram_utils import telegram_utils
from .queue_manager import queue_manager
from telegram import Update, Message

logger = logging.getLogger(__name__)


class ExtractHandlers:
    """
    USER TEST EXTRACTION SYSTEM

    Flow:

        Test Index
             ↓
        Test selected
             ↓
        Access check
             ↓
        Paid user priority
             ↓
        Queue
             ↓
        GitHub TCS HTML
             ↓
        Database channel backup
             ↓
        User receives Test
             ↓
        Extraction statistics update

    High-load design:

        FREE USER  → Normal Queue
        PAID USER  → Priority Queue

    MongoDB:
        Questions JSON save नहीं होता।
        केवल test metadata/reference save होता है।
    """

    # ============================================================
    # TEST DETAILS
    # ============================================================
    # ============================================================
    # REGISTER HANDLERS
    # ============================================================

    def register(self, application):
        """
        Register all extraction related Telegram callbacks.

        Usage:
            extract_handlers.register(application)
        """

        # Test details
        application.add_handler(
            CallbackQueryHandler(
                self._test_callback,
                pattern=r"^test:"
            )
        )

        # Extract button
        application.add_handler(
            CallbackQueryHandler(
                self._extract_callback,
                pattern=r"^extract:"
            )
        )

        # Extract confirmation
        application.add_handler(
            CallbackQueryHandler(
                self._extract_confirm_callback,
                pattern=r"^extract_confirm:"
            )
        )

        # Retry extraction
        application.add_handler(
            CallbackQueryHandler(
                self._retry_callback,
                pattern=r"^retry_extract:"
            )
        )

        logger.info(
            "ExtractHandlers registered successfully."
        )


    async def _test_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        query = update.callback_query

        if not query:
            return

        data = query.data or ""

        await telegram_utils.answer_callback(query)

        test_id = data.split(
            ":",
            1
        )[1].strip()

        if not test_id:
            return await self._send_error(
                update,
                context,
                "❌ Invalid Test ID."
            )

        return await self.show_test(
            update,
            context,
            test_id,
        )


    async def _extract_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        query = update.callback_query

        if not query:
            return

        data = query.data or ""

        await telegram_utils.answer_callback(query)

        test_id = data.split(
            ":",
            1
        )[1].strip()

        if not test_id:
            return await self._send_error(
                update,
                context,
                "❌ Invalid Test ID."
            )

        return await self.confirm_extract(
            update,
            context,
            test_id,
        )


    async def _extract_confirm_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        query = update.callback_query

        if not query:
            return

        data = query.data or ""

        await telegram_utils.answer_callback(query)

        test_id = data.split(
            ":",
            1
        )[1].strip()

        if not test_id:
            return await self._send_error(
                update,
                context,
                "❌ Invalid Test ID."
            )

        return await self.create_extract_job(
            update,
            context,
            test_id,
        )


    async def _retry_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        query = update.callback_query

        if not query:
            return

        data = query.data or ""

        await telegram_utils.answer_callback(query)

        job_id = data.split(
            ":",
            1
        )[1].strip()

        if not job_id:
            return await self._send_error(
                update,
                context,
                "❌ Invalid Job ID."
            )

        return await self.retry_extract_job(
            update,
            context,
            job_id,
    )
    async def show_test(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        test_id: str,
    ):

        user = update.effective_user

        if not user:
            return

        # --------------------------------------------------------
        # User access
        # --------------------------------------------------------

        if not await telegram_utils.check_user_access(
            update,
            context,
        ):
            return

        # --------------------------------------------------------
        # Test metadata
        # --------------------------------------------------------

        test = db.get_test(
            test_id
        )

        if not test:

            return await self._send_error(
                update,
                context,
                "❌ यह Test database में नहीं मिला।",
            )

        if not test.get(
            "ready",
            True,
        ):

            return await self._send_error(
                update,
                context,
                (
                    "⏳ यह Test अभी processing में है।\n"
                    "थोड़ी देर बाद फिर try करें।"
                ),
            )

        # --------------------------------------------------------
        # Maintenance
        # --------------------------------------------------------

        if db.get_setting(
            "extract_enabled",
            True,
        ) is False:

            return await self._send_error(
                update,
                context,
                (
                    "🛠️ Test Extract service अभी temporarily "
                    "disabled है।"
                ),
            )

        # --------------------------------------------------------
        # Paid status
        # --------------------------------------------------------

        paid = db.is_paid_user(
            user.id
        )

        queue_status = db.get_queue_status()

        normal_queue = queue_status.get(
            "normal_queued",
            queue_status.get(
                "queued",
                0,
            ),
        )

        priority_queue = queue_status.get(
            "priority_queued",
            0,
        )

        text = (
            "📚 **TEST DETAILS**\n\n"
            f"🆔 Test ID: `{test.get('test_id', test_id)}`\n"
            f"📚 Series: {test.get('series', '-')}\n"
            f"🎯 Exam: **{test.get('exam', '-') }**\n"
            f"🗂 Section: {test.get('section', '-')}\n"
            f"📁 Subsection: {test.get('subsection', '-')}\n"
            f"📝 Test: **{test.get('title', '-') }**\n"
            f"📅 Year: {test.get('year', '-')}\n"
            f"❓ Questions: **{test.get('question_count', 0)}**\n"
            f"🌐 Language: {test.get('language', 'Hindi')}\n"
            f"📌 Type: {test.get('test_type', '-')}\n"
        )

        if test.get("shift"):

            text += (
                f"🕐 Shift: {test.get('shift')}\n"
            )

        text += (
            "\n"
            f"👤 Your Status: "
            f"{'💎 PAID' if paid else '🆓 FREE'}\n\n"
            "⚡ **Queue Status**\n"
            f"💎 Priority: {priority_queue}\n"
            f"🆓 Normal: {normal_queue}\n\n"
            "Extract करने के लिए नीचे button दबाएँ।"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🚀 EXTRACT TEST",
                        callback_data=(
                            f"extract:{test_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ BACK TO INDEX",
                        callback_data="index:categories",
                    ),
                ],
            ]
        )

        await self._edit_or_send(
            update,
            context,
            text,
            keyboard,
        )

    # ============================================================
    # EXTRACT CONFIRMATION
    # ============================================================

    async def confirm_extract(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        test_id: str,
    ):

        user = update.effective_user

        if not user:

            return

        if not await telegram_utils.check_user_access(
            update,
            context,
        ):
            return

        test = db.get_test(
            test_id
        )

        if not test:

            return await self._send_error(
                update,
                context,
                "❌ Test नहीं मिला।",
            )

        # --------------------------------------------------------
        # User access
        # --------------------------------------------------------

        access = db.check_extract_access(
            user.id
        )

        if not access.get(
            "allowed",
            True,
        ):

            reason = access.get(
                "reason",
                "Extract limit समाप्त हो गया।",
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💎 PREMIUM",
                            callback_data="menu:premium",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🆓 FREE TRIAL",
                            callback_data="menu:trial",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🏠 HOME",
                            callback_data="home",
                        )
                    ],
                ]
            )

            return await self._edit_or_send(
                update,
                context,
                f"❌ **EXTRACT LIMIT**\n\n{reason}",
                keyboard,
            )

        paid = db.is_paid_user(
            user.id
        )

        # --------------------------------------------------------
        # Duplicate running request
        # --------------------------------------------------------

        existing = db.get_active_extract_job(
            user.id,
            test_id,
        )

        if existing:

            return await self.show_job_status(
                update,
                context,
                existing.get(
                    "job_id"
                ),
            )

        # --------------------------------------------------------
        # Priority
        # --------------------------------------------------------

        priority = (
            100
            if paid
            else 10
        )

        # --------------------------------------------------------
        # Confirmation UI
        # --------------------------------------------------------

        queue_status = db.get_queue_status()

        if paid:

            queue_message = (
                "💎 **PAID PRIORITY ENABLED**\n"
                "आपका request priority queue में जाएगा।"
            )

        else:

            queue_message = (
                "🆓 आपका request normal queue में जाएगा।"
            )

        text = (
            "🚀 **EXTRACT TEST**\n\n"
            f"📝 {test.get('title', '-')}\n"
            f"❓ Questions: {test.get('question_count', 0)}\n\n"
            f"{queue_message}\n\n"
            "क्या आप Test Extract करना चाहते हैं?"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ YES, EXTRACT",
                        callback_data=(
                            f"extract_confirm:{test_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ CANCEL",
                        callback_data=(
                            f"test:{test_id}"
                        ),
                    )
                ],
            ]
        )

        await self._edit_or_send(
            update,
            context,
            text,
            keyboard,
        )

    # ============================================================
    # CREATE EXTRACTION JOB
    # ============================================================

    async def create_extract_job(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        test_id: str,
    ):

        user = update.effective_user

        query = update.callback_query

        if not user:

            return

        if not await telegram_utils.check_user_access(
            update,
            context,
        ):
            return

        test = db.get_test(
            test_id
        )

        if not test:

            return await self._send_error(
                update,
                context,
                "❌ Test नहीं मिला।",
            )

        # --------------------------------------------------------
        # Access
        # --------------------------------------------------------

        access = db.check_extract_access(
            user.id
        )

        if not access.get(
            "allowed",
            True,
        ):

            return await self._send_error(
                update,
                context,
                access.get(
                    "reason",
                    "Extract not allowed.",
                ),
            )

        # --------------------------------------------------------
        # Paid first
        # --------------------------------------------------------

        paid = db.is_paid_user(
            user.id
        )

        priority = (
            100
            if paid
            else 10
        )

        # --------------------------------------------------------
        # Prevent duplicate
        # --------------------------------------------------------

        active = db.get_active_extract_job(
            user.id,
            test_id,
        )

        if active:

            return await self.show_job_status(
                update,
                context,
                active.get(
                    "job_id"
                ),
            )

        # --------------------------------------------------------
        # Create DB record
        # --------------------------------------------------------

        job_id = db.create_extract_job(
            user_id=user.id,
            test_id=test_id,
            priority=priority,
            is_paid=paid,
        )

        # --------------------------------------------------------
        # Queue
        # --------------------------------------------------------

        try:

            queue_job_id = await queue_manager.add_job(
                user_id=user.id,
                job_type="test_extract",
                payload={
                    "test_id": test_id,
                    "user_id": user.id,
                    "is_paid": paid,
                },
                priority=priority,
            )

            db.attach_queue_job(
                job_id,
                queue_job_id,
            )

        except Exception:

            logger.exception(
                "Failed to add extraction job"
            )

            db.mark_extract_failed(
                job_id,
                "Queue service unavailable",
            )

            return await self._send_error(
                update,
                context,
                (
                    "❌ अभी server busy है।\n"
                    "कृपया थोड़ी देर बाद retry करें।"
                ),
            )

        # --------------------------------------------------------
        # User progress message
        # --------------------------------------------------------

        status_message = await self._send_status(
            update,
            context,
            (
                "🚀 **EXTRACT REQUEST ACCEPTED**\n\n"
                f"🆔 Job: `{job_id}`\n"
                f"📝 {test.get('title', '-')}\n\n"
                "⏳ Queue में add हो गया है...\n"
                "आपको live progress यहीं मिलेगा।"
            ),
        )

        if status_message:

            db.attach_status_message(
                job_id,
                status_message.message_id,
            )

        # --------------------------------------------------------
        # User activity
        # --------------------------------------------------------

        await telegram_utils.log_user_activity(
            context,
            user.id,
            "TEST_EXTRACT_REQUEST",
            extra={
                "test_id": test_id,
                "job_id": job_id,
                "paid": paid,
            },
        )

        # --------------------------------------------------------
        # Extract count reservation
        # --------------------------------------------------------

        db.reserve_extract(
            user.id,
            test_id,
            job_id,
        )

        # --------------------------------------------------------
        # Immediately show queue
        # --------------------------------------------------------

        queue_status = db.get_queue_status()

        await self.update_job_message(
            context,
            job_id,
            (
                "⚡ **QUEUE STATUS**\n\n"
                f"🆔 Job: `{job_id}`\n"
                f"{'💎 PAID PRIORITY' if paid else '🆓 NORMAL QUEUE'}\n\n"
                f"💎 Priority Queue: "
                f"{queue_status.get('priority_queued', 0)}\n"
                f"🆓 Normal Queue: "
                f"{queue_status.get('normal_queued', 0)}\n\n"
                "⏳ Processing का wait करें..."
            ),
        )

    # ============================================================
    # PROCESS EXTRACT JOB
    # ============================================================

    async def process_extract_job(
        self,
        job: Dict[str, Any],
    ) -> Dict[str, Any]:

        queue_job_id = job.get(
            "job_id"
        )

        payload = job.get(
            "payload",
            {},
        )

        user_id = int(
            payload.get(
                "user_id"
            )
        )

        test_id = str(
            payload.get(
                "test_id"
            )
        )

        # --------------------------------------------------------
        # MongoDB job
        # --------------------------------------------------------

        extract_job = db.get_extract_job_by_queue_id(
            queue_job_id
        )

        if not extract_job:

            raise ValueError(
                "Extraction job record नहीं मिला।"
            )

        internal_job_id = extract_job.get(
            "job_id"
        )

        test = db.get_test(
            test_id
        )

        if not test:

            raise ValueError(
                "Requested test not found."
            )

        # --------------------------------------------------------
        # Stage 1
        # --------------------------------------------------------

        await self.progress(
            internal_job_id,
            5,
            "🔍 Test information verify हो रही है...",
        )

        # --------------------------------------------------------
        # Stage 2
        # --------------------------------------------------------

        github_path = test.get("github_path") or ""
        html = ""

        if github_path and CONFIG.github_token and CONFIG.github_owner and CONFIG.github_repo:
            await self.progress(
                internal_job_id, 20,
                "☁️ GitHub से TCS HTML locate किया जा रहा है...",
            )
            try:
                html = github.download_test(github_path) or ""
            except Exception:
                logger.exception("GitHub download failed; trying database backup.")

        # GitHub is optional. Use the stored Database backup as a reliable fallback.
        if not html:
            backup = db.get_backup(test_id) or {}
            html = backup.get("html") or ""

        if not html:
            raise ValueError("TCS HTML नहीं मिला। GitHub या Database backup configure करें।")

        await self.progress(
            internal_job_id,
            35,
            "📄 TCS HTML मिल गया।",
        )

        # --------------------------------------------------------
        # Validate HTML
        # --------------------------------------------------------

        if (
            "<html" not in html.lower()
            and "<!doctype" not in html.lower()
        ):

            raise ValueError(
                "GitHub file valid HTML नहीं है।"
            )

        await self.progress(
            internal_job_id,
            45,
            "✅ Test file validated.",
        )

        # --------------------------------------------------------
        # Database channel
        # --------------------------------------------------------

        await self.progress(
            internal_job_id,
            55,
            "📢 Database channel से backup verify किया जा रहा है...",
        )

        # --------------------------------------------------------
        # Get bot
        # --------------------------------------------------------

        bot = queue_manager.bot

        if bot is None:

            raise RuntimeError(
                "Telegram bot instance unavailable."
            )

        # --------------------------------------------------------
        # Send/copy test to database channel
        # --------------------------------------------------------

        database_message = None

        try:

            database_message = (
                await telegram_utils.send_database_test(
                    bot=bot,
                    html=html.encode(
                        "utf-8"
                    ),
                    filename="tcs.html",
                    caption=(
                        "📚 TEST DATABASE\n\n"
                        f"🆔 Test ID: `{test_id}`\n"
                        f"📝 {test.get('title', '-')}\n"
                        f"🎯 {test.get('exam', '-')}\n"
                        f"❓ {test.get('question_count', 0)}"
                    ),
                )
            )

        except Exception:

            logger.exception(
                "Database channel backup failed"
            )

            # Database channel backup fail होने पर
            # extraction पूरी तरह fail नहीं करेंगे।
            database_message = None

        await self.progress(
            internal_job_id,
            70,
            "📦 Test response तैयार हो रहा है...",
        )

        # --------------------------------------------------------
        # Update extraction stats
        # --------------------------------------------------------

        db.increment_extract_count(
            test_id
        )

        db.mark_extract_success(
            internal_job_id
        )

        await self.progress(
            internal_job_id,
            85,
            "📊 Extraction statistics update हो रही हैं...",
        )

        # --------------------------------------------------------
        # Return
        # --------------------------------------------------------

        return {
            "job_id": internal_job_id,
            "queue_job_id": queue_job_id,
            "user_id": user_id,
            "test_id": test_id,
            "title": test.get(
                "title",
                "",
            ),
            "github_path": github_path,
            "github_url": test.get(
                "github_url",
                "",
            ),
            "html": html,
            "database_message_id": (
                database_message.message_id
                if database_message
                else None
            ),
        }

    # ============================================================
    # COMPLETE JOB
    # ============================================================

    async def complete_job(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        result: Dict[str, Any],
    ):

        job_id = result.get(
            "job_id"
        )

        user_id = result.get(
            "user_id"
        )

        test_id = result.get(
            "test_id"
        )

        title = result.get(
            "title",
            "Test",
        )

        github_url = result.get(
            "github_url"
        )

        html = result.get(
            "html"
        )

        database_message_id = result.get(
            "database_message_id"
        )

        # --------------------------------------------------------
        # User result
        # --------------------------------------------------------

        keyboard_rows = []

        # Direct GitHub
        if github_url:

            keyboard_rows.append(
                [
                    InlineKeyboardButton(
                        "🌐 OPEN TEST",
                        url=github_url,
                    )
                ]
            )

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    "📚 MORE TESTS",
                    callback_data="index:categories",
                ),
                InlineKeyboardButton(
                    "🏠 HOME",
                    callback_data="home",
                ),
            ]
        )

        text = (
            "🎉 **TEST EXTRACTED SUCCESSFULLY!**\n\n"
            f"📝 **{title}**\n"
            f"🆔 Test ID: `{test_id}`\n\n"
            "✅ Test ready है।\n"
        )

        if github_url:

            text += (
                "\n🌐 नीचे **OPEN TEST** button से "
                "Test open करें।"
            )

        else:

            text += (
                "\n📦 Test database channel में available है।"
            )

        try:

            await telegram_utils.send_message(
                context.bot,
                user_id,
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    keyboard_rows
                ),
            )

        except Exception:

            logger.exception(
                "Could not send extract result"
            )

        # --------------------------------------------------------
        # Optional direct HTML
        # --------------------------------------------------------

        # IMPORTANT:
        # Default रूप से GitHub link दिया जाता है।
        # इससे Telegram पर बहुत बड़ी HTML file
        # हर extraction पर भेजने से load कम रहता है।
        #
        # अगर config में direct file enabled है,
        # तब HTML भी भेज सकते हैं।

        if (
            CONFIG.send_extracted_html
            and html
        ):

            try:

                await telegram_utils.send_document_bytes(
                    context.bot,
                    user_id,
                    html.encode(
                        "utf-8"
                    ),
                    "tcs.html",
                    caption=(
                        f"📚 {title}\n"
                        "✅ Extracted Test"
                    ),
                )

            except Exception:

                logger.exception(
                    "Direct HTML send failed"
                )

        # --------------------------------------------------------
        # User activity
        # --------------------------------------------------------

        await telegram_utils.log_user_activity(
            context,
            user_id,
            "TEST_EXTRACT_SUCCESS",
            extra={
                "test_id": test_id,
                "job_id": job_id,
            },
        )

        # --------------------------------------------------------
        # Finish DB
        # --------------------------------------------------------

        db.finalize_extract(
            job_id,
            status="completed",
            database_message_id=database_message_id,
        )

        await self.progress(
            job_id,
            100,
            "🎉 Test successfully delivered.",
        )

    # ============================================================
    # FAILED JOB
    # ============================================================

    async def failed_job(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        job: Dict[str, Any],
        error: str,
    ):

        job_id = job.get(
            "job_id"
        )

        extract_job = db.get_extract_job(
            job_id
        )

        if not extract_job:

            return

        user_id = extract_job.get(
            "user_id"
        )

        test_id = extract_job.get(
            "test_id"
        )

        retry_count = extract_job.get(
            "retry_count",
            0,
        )

        # --------------------------------------------------------
        # Retry limit
        # --------------------------------------------------------

        max_retry = CONFIG.extract_max_retries

        if retry_count < max_retry:

            db.increment_extract_retry(
                job_id,
                error,
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔄 RETRY",
                            callback_data=(
                                f"retry_extract:{job_id}"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📚 TEST INDEX",
                            callback_data="index:categories",
                        )
                    ],
                ]
            )

            try:

                await telegram_utils.send_message(
                    context.bot,
                    user_id,
                    (
                        "⚠️ **TEST EXTRACTION FAILED**\n\n"
                        f"🆔 Job: `{job_id}`\n"
                        f"❌ Error: {error[:500]}\n\n"
                        "आप Retry button दबाकर फिर try कर सकते हैं।"
                    ),
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )

            except Exception:

                logger.exception(
                    "Failed notification error"
                )

            await self.progress(
                job_id,
                0,
                (
                    f"❌ Failed. Retry "
                    f"{retry_count + 1}/{max_retry} available."
                ),
            )

            return

        # --------------------------------------------------------
        # Final failure
        # --------------------------------------------------------

        db.mark_extract_failed(
            job_id,
            error,
        )

        try:

            await telegram_utils.send_message(
                context.bot,
                user_id,
                (
                    "❌ **TEST EXTRACTION FAILED**\n\n"
                    f"🆔 Job: `{job_id}`\n\n"
                    "Automatic retry limit complete हो गई है।\n"
                    "Admin को issue report कर दिया गया है।"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔄 TRY AGAIN",
                                callback_data=(
                                    f"retry_test:{test_id}"
                                ),
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "📞 REPORT",
                                callback_data="menu:report",
                            )
                        ],
                    ]
                ),
            )

        except Exception:

            logger.exception(
                "Final failure notification failed"
            )

        await telegram_utils.log_user_activity(
            context,
            user_id,
            "TEST_EXTRACT_FAILED",
            extra={
                "test_id": test_id,
                "job_id": job_id,
                "error": error,
            },
        )

    # ============================================================
    # RETRY
    # ============================================================

    async def retry_extract_job(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        job_id: str,
    ):

        user = update.effective_user

        if not user:

            return

        job = db.get_extract_job(
            job_id
        )

        if not job:

            return await self._send_error(
                update,
                context,
                "❌ Extraction job नहीं मिला।",
            )

        if int(
            job.get(
                "user_id"
            )
        ) != user.id:

            return await self._send_error(
                update,
                context,
                "🚫 यह आपका extraction job नहीं है।",
            )

        if job.get(
            "status"
        ) == "completed":

            return await self._send_error(
                update,
                context,
                "✅ यह Test पहले ही successfully extract हो चुका है।",
            )

        test_id = job.get(
            "test_id"
        )

        # --------------------------------------------------------
        # New job
        # --------------------------------------------------------

        test = db.get_test(
            test_id
        )

        if not test:

            return await self._send_error(
                update,
                context,
                "❌ Test नहीं मिला।",
            )

        paid = db.is_paid_user(
            user.id
        )

        priority = (
            100
            if paid
            else 10
        )

        new_job_id = db.create_extract_job(
            user_id=user.id,
            test_id=test_id,
            priority=priority,
            is_paid=paid,
            retry_of=job_id,
        )

        try:

            queue_job_id = await queue_manager.add_job(
                user_id=user.id,
                job_type="test_extract",
                payload={
                    "test_id": test_id,
                    "user_id": user.id,
                    "is_paid": paid,
                    "retry_of": job_id,
                },
                priority=priority,
            )

            db.attach_queue_job(
                new_job_id,
                queue_job_id,
            )

        except Exception:

            db.mark_extract_failed(
                new_job_id,
                "Queue unavailable",
            )

            return await self._send_error(
                update,
                context,
                "❌ Server queue अभी unavailable है।",
            )

        status_message = await self._send_status(
            update,
            context,
            (
                "🔄 **RETRY STARTED**\n\n"
                f"🆔 New Job: `{new_job_id}`\n"
                f"📝 {test.get('title', '-')}\n\n"
                "⏳ Queue में add हो गया।"
            ),
        )

        if status_message:

            db.attach_status_message(
                new_job_id,
                status_message.message_id,
            )

    # ============================================================
    # JOB STATUS
    # ============================================================

    async def show_job_status(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        job_id: str,
    ):

        job = db.get_extract_job(
            job_id
        )

        if not job:

            return await self._send_error(
                update,
                context,
                "❌ Job नहीं मिला।",
            )

        status = job.get(
            "status",
            "queued",
        )

        progress = job.get(
            "progress",
            0,
        )

        test = db.get_test(
            job.get(
                "test_id"
            )
        )

        title = (
            test.get(
                "title",
                "Test",
            )
            if test
            else "Test"
        )

        if status == "completed":

            text = (
                "✅ **TEST COMPLETED**\n\n"
                f"📝 {title}\n"
                f"🆔 Job: `{job_id}`"
            )

        elif status == "failed":

            text = (
                "❌ **TEST FAILED**\n\n"
                f"📝 {title}\n"
                f"🆔 Job: `{job_id}`\n"
                f"❌ {job.get('error', '-')[:500]}"
            )

        else:

            text = (
                "⚡ **TEST PROCESSING**\n\n"
                f"📝 {title}\n"
                f"🆔 Job: `{job_id}`\n\n"
                f"📊 Progress: **{progress}%**\n"
                f"📌 Status: **{status}**\n"
                f"💬 {job.get('progress_message', 'Processing...')}"
            )

        keyboard_rows = []

        if status == "failed":

            keyboard_rows.append(
                [
                    InlineKeyboardButton(
                        "🔄 RETRY",
                        callback_data=(
                            f"retry_extract:{job_id}"
                        ),
                    )
                ]
            )

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    "📚 TEST INDEX",
                    callback_data="index:categories",
                )
            ]
        )

        await self._edit_or_send(
            update,
            context,
            text,
            InlineKeyboardMarkup(
                keyboard_rows
            ),
        )

    # ============================================================
    # LIVE PROGRESS
    # ============================================================

    async def progress(
        self,
        job_id: str,
        percentage: int,
        message: str,
    ):

        db.update_extract_progress(
            job_id,
            percentage,
            message,
        )

        status_message_id = db.get_status_message_id(
            job_id
        )

        if not status_message_id:

            return

        job = db.get_extract_job(
            job_id
        )

        if not job:

            return

        user_id = job.get(
            "user_id"
        )

        bot = queue_manager.bot

        if not bot:

            return

        # --------------------------------------------------------
        # Rate limited live updates
        # --------------------------------------------------------

        if not db.should_update_progress(
            job_id
        ):

            return

        try:

            text = (
                "⚙️ **TEST EXTRACTING...**\n\n"
                f"🆔 Job: `{job_id}`\n\n"
                f"📊 Progress: **{percentage}%**\n"
                f"💬 {message}\n\n"
                "⏳ Please wait..."
            )

            await bot.edit_message_text(
                chat_id=user_id,
                message_id=status_message_id,
                text=text,
                parse_mode="Markdown",
            )

        except Exception:

            logger.debug(
                "Progress update failed",
                exc_info=True,
            )

    # ============================================================
    # STATUS MESSAGE
    # ============================================================

    async def _send_status(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
    ) -> Optional[Message]:

        message = update.effective_message

        if not message:

            return None

        try:

            return await context.bot.send_message(
                chat_id=message.chat_id,
                text=text,
                parse_mode="Markdown",
            )

        except Exception:

            logger.exception(
                "Could not send status"
            )

            return None

    # ============================================================
    # UPDATE JOB MESSAGE
    # ============================================================

    async def update_job_message(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        job_id: str,
        text: str,
    ):

        job = db.get_extract_job(
            job_id
        )

        if not job:

            return

        message_id = job.get(
            "status_message_id"
        )

        user_id = job.get(
            "user_id"
        )

        if not message_id:

            return

        try:

            await context.bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text=text,
                parse_mode="Markdown",
            )

        except Exception:

            logger.debug(
                "Job status edit failed",
                exc_info=True,
            )

    # ============================================================
    # GENERIC UI
    # ============================================================

    async def _edit_or_send(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        keyboard: Optional[
            InlineKeyboardMarkup
        ] = None,
    ):

        query = update.callback_query

        if query:

            try:

                await query.edit_message_text(
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )

                return

            except Exception:

                pass

        message = update.effective_message

        if message:

            await context.bot.send_message(
                chat_id=message.chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

    async def _send_error(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
    ):

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📚 TEST INDEX",
                        callback_data="index:categories",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 HOME",
                        callback_data="home",
                    )
                ],
            ]
        )

        await self._edit_or_send(
            update,
            context,
            text,
            keyboard,
        )


# Compatibility callback router used by main.py.
async def _extract_handle_callback(self, update, context):
    query = update.callback_query
    if not query:
        return
    data = query.data or ""
    if data.startswith("extract_confirm:"):
        return await self._extract_confirm_callback(update, context)
    if data.startswith("extract:"):
        return await self._extract_callback(update, context)
    if data.startswith("retry_extract:") or data.startswith("retry:"):
        # _retry_callback expects the job id after the first colon.
        return await self._retry_callback(update, context)
    if data.startswith("test:"):
        return await self._test_callback(update, context)

ExtractHandlers.handle_callback = _extract_handle_callback


# ================================================================
# SINGLE INSTANCE
# ================================================================

extract_handlers = ExtractHandlers()

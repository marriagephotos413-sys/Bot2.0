import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.helpers import safe_int
from app.database import db


logger = logging.getLogger(
    "telegram-test-series-bot.reports"
)


# ============================================================
# REPORT SERVICE
# ============================================================

class ReportService:
    """
    Bot reporting system.

    Reports:
    - Most extracted exams
    - Most extracted tests
    - Extraction success/failure
    - Upload success/failure
    - User activity
    - Daily activity
    - Paid-user activity
    - Failed upload retry information

    IMPORTANT:
    Test JSON MongoDB में store नहीं होगा.
    यहाँ केवल metadata/statistics रखे जा सकते हैं.
    """

    # ========================================================
    # DATABASE CALL
    # ========================================================

    async def _call_db(
        self,
        method_name: str,
        *args,
        **kwargs,
    ):

        method = getattr(
            db,
            method_name,
            None,
        )

        if not method:
            return None

        try:

            result = method(
                *args,
                **kwargs,
            )

            if hasattr(
                result,
                "__await__",
            ):

                result = await result

            return result

        except TypeError:

            try:

                result = method(
                    *args
                )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                return result

            except Exception:

                logger.debug(
                    "DB method failed: %s",
                    method_name,
                    exc_info=True,
                )

        except Exception:

            logger.exception(
                "DB method failed: %s",
                method_name,
            )

        return None

    # ========================================================
    # RECORD EXTRACTION
    # ========================================================

    async def record_extraction(
        self,
        user_id: int,
        test_id: Optional[str] = None,
        exam: Optional[str] = None,
        test_name: Optional[str] = None,
        success: bool = True,
        paid_user: bool = False,
    ) -> bool:

        data = {
            "user_id": int(user_id),
            "test_id": test_id,
            "exam": exam,
            "test_name": test_name,
            "success": bool(success),
            "paid_user": bool(paid_user),
            "created_at": datetime.now(
                timezone.utc
            ),
        }

        # Preferred DB method.

        result = await self._call_db(
            "record_extraction",
            data,
        )

        if result is not None:
            return bool(result)

        # Alternate method.

        result = await self._call_db(
            "log_extraction",
            data,
        )

        if result is not None:
            return bool(result)

        return False

    # ========================================================
    # RECORD UPLOAD
    # ========================================================

    async def record_upload(
        self,
        user_id: int,
        test_id: Optional[str] = None,
        test_name: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> bool:

        data = {
            "user_id": int(user_id),
            "test_id": test_id,
            "test_name": test_name,
            "success": bool(success),
            "error": error,
            "created_at": datetime.now(
                timezone.utc
            ),
        }

        result = await self._call_db(
            "record_upload",
            data,
        )

        if result is not None:
            return bool(result)

        result = await self._call_db(
            "log_upload",
            data,
        )

        if result is not None:
            return bool(result)

        return False

    # ========================================================
    # EXAM REPORT
    # ========================================================

    async def exam_report(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        limit = max(
            1,
            min(
                safe_int(
                    limit,
                    20,
                ),
                100,
            ),
        )

        result = await self._call_db(
            "get_exam_extraction_report",
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        result = await self._call_db(
            "get_exam_statistics",
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # TEST REPORT
    # ========================================================

    async def test_report(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        limit = max(
            1,
            min(
                safe_int(
                    limit,
                    20,
                ),
                100,
            ),
        )

        result = await self._call_db(
            "get_test_extraction_report",
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        result = await self._call_db(
            "get_popular_tests",
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # USER REPORT
    # ========================================================

    async def user_report(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        result = await self._call_db(
            "get_user_activity_report",
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # DAILY REPORT
    # ========================================================

    async def daily_report(
        self,
        days: int = 7,
    ) -> List[Dict[str, Any]]:

        days = max(
            1,
            min(
                safe_int(
                    days,
                    7,
                ),
                90,
            ),
        )

        result = await self._call_db(
            "get_daily_activity_report",
            days=days,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # FAILED UPLOADS
    # ========================================================

    async def failed_uploads(
        self,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:

        result = await self._call_db(
            "get_failed_uploads",
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # FAILED EXTRACTIONS
    # ========================================================

    async def failed_extractions(
        self,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:

        result = await self._call_db(
            "get_failed_extractions",
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # SUMMARY
    # ========================================================

    async def summary(
        self,
    ) -> Dict[str, Any]:

        exams = await self.exam_report(
            limit=100
        )

        tests = await self.test_report(
            limit=100
        )

        failed_uploads = (
            await self.failed_uploads()
        )

        failed_extractions = (
            await self.failed_extractions()
        )

        return {
            "exams": exams,
            "tests": tests,
            "failed_uploads": failed_uploads,
            "failed_extractions": failed_extractions,
            "generated_at": datetime.now(
                timezone.utc
            ),
        }

    # ========================================================
    # EXAM REPORT TEXT
    # ========================================================

    async def exam_report_text(
        self,
        limit: int = 20,
    ) -> str:

        reports = await self.exam_report(
            limit
        )

        lines = [
            "📊 <b>EXAM EXTRACTION REPORT</b>",
            "",
        ]

        if not reports:

            lines.append(
                "❌ अभी कोई exam report available नहीं है।"
            )

            return "\n".join(
                lines
            )

        for index, item in enumerate(
            reports,
            start=1,
        ):

            exam = item.get(
                "exam",
                item.get(
                    "exam_name",
                    "Unknown Exam",
                ),
            )

            count = item.get(
                "count",
                item.get(
                    "extractions",
                    item.get(
                        "total",
                        0,
                    ),
                ),
            )

            lines.append(
                (
                    f"<b>{index}.</b> "
                    f"📚 {exam}\n"
                    f"   📥 Extracted: "
                    f"<b>{count}</b>"
                )
            )

        return "\n".join(
            lines
        )

    # ========================================================
    # TEST REPORT TEXT
    # ========================================================

    async def test_report_text(
        self,
        limit: int = 20,
    ) -> str:

        reports = await self.test_report(
            limit
        )

        lines = [
            "🔥 <b>MOST EXTRACTED TESTS</b>",
            "",
        ]

        if not reports:

            lines.append(
                "❌ अभी कोई test report available नहीं है।"
            )

            return "\n".join(
                lines
            )

        for index, item in enumerate(
            reports,
            start=1,
        ):

            name = item.get(
                "test_name",
                item.get(
                    "name",
                    "Unknown Test",
                ),
            )

            exam = item.get(
                "exam",
                item.get(
                    "exam_name",
                    "",
                ),
            )

            count = item.get(
                "count",
                item.get(
                    "extractions",
                    0,
                ),
            )

            if exam:

                lines.append(
                    (
                        f"<b>{index}.</b> "
                        f"📝 {name}\n"
                        f"   📚 Exam: {exam}\n"
                        f"   📥 Extracted: "
                        f"<b>{count}</b>"
                    )
                )

            else:

                lines.append(
                    (
                        f"<b>{index}.</b> "
                        f"📝 {name}\n"
                        f"   📥 Extracted: "
                        f"<b>{count}</b>"
                    )
                )

        return "\n".join(
            lines
        )

    # ========================================================
    # FAILED UPLOAD TEXT
    # ========================================================

    async def failed_upload_text(
        self,
        limit: int = 50,
    ) -> str:

        reports = await self.failed_uploads(
            limit
        )

        lines = [
            "❌ <b>FAILED TEST UPLOADS</b>",
            "",
        ]

        if not reports:

            lines.append(
                "✅ कोई failed upload नहीं है।"
            )

            return "\n".join(
                lines
            )

        for index, item in enumerate(
            reports,
            start=1,
        ):

            test_name = item.get(
                "test_name",
                item.get(
                    "name",
                    "Unknown Test",
                ),
            )

            test_id = item.get(
                "test_id",
                "N/A",
            )

            error = item.get(
                "error",
                "Unknown error",
            )

            lines.append(
                (
                    f"<b>{index}.</b> "
                    f"📝 {test_name}\n"
                    f"🆔 <code>{test_id}</code>\n"
                    f"⚠️ {error}"
                )
            )

            lines.append("")

        lines.append(
            "👇 नीचे Retry option उपलब्ध होने पर "
            "failed tests को दोबारा process किया जा सकता है।"
        )

        return "\n".join(
            lines
        )

    # ========================================================
    # COMPLETE ADMIN REPORT
    # ========================================================

    async def admin_report_text(
        self,
    ) -> str:

        summary = await self.summary()

        exams = summary[
            "exams"
        ]

        tests = summary[
            "tests"
        ]

        failed_uploads = summary[
            "failed_uploads"
        ]

        failed_extractions = summary[
            "failed_extractions"
        ]

        lines = [
            "📊 <b>COMPLETE BOT REPORT</b>",
            "",
            "📚 <b>TOP EXAMS</b>",
        ]

        if exams:

            for index, item in enumerate(
                exams[:10],
                start=1,
            ):

                exam = item.get(
                    "exam",
                    item.get(
                        "exam_name",
                        "Unknown",
                    ),
                )

                count = item.get(
                    "count",
                    item.get(
                        "extractions",
                        0,
                    ),
                )

                lines.append(
                    (
                        f"{index}. {exam} — "
                        f"<b>{count}</b>"
                    )
                )

        else:

            lines.append(
                "No exam data."
            )

        lines.extend(
            [
                "",
                "🔥 <b>TOP TESTS</b>",
            ]
        )

        if tests:

            for index, item in enumerate(
                tests[:10],
                start=1,
            ):

                name = item.get(
                    "test_name",
                    item.get(
                        "name",
                        "Unknown",
                    ),
                )

                count = item.get(
                    "count",
                    item.get(
                        "extractions",
                        0,
                    ),
                )

                lines.append(
                    (
                        f"{index}. {name} — "
                        f"<b>{count}</b>"
                    )
                )

        else:

            lines.append(
                "No test data."
            )

        lines.extend(
            [
                "",
                "❌ <b>FAILED</b>",
                (
                    f"Upload Failed: "
                    f"<b>{len(failed_uploads)}</b>"
                ),
                (
                    f"Extraction Failed: "
                    f"<b>{len(failed_extractions)}</b>"
                ),
            ]
        )

        return "\n".join(
            lines
        )


# ============================================================
# GLOBAL SERVICE
# ============================================================

report_service = ReportService()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def record_extraction(
    user_id: int,
    test_id: Optional[str] = None,
    exam: Optional[str] = None,
    test_name: Optional[str] = None,
    success: bool = True,
    paid_user: bool = False,
):

    return await report_service.record_extraction(
        user_id=user_id,
        test_id=test_id,
        exam=exam,
        test_name=test_name,
        success=success,
        paid_user=paid_user,
    )


async def record_upload(
    user_id: int,
    test_id: Optional[str] = None,
    test_name: Optional[str] = None,
    success: bool = True,
    error: Optional[str] = None,
):

    return await report_service.record_upload(
        user_id=user_id,
        test_id=test_id,
        test_name=test_name,
        success=success,
        error=error,
    )


async def get_exam_report(
    limit: int = 20,
):

    return await report_service.exam_report(
        limit
    )


async def get_test_report(
    limit: int = 20,
):

    return await report_service.test_report(
        limit
    )


async def get_failed_uploads(
    limit: int = 100,
):

    return await report_service.failed_uploads(
        limit
    )


# ============================================================
# TELEGRAM REPORT HANDLER
# ============================================================

async def show_reports(
    update,
    context,
):

    try:

        text = await report_service.admin_report_text()

        if update.callback_query:

            query = update.callback_query

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
            "Failed to show reports."
        )

        try:

            if update.effective_message:

                await update.effective_message.reply_text(
                    "❌ Report load नहीं हो सकी।"
                )

        except Exception:

            logger.debug(
                "Could not send report error.",
                exc_info=True,
            )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "ReportService",
    "report_service",
    "record_extraction",
    "record_upload",
    "get_exam_report",
    "get_test_report",
    "get_failed_uploads",
    "show_reports",
]

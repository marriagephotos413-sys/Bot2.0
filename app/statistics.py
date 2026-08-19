import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.user_management import user_manager


logger = logging.getLogger(
    "telegram-test-series-bot.statistics"
)


# ============================================================
# STATISTICS SERVICE
# ============================================================

class StatisticsService:
    """
    Bot statistics manager.

    Tracks / displays:

    - Total users
    - Paid users
    - Banned users
    - Free users
    - Trial users
    - Total test extractions
    - Successful extractions
    - Failed extractions
    - Total tests
    - Popular exams
    - Popular tests
    - Daily activity
    - Overall bot activity

    Test JSON MongoDB में store नहीं किया जाता।
    इसलिए test statistics केवल available metadata/
    counters से निकाली जाती हैं।
    """

    # ========================================================
    # DATABASE
    # ========================================================

    def _get_db(self):

        try:

            from app.database import db

            return db

        except Exception:

            logger.exception(
                "Database unavailable."
            )

            return None

    # ========================================================
    # CALL DATABASE METHOD
    # ========================================================

    async def _call(
        self,
        method_name: str,
        *args,
        **kwargs,
    ):

        database = self._get_db()

        if database is None:
            return None

        method = getattr(
            database,
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

            # कुछ database implementations keyword
            # arguments support नहीं करतीं।
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
                    (
                        "Database method failed: "
                        "%s"
                    ),
                    method_name,
                    exc_info=True,
                )

        except Exception:

            logger.exception(
                "Database method failed: %s",
                method_name,
            )

        return None

    # ========================================================
    # USER STATISTICS
    # ========================================================

    async def total_users(
        self,
    ) -> int:

        result = await user_manager.count_users()

        return int(
            result or 0
        )

    async def paid_users(
        self,
    ) -> int:

        result = await user_manager.count_paid_users()

        return int(
            result or 0
        )

    async def banned_users(
        self,
    ) -> int:

        result = await user_manager.count_banned_users()

        return int(
            result or 0
        )

    async def free_users(
        self,
    ) -> int:

        total = await self.total_users()
        paid = await self.paid_users()

        return max(
            0,
            total - paid,
        )

    # ========================================================
    # TRIAL USERS
    # ========================================================

    async def trial_users(
        self,
    ) -> int:

        result = await self._call(
            "count_trial_users"
        )

        if result is not None:

            return int(
                result or 0
            )

        users = await user_manager.list_users(
            limit=100000
        )

        count = 0

        for user in users:

            if user.get(
                "trial_active",
                False,
            ):

                count += 1

        return count

    # ========================================================
    # EXTRACTION STATISTICS
    # ========================================================

    async def extraction_statistics(
        self,
    ) -> Dict[str, int]:

        result = await self._call(
            "get_extraction_statistics"
        )

        if isinstance(
            result,
            dict,
        ):

            return {
                "total": int(
                    result.get(
                        "total",
                        result.get(
                            "total_extractions",
                            0,
                        ),
                    )
                    or 0
                ),
                "successful": int(
                    result.get(
                        "successful",
                        result.get(
                            "successful_extractions",
                            0,
                        ),
                    )
                    or 0
                ),
                "failed": int(
                    result.get(
                        "failed",
                        result.get(
                            "failed_extractions",
                            0,
                        ),
                    )
                    or 0
                ),
            }

        # Fallback: users के counters से calculate करें।

        users = await user_manager.list_users(
            limit=100000
        )

        total = 0
        successful = 0
        failed = 0

        for user in users:

            total += int(
                user.get(
                    "total_extractions",
                    0,
                )
                or 0
            )

            successful += int(
                user.get(
                    "successful_extractions",
                    0,
                )
                or 0
            )

            failed += int(
                user.get(
                    "failed_extractions",
                    0,
                )
                or 0
            )

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
        }

    # ========================================================
    # TEST STATISTICS
    # ========================================================

    async def test_statistics(
        self,
    ) -> Dict[str, int]:

        result = await self._call(
            "get_test_statistics"
        )

        if isinstance(
            result,
            dict,
        ):

            return {
                "total_tests": int(
                    result.get(
                        "total_tests",
                        result.get(
                            "total",
                            0,
                        ),
                    )
                    or 0
                ),
                "active_tests": int(
                    result.get(
                        "active_tests",
                        0,
                    )
                    or 0
                ),
                "failed_tests": int(
                    result.get(
                        "failed_tests",
                        0,
                    )
                    or 0
                ),
            }

        # MongoDB में test JSON नहीं है।
        # इसलिए test-manager से metadata count लेने की कोशिश।

        try:

            from app.test_manager import (
                test_manager,
            )

            total = await test_manager.count_tests()

            return {
                "total_tests": int(
                    total or 0
                ),
                "active_tests": int(
                    total or 0
                ),
                "failed_tests": 0,
            }

        except Exception:

            logger.debug(
                "Test manager statistics unavailable.",
                exc_info=True,
            )

        return {
            "total_tests": 0,
            "active_tests": 0,
            "failed_tests": 0,
        }

    # ========================================================
    # EXAM STATISTICS
    # ========================================================

    async def exam_statistics(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        result = await self._call(
            "get_exam_statistics",
            limit=int(limit),
        )

        if isinstance(
            result,
            list,
        ):

            return result

        if isinstance(
            result,
            dict,
        ):

            data = result.get(
                "items",
                result.get(
                    "data",
                    [],
                ),
            )

            if isinstance(
                data,
                list,
            ):

                return data

        # Fallback: available activity statistics.

        result = await self._call(
            "get_popular_exams",
            limit=int(limit),
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # TEST EXTRACTION REPORT
    # ========================================================

    async def extraction_report(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        result = await self._call(
            "get_extraction_report",
            limit=int(limit),
        )

        if isinstance(
            result,
            list,
        ):

            return result

        if isinstance(
            result,
            dict,
        ):

            data = result.get(
                "items",
                result.get(
                    "data",
                    [],
                ),
            )

            if isinstance(
                data,
                list,
            ):

                return data

        return []

    # ========================================================
    # DAILY STATISTICS
    # ========================================================

    async def daily_statistics(
        self,
        days: int = 7,
    ) -> List[Dict[str, Any]]:

        days = max(
            1,
            min(
                int(days),
                90,
            ),
        )

        result = await self._call(
            "get_daily_statistics",
            days=days,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        if isinstance(
            result,
            dict,
        ):

            data = result.get(
                "items",
                result.get(
                    "data",
                    [],
                ),
            )

            if isinstance(
                data,
                list,
            ):

                return data

        return []

    # ========================================================
    # COMPLETE STATISTICS
    # ========================================================

    async def get_all(
        self,
    ) -> Dict[str, Any]:

        users = await self.total_users()
        paid = await self.paid_users()
        banned = await self.banned_users()
        free = await self.free_users()
        trial = await self.trial_users()

        extraction = (
            await self.extraction_statistics()
        )

        tests = (
            await self.test_statistics()
        )

        return {
            "users": {
                "total": users,
                "paid": paid,
                "free": free,
                "banned": banned,
                "trial": trial,
            },
            "extractions": extraction,
            "tests": tests,
            "generated_at": datetime.now(
                timezone.utc
            ),
        }

    # ========================================================
    # ADMIN TEXT
    # ========================================================

    async def admin_text(
        self,
    ) -> str:

        data = await self.get_all()

        users = data["users"]
        extraction = data["extractions"]
        tests = data["tests"]

        return (
            "📊 <b>BOT STATISTICS</b>\n"
            "\n"
            "👥 <b>USERS</b>\n"
            f"👤 Total Users: "
            f"<b>{users['total']}</b>\n"
            f"💎 Paid Users: "
            f"<b>{users['paid']}</b>\n"
            f"🆓 Free Users: "
            f"<b>{users['free']}</b>\n"
            f"🎁 Trial Users: "
            f"<b>{users['trial']}</b>\n"
            f"🚫 Banned Users: "
            f"<b>{users['banned']}</b>\n"
            "\n"
            "📚 <b>TESTS</b>\n"
            f"📄 Total Tests: "
            f"<b>{tests['total_tests']}</b>\n"
            f"🟢 Active Tests: "
            f"<b>{tests['active_tests']}</b>\n"
            f"❌ Failed Tests: "
            f"<b>{tests['failed_tests']}</b>\n"
            "\n"
            "🚀 <b>EXTRACTION</b>\n"
            f"📥 Total Extracted: "
            f"<b>{extraction['total']}</b>\n"
            f"✅ Successful: "
            f"<b>{extraction['successful']}</b>\n"
            f"❌ Failed: "
            f"<b>{extraction['failed']}</b>"
        )

    # ========================================================
    # EXAM REPORT TEXT
    # ========================================================

    async def exam_report_text(
        self,
        limit: int = 20,
    ) -> str:

        reports = await self.extraction_report(
            limit=limit
        )

        if not reports:

            return (
                "📊 <b>EXAM EXTRACTION REPORT</b>\n\n"
                "अभी कोई extraction report available नहीं है।"
            )

        lines = [
            "📊 <b>EXAM EXTRACTION REPORT</b>",
            "",
        ]

        for index, item in enumerate(
            reports,
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
                    f"<b>{index}.</b> "
                    f"📚 {exam} — "
                    f"<b>{count}</b> Extracted"
                )
            )

        return "\n".join(
            lines
        )

    # ========================================================
    # POPULAR TESTS TEXT
    # ========================================================

    async def popular_tests_text(
        self,
        limit: int = 20,
    ) -> str:

        reports = await self.extraction_report(
            limit=limit
        )

        if not reports:

            return (
                "🔥 <b>POPULAR TESTS</b>\n\n"
                "अभी data available नहीं है।"
            )

        lines = [
            "🔥 <b>MOST EXTRACTED TESTS</b>",
            "",
        ]

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

            count = item.get(
                "count",
                item.get(
                    "extractions",
                    0,
                ),
            )

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


# ============================================================
# GLOBAL INSTANCE
# ============================================================

statistics_service = StatisticsService()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def get_bot_statistics():

    return await statistics_service.get_all()


async def get_bot_statistics_text():

    return await statistics_service.admin_text()


async def get_exam_report(
    limit: int = 20,
):

    return await statistics_service.exam_report_text(
        limit=limit
    )


async def get_popular_tests(
    limit: int = 20,
):

    return await statistics_service.popular_tests_text(
        limit=limit
    )


# ============================================================
# TELEGRAM HANDLER
# ============================================================

async def show_statistics(
    update,
    context,
):

    try:

        text = await statistics_service.admin_text()

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
            "Failed to show statistics."
        )

        try:

            if update.effective_message:

                await update.effective_message.reply_text(
                    "❌ Statistics load नहीं हो सकी।"
                )

        except Exception:

            logger.debug(
                "Statistics error message failed.",
                exc_info=True,
            )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "StatisticsService",
    "statistics_service",
    "get_bot_statistics",
    "get_bot_statistics_text",
    "get_exam_report",
    "get_popular_tests",
    "show_statistics",
]

import logging
from typing import Any, Dict, List, Optional

from app.helpers import clean_text, safe_int
from app.database import db


logger = logging.getLogger(
    "telegram-test-series-bot.search"
)


# ============================================================
# SEARCH SERVICE
# ============================================================

class SearchService:
    """
    Test Search & Index Service.

    Search hierarchy:

        Category
          ↓
        Exam
          ↓
        Section
          ↓
        Subsection / Year
          ↓
        Test Type
          ↓
        Test

    Examples:

        SSC
          └── SSC GD
                └── Previous Year
                      └── 2024
                            └── PYQ
                                  └── Test List

        RRB
          └── NTPC
                └── Mock Test
                      └── 2026
                            └── Test List

    IMPORTANT:
    Actual question JSON MongoDB में store नहीं किया जाता।
    Search/index में केवल test metadata और GitHub source
    reference इस्तेमाल किया जा सकता है।
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
                    "Database method failed: %s",
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
    # SEARCH
    # ========================================================

    async def search(
        self,
        query: str,
        *,
        category: Optional[str] = None,
        exam: Optional[str] = None,
        year: Optional[str] = None,
        test_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:

        query = clean_text(
            query
        )

        if not query:
            return []

        limit = max(
            1,
            min(
                safe_int(
                    limit,
                    50,
                ),
                100,
            ),
        )

        filters = {
            "query": query,
            "category": category,
            "exam": exam,
            "year": year,
            "test_type": test_type,
            "limit": limit,
        }

        # Preferred database search.

        result = await self._call_db(
            "search_tests",
            **filters,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        # Alternate method name.

        result = await self._call_db(
            "search_test_metadata",
            **filters,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        # No metadata provider available.

        return []

    # ========================================================
    # SEARCH BY CATEGORY
    # ========================================================

    async def by_category(
        self,
        category: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:

        category = clean_text(
            category
        )

        if not category:
            return []

        result = await self._call_db(
            "get_tests_by_category",
            category=category,
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # SEARCH BY EXAM
    # ========================================================

    async def by_exam(
        self,
        exam: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:

        exam = clean_text(
            exam
        )

        if not exam:
            return []

        result = await self._call_db(
            "get_tests_by_exam",
            exam=exam,
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # SEARCH BY YEAR
    # ========================================================

    async def by_year(
        self,
        exam: Optional[str],
        year: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:

        year = clean_text(
            year
        )

        if not year:
            return []

        result = await self._call_db(
            "get_tests_by_year",
            exam=exam,
            year=year,
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # SEARCH BY TEST TYPE
    # ========================================================

    async def by_test_type(
        self,
        test_type: str,
        *,
        exam: Optional[str] = None,
        year: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:

        test_type = clean_text(
            test_type
        )

        if not test_type:
            return []

        result = await self._call_db(
            "get_tests_by_type",
            test_type=test_type,
            exam=exam,
            year=year,
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # CATEGORIES
    # ========================================================

    async def categories(
        self,
    ) -> List[Dict[str, Any]]:

        result = await self._call_db(
            "get_test_categories"
        )

        if isinstance(
            result,
            list,
        ):

            return result

        # Alternate method.

        result = await self._call_db(
            "list_categories"
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # EXAMS
    # ========================================================

    async def exams(
        self,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        result = await self._call_db(
            "get_test_exams",
            category=category,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        result = await self._call_db(
            "list_exams",
            category=category,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # YEARS
    # ========================================================

    async def years(
        self,
        exam: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Any]:

        result = await self._call_db(
            "get_test_years",
            exam=exam,
            category=category,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # TEST TYPES
    # ========================================================

    async def test_types(
        self,
        exam: Optional[str] = None,
        year: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        result = await self._call_db(
            "get_test_types",
            exam=exam,
            year=year,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # TEST LIST
    # ========================================================

    async def test_list(
        self,
        *,
        category: Optional[str] = None,
        exam: Optional[str] = None,
        year: Optional[str] = None,
        test_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:

        result = await self._call_db(
            "list_tests",
            category=category,
            exam=exam,
            year=year,
            test_type=test_type,
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # TEST DETAIL
    # ========================================================

    async def test_detail(
        self,
        test_id: str,
    ) -> Optional[Dict[str, Any]]:

        test_id = clean_text(
            test_id
        )

        if not test_id:
            return None

        result = await self._call_db(
            "get_test_metadata",
            test_id=test_id,
        )

        if isinstance(
            result,
            dict,
        ):

            return result

        result = await self._call_db(
            "get_test",
            test_id=test_id,
        )

        if isinstance(
            result,
            dict,
        ):

            return result

        return None

    # ========================================================
    # FORMAT TEST RESULT
    # ========================================================

    @staticmethod
    def format_test(
        item: Dict[str, Any],
    ) -> str:

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

        year = item.get(
            "year",
            "",
        )

        test_type = item.get(
            "test_type",
            item.get(
                "type",
                "",
            ),
        )

        questions = item.get(
            "questions",
            item.get(
                "question_count",
                "",
            ),
        )

        parts = [
            f"📝 <b>{name}</b>"
        ]

        if exam:
            parts.append(
                f"📚 Exam: {exam}"
            )

        if year:
            parts.append(
                f"📅 Year: {year}"
            )

        if test_type:
            parts.append(
                f"📁 Type: {test_type}"
            )

        if questions:
            parts.append(
                f"❓ Questions: {questions}"
            )

        return "\n".join(
            parts
        )

    # ========================================================
    # FORMAT SEARCH RESULTS
    # ========================================================

    def format_results(
        self,
        results: List[Dict[str, Any]],
        *,
        title: str = "SEARCH RESULTS",
    ) -> str:

        lines = [
            f"🔎 <b>{title}</b>",
            "",
        ]

        if not results:

            lines.append(
                "❌ कोई test नहीं मिला।"
            )

            return "\n".join(
                lines
            )

        for index, item in enumerate(
            results,
            start=1,
        ):

            lines.append(
                f"<b>{index}.</b>"
            )

            lines.append(
                self.format_test(
                    item
                )
            )

            lines.append("")

        lines.append(
            f"📊 Total: <b>{len(results)}</b>"
        )

        return "\n".join(
            lines
        )


# ============================================================
# GLOBAL INSTANCE
# ============================================================

search_service = SearchService()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def search_tests(
    query: str,
    **kwargs,
):

    return await search_service.search(
        query,
        **kwargs,
    )


async def get_categories():

    return await search_service.categories()


async def get_exams(
    category: Optional[str] = None,
):

    return await search_service.exams(
        category
    )


async def get_years(
    exam: Optional[str] = None,
    category: Optional[str] = None,
):

    return await search_service.years(
        exam=exam,
        category=category,
    )


async def get_test_types(
    exam: Optional[str] = None,
    year: Optional[str] = None,
):

    return await search_service.test_types(
        exam=exam,
        year=year,
    )


async def get_test_list(
    **kwargs,
):

    return await search_service.test_list(
        **kwargs
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "SearchService",
    "search_service",
    "search_tests",
    "get_categories",
    "get_exams",
    "get_years",
    "get_test_types",
    "get_test_list",
]

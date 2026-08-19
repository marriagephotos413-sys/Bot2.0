import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.database import db
from app.helpers import clean_text, safe_int
from app.settings import settings_service


logger = logging.getLogger(
    "telegram-test-series-bot.test-manager"
)


# ============================================================
# TEST MANAGER
# ============================================================

class TestManager:
    """
    Test metadata manager.

    IMPORTANT ARCHITECTURE
    ----------------------
    Actual question JSON MongoDB में save नहीं होगा.

    Flow:

        Telegram Test Upload
                ↓
        Parse / Extract Questions
                ↓
        Generate JSON
                ↓
        GitHub -> tcs.html
                ↓
        Database Channel -> backup/reference
                ↓
        MongoDB -> केवल metadata/statistics
                ↓
        User Test Extract
                ↓
        GitHub test source
                ↓
        Test JSON
                ↓
        User

    MongoDB में केवल:
        - test_id
        - exam
        - section
        - subsection
        - test_name
        - question_count
        - language
        - source
        - github path
        - status
        - upload statistics
        - extraction statistics
        - timestamps

    store किए जा सकते हैं।
    """

    # ========================================================
    # STATUS
    # ========================================================

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_UPLOADING = "uploading"
    STATUS_ACTIVE = "active"
    STATUS_FAILED = "failed"
    STATUS_DISABLED = "disabled"

    # ========================================================
    # INIT
    # ========================================================

    def __init__(self):

        self.local_status: Dict[
            str,
            Dict[str, Any]
        ] = {}

        self._locks: Dict[
            str,
            asyncio.Lock
        ] = {}

    # ========================================================
    # LOCK
    # ========================================================

    def _get_lock(
        self,
        test_id: str,
    ) -> asyncio.Lock:

        if test_id not in self._locks:

            self._locks[
                test_id
            ] = asyncio.Lock()

        return self._locks[
            test_id
        ]

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
    # NORMALIZE METADATA
    # ========================================================

    @staticmethod
    def normalize_metadata(
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:

        data = dict(
            metadata or {}
        )

        test_id = clean_text(
            data.get(
                "test_id",
                data.get(
                    "id",
                    "",
                ),
            )
        )

        if not test_id:

            raise ValueError(
                "test_id required."
            )

        question_count = safe_int(
            data.get(
                "question_count",
                data.get(
                    "questions",
                    data.get(
                        "total_questions",
                        0,
                    ),
                ),
            ),
            0,
        )

        normalized = {
            "test_id": test_id,

            "series": clean_text(
                data.get(
                    "series",
                    "",
                )
            ),

            "category": clean_text(
                data.get(
                    "category",
                    "",
                )
            ),

            "section": clean_text(
                data.get(
                    "section",
                    "",
                )
            ),

            "subsection": clean_text(
                data.get(
                    "subsection",
                    "",
                )
            ),

            "exam": clean_text(
                data.get(
                    "exam",
                    data.get(
                        "exam_name",
                        "",
                    ),
                )
            ),

            "year": clean_text(
                data.get(
                    "year",
                    "",
                )
            ),

            "test_name": clean_text(
                data.get(
                    "test_name",
                    data.get(
                        "name",
                        "Unnamed Test",
                    ),
                )
            ),

            "test_type": clean_text(
                data.get(
                    "test_type",
                    data.get(
                        "type",
                        "",
                    ),
                )
            ),

            "shift": clean_text(
                data.get(
                    "shift",
                    "",
                )
            ),

            "language": clean_text(
                data.get(
                    "language",
                    "Hindi",
                )
            ),

            "question_count": max(
                0,
                question_count,
            ),

            "source": clean_text(
                data.get(
                    "source",
                    "github",
                )
            ),

            "github_file": clean_text(
                data.get(
                    "github_file",
                    settings_service.github_test_file(),
                )
            ),

            "github_branch": clean_text(
                data.get(
                    "github_branch",
                    settings_service.github_branch(),
                )
            ),

            "status": clean_text(
                data.get(
                    "status",
                    TestManager.STATUS_PENDING,
                )
            ),

            "enabled": bool(
                data.get(
                    "enabled",
                    True,
                )
            ),

            "question_json_key": clean_text(
                data.get(
                    "question_json_key",
                    test_id,
                )
            ),

            "database_message_id": data.get(
                "database_message_id"
            ),

            "created_at": data.get(
                "created_at",
                datetime.now(
                    timezone.utc
                ),
            ),

            "updated_at": datetime.now(
                timezone.utc
            ),
        }

        return normalized

    # ========================================================
    # CREATE / REGISTER TEST
    # ========================================================

    async def register_test(
        self,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:

        data = self.normalize_metadata(
            metadata
        )

        test_id = data[
            "test_id"
        ]

        self.local_status[
            test_id
        ] = {
            "status": data[
                "status"
            ],
            "progress": 0,
            "message": "Registered",
            "updated_at": datetime.now(
                timezone.utc
            ),
        }

        # Metadata only.
        # Questions JSON is intentionally NOT passed.

        result = await self._call_db(
            "upsert_test_metadata",
            data,
        )

        if result is None:

            result = await self._call_db(
                "save_test_metadata",
                data,
            )

        if isinstance(
            result,
            dict,
        ):

            return result

        return data

    # ========================================================
    # UPDATE STATUS
    # ========================================================

    async def update_status(
        self,
        test_id: str,
        status: str,
        progress: Optional[int] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:

        test_id = clean_text(
            test_id
        )

        status = clean_text(
            status
        )

        if not test_id:

            raise ValueError(
                "test_id required."
            )

        if not status:

            raise ValueError(
                "status required."
            )

        if progress is not None:

            progress = max(
                0,
                min(
                    100,
                    safe_int(
                        progress,
                        0,
                    ),
                ),
            )

        state = self.local_status.setdefault(
            test_id,
            {},
        )

        state.update(
            {
                "status": status,
                "updated_at": datetime.now(
                    timezone.utc
                ),
            }
        )

        if progress is not None:

            state[
                "progress"
            ] = progress

        if message is not None:

            state[
                "message"
            ] = clean_text(
                message
            )

        # Metadata update only.

        result = await self._call_db(
            "update_test_status",
            test_id=test_id,
            status=status,
            progress=progress,
            message=message,
        )

        if isinstance(
            result,
            dict,
        ):

            return result

        return dict(
            state
        )

    # ========================================================
    # GET STATUS
    # ========================================================

    async def get_status(
        self,
        test_id: str,
    ) -> Dict[str, Any]:

        test_id = clean_text(
            test_id
        )

        local = self.local_status.get(
            test_id
        )

        if local:

            return dict(
                local
            )

        result = await self._call_db(
            "get_test_status",
            test_id=test_id,
        )

        if isinstance(
            result,
            dict,
        ):

            return result

        return {
            "status": "unknown",
            "progress": 0,
            "message": "Status unavailable.",
        }

    # ========================================================
    # GET TEST
    # ========================================================

    async def get_test(
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
    # LIST TESTS
    # ========================================================

    async def list_tests(
        self,
        *,
        category: Optional[str] = None,
        exam: Optional[str] = None,
        year: Optional[str] = None,
        test_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:

        limit = max(
            1,
            min(
                safe_int(
                    limit,
                    100,
                ),
                1000,
            ),
        )

        result = await self._call_db(
            "list_tests",
            category=category,
            exam=exam,
            year=year,
            test_type=test_type,
            status=status,
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        result = await self._call_db(
            "list_test_metadata",
            category=category,
            exam=exam,
            year=year,
            test_type=test_type,
            status=status,
            limit=limit,
        )

        if isinstance(
            result,
            list,
        ):

            return result

        return []

    # ========================================================
    # COUNT
    # ========================================================

    async def count_tests(
        self,
    ) -> int:

        result = await self._call_db(
            "count_tests"
        )

        if result is not None:

            return safe_int(
                result,
                0,
            )

        result = await self._call_db(
            "count_test_metadata"
        )

        if result is not None:

            return safe_int(
                result,
                0,
            )

        tests = await self.list_tests(
            limit=100000
        )

        return len(
            tests
        )

    # ========================================================
    # START PROCESSING
    # ========================================================

    async def start_processing(
        self,
        test_id: str,
    ) -> Dict[str, Any]:

        lock = self._get_lock(
            test_id
        )

        if lock.locked():

            return {
                "success": False,
                "test_id": test_id,
                "status": "already_processing",
                "message": (
                    "This test is already being processed."
                ),
            }

        await lock.acquire()

        try:

            await self.update_status(
                test_id,
                self.STATUS_PROCESSING,
                progress=5,
                message="Processing started...",
            )

            return {
                "success": True,
                "test_id": test_id,
                "status": self.STATUS_PROCESSING,
            }

        except Exception:

            lock.release()

            raise

    # ========================================================
    # FINISH PROCESSING
    # ========================================================

    async def finish_processing(
        self,
        test_id: str,
        success: bool = True,
        message: Optional[str] = None,
    ):

        try:

            if success:

                await self.update_status(
                    test_id,
                    self.STATUS_ACTIVE,
                    progress=100,
                    message=(
                        message
                        or "Test ready."
                    ),
                )

            else:

                await self.update_status(
                    test_id,
                    self.STATUS_FAILED,
                    progress=100,
                    message=(
                        message
                        or "Test processing failed."
                    ),
                )

        finally:

            lock = self._get_lock(
                test_id
            )

            if lock.locked():

                try:

                    lock.release()

                except RuntimeError:

                    pass

    # ========================================================
    # UPLOAD START
    # ========================================================

    async def start_upload(
        self,
        test_id: str,
    ):

        await self.update_status(
            test_id,
            self.STATUS_UPLOADING,
            progress=10,
            message="Uploading test...",
        )

    # ========================================================
    # UPLOAD SUCCESS
    # ========================================================

    async def upload_success(
        self,
        test_id: str,
        *,
        github_file: Optional[str] = None,
        database_message_id: Optional[int] = None,
    ):

        if github_file:

            result = await self._call_db(
                "update_test_github_source",
                test_id=test_id,
                github_file=github_file,
            )

            if result is None:

                await self._call_db(
                    "update_test_source",
                    test_id=test_id,
                    github_file=github_file,
                )

        if database_message_id is not None:

            await self._call_db(
                "update_test_database_message",
                test_id=test_id,
                database_message_id=(
                    database_message_id
                ),
            )

        await self.update_status(
            test_id,
            self.STATUS_ACTIVE,
            progress=100,
            message="Upload completed.",
        )

    # ========================================================
    # UPLOAD FAILED
    # ========================================================

    async def upload_failed(
        self,
        test_id: str,
        error: str,
    ):

        error = clean_text(
            error
        )

        await self.update_status(
            test_id,
            self.STATUS_FAILED,
            progress=100,
            message=error,
        )

        await self._call_db(
            "record_failed_upload",
            test_id=test_id,
            error=error,
        )

    # ========================================================
    # DISABLE
    # ========================================================

    async def disable_test(
        self,
        test_id: str,
    ) -> bool:

        result = await self._call_db(
            "disable_test",
            test_id=test_id,
        )

        if result is not None:

            return bool(
                result
            )

        result = await self._call_db(
            "update_test_status",
            test_id=test_id,
            status=self.STATUS_DISABLED,
            progress=100,
            message="Test disabled.",
        )

        return bool(
            result is not None
        )

    # ========================================================
    # ENABLE
    # ========================================================

    async def enable_test(
        self,
        test_id: str,
    ) -> bool:

        result = await self._call_db(
            "enable_test",
            test_id=test_id,
        )

        if result is not None:

            return bool(
                result
            )

        result = await self._call_db(
            "update_test_status",
            test_id=test_id,
            status=self.STATUS_ACTIVE,
            progress=100,
            message="Test enabled.",
        )

        return bool(
            result is not None
        )

    # ========================================================
    # RETRY
    # ========================================================

    async def retry_test(
        self,
        test_id: str,
    ) -> Dict[str, Any]:

        test_id = clean_text(
            test_id
        )

        if not test_id:

            return {
                "success": False,
                "error": "Test ID missing.",
            }

        test = await self.get_test(
            test_id
        )

        if not test:

            return {
                "success": False,
                "error": "Test not found.",
            }

        status = clean_text(
            test.get(
                "status",
                "",
            )
        )

        if status != self.STATUS_FAILED:

            return {
                "success": False,
                "error": (
                    "Only failed tests can be retried."
                ),
            }

        await self.update_status(
            test_id,
            self.STATUS_PENDING,
            progress=0,
            message="Retry queued.",
        )

        result = await self._call_db(
            "mark_test_retry",
            test_id=test_id,
        )

        return {
            "success": True,
            "test_id": test_id,
            "status": self.STATUS_PENDING,
            "database_result": result,
        }

    # ========================================================
    # EXTRACTION COUNT
    # ========================================================

    async def increment_extraction(
        self,
        test_id: str,
        user_id: int,
        paid_user: bool = False,
    ) -> bool:

        result = await self._call_db(
            "increment_test_extraction",
            test_id=test_id,
            user_id=int(user_id),
            paid_user=bool(paid_user),
        )

        if result is not None:

            return bool(
                result
            )

        # Alternate method.

        result = await self._call_db(
            "record_test_extraction",
            test_id=test_id,
            user_id=int(user_id),
            paid_user=bool(paid_user),
        )

        return bool(
            result
        ) if result is not None else False

    # ========================================================
    # USER EXTRACTION ACCESS
    # ========================================================

    async def can_extract(
        self,
        test_id: str,
        user_id: int,
        paid_user: bool = False,
    ) -> Dict[str, Any]:

        if not settings_service.extraction_enabled():

            return {
                "allowed": False,
                "reason": "Test extraction is disabled.",
            }

        test = await self.get_test(
            test_id
        )

        if not test:

            return {
                "allowed": False,
                "reason": "Test not found.",
            }

        status = clean_text(
            test.get(
                "status",
                "",
            )
        )

        if status != self.STATUS_ACTIVE:

            return {
                "allowed": False,
                "reason": (
                    "Test अभी available नहीं है."
                ),
                "status": status,
            }

        if not test.get(
            "enabled",
            True,
        ):

            return {
                "allowed": False,
                "reason": "Test disabled.",
            }

        # Paid users get priority, but this method does not
        # block free users merely because paid users exist.

        return {
            "allowed": True,
            "paid_priority": (
                bool(paid_user)
                and settings_service.paid_first()
            ),
            "test": test,
        }

    # ========================================================
    # BUILD USER INFO
    # ========================================================

    @staticmethod
    def user_test_info(
        test: Dict[str, Any],
    ) -> str:

        series = test.get(
            "series",
            "",
        )

        section = test.get(
            "section",
            "",
        )

        subsection = test.get(
            "subsection",
            "",
        )

        exam = test.get(
            "exam",
            "",
        )

        test_name = test.get(
            "test_name",
            test.get(
                "name",
                "Test",
            ),
        )

        questions = test.get(
            "question_count",
            0,
        )

        language = test.get(
            "language",
            "Hindi",
        )

        lines = []

        if series:

            lines.append(
                f"📚 <b>SERIES:</b> {series}"
            )

        if section:

            lines.append(
                f"🗂 <b>SECTION:</b> {section}"
            )

        if subsection:

            lines.append(
                f"📁 <b>SUBSECTION:</b> {subsection}"
            )

        if exam:

            lines.append(
                f"🎯 <b>EXAM:</b> {exam}"
            )

        lines.append(
            f"✅ <b>TEST:</b> {test_name}"
        )

        lines.append(
            (
                f"❓ <b>{questions} QUESTIONS</b>"
                f" • 🌐 {language}"
            )
        )

        return "\n".join(
            lines
        )


# ============================================================
# GLOBAL INSTANCE
# ============================================================

test_manager = TestManager()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def register_test(
    metadata: Dict[str, Any],
):

    return await test_manager.register_test(
        metadata
    )


async def get_test(
    test_id: str,
):

    return await test_manager.get_test(
        test_id
    )


async def list_tests(
    **kwargs,
):

    return await test_manager.list_tests(
        **kwargs
    )


async def count_tests():

    return await test_manager.count_tests()


async def retry_test(
    test_id: str,
):

    return await test_manager.retry_test(
        test_id
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "TestManager",
    "test_manager",
    "register_test",
    "get_test",
    "list_tests",
    "count_tests",
    "retry_test",
]

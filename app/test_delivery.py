import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError

from app.database import db
from app.helpers import clean_text, safe_int
from app.settings import settings_service
from app.test_manager import test_manager


logger = logging.getLogger(
    "telegram-test-series-bot.test-delivery"
)


# ============================================================
# TEST DELIVERY SERVICE
# ============================================================

class TestDeliveryService:
    """
    User Test Extraction / Delivery Service.

    FLOW
    ----
    User
      ↓
    Test Extract
      ↓
    Check user access
      ↓
    Paid user priority
      ↓
    Queue / load protection
      ↓
    Read test source metadata
      ↓
    GitHub tcs.html source
      ↓
    Get test JSON by test_id/key
      ↓
    Return JSON / test link to user

    IMPORTANT
    ---------
    Actual question JSON MongoDB में save नहीं होता।

    MongoDB:
        user + payment + test metadata + statistics

    GitHub:
        tcs.html + actual question JSON

    Database Channel:
        uploaded/reference copy

    यह service MongoDB से question JSON read नहीं करती।
    """

    # ========================================================
    # INIT
    # ========================================================

    def __init__(self):

        self._locks: Dict[
            str,
            asyncio.Lock
        ] = {}

    # ========================================================
    # TEST LOCK
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
    # GITHUB SOURCE
    # ========================================================

    async def _get_github_service(self):

        try:

            from app.github import github_service

            return github_service

        except Exception:

            logger.exception(
                "GitHub service unavailable."
            )

            return None

    # ========================================================
    # GET TEST JSON FROM GITHUB
    # ========================================================

    async def get_test_json(
        self,
        test: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:

        """
        GitHub की tcs.html से test JSON प्राप्त करता है।

        यह function MongoDB में questions खोजने की कोशिश
        नहीं करता।
        """

        github = (
            await self._get_github_service()
        )

        if github is None:

            return None

        test_id = clean_text(
            test.get(
                "test_id",
                "",
            )
        )

        json_key = clean_text(
            test.get(
                "question_json_key",
                test_id,
            )
        )

        github_file = clean_text(
            test.get(
                "github_file",
                settings_service.github_test_file(),
            )
        )

        branch = clean_text(
            test.get(
                "github_branch",
                settings_service.github_branch(),
            )
        )

        # ----------------------------------------------------
        # Preferred GitHub service methods
        # ----------------------------------------------------

        methods = (
            "get_test_json",
            "read_test_json",
            "extract_test_json",
            "get_json_from_html",
        )

        for method_name in methods:

            method = getattr(
                github,
                method_name,
                None,
            )

            if not method:

                continue

            try:

                result = method(
                    test_id=test_id,
                    json_key=json_key,
                    file_path=github_file,
                    branch=branch,
                )

                if hasattr(
                    result,
                    "__await__",
                ):

                    result = await result

                if isinstance(
                    result,
                    dict,
                ):

                    return result

            except TypeError:

                try:

                    result = method(
                        test_id,
                        github_file,
                    )

                    if hasattr(
                        result,
                        "__await__",
                    ):

                        result = await result

                    if isinstance(
                        result,
                        dict,
                    ):

                        return result

                except Exception:

                    logger.debug(
                        (
                            "GitHub method failed: "
                            "%s"
                        ),
                        method_name,
                        exc_info=True,
                    )

            except Exception:

                logger.exception(
                    (
                        "GitHub JSON read failed: "
                        "%s"
                    ),
                    method_name,
                )

        return None

    # ========================================================
    # ACCESS CHECK
    # ========================================================

    async def check_access(
        self,
        user_id: int,
        test_id: str,
        paid_user: bool = False,
    ) -> Dict[str, Any]:

        if not settings_service.extraction_enabled():

            return {
                "allowed": False,
                "reason": (
                    "Test extraction currently disabled."
                ),
            }

        result = await test_manager.can_extract(
            test_id=test_id,
            user_id=user_id,
            paid_user=paid_user,
        )

        return result

    # ========================================================
    # LIVE STATUS
    # ========================================================

    async def _progress(
        self,
        message,
        text: str,
    ):

        if not message:

            return

        try:

            await message.edit_text(
                text,
                parse_mode="HTML",
            )

        except TelegramError:

            pass

        except Exception:

            logger.debug(
                "Progress message update failed.",
                exc_info=True,
            )

    # ========================================================
    # BUILD WAIT MESSAGE
    # ========================================================

    def wait_text(
        self,
        *,
        paid_user: bool = False,
    ) -> str:

        return (
            settings_service.build_wait_message(
                paid_user=paid_user
            )
        )

    # ========================================================
    # DELIVERY
    # ========================================================

    async def deliver(
        self,
        *,
        user_id: int,
        test_id: str,
        paid_user: bool = False,
        progress_message=None,
    ) -> Dict[str, Any]:

        """
        Complete test extraction flow.
        """

        test_id = clean_text(
            test_id
        )

        if not test_id:

            return {
                "success": False,
                "error": "Test ID missing.",
            }

        # ----------------------------------------------------
        # Access
        # ----------------------------------------------------

        access = await self.check_access(
            user_id=user_id,
            test_id=test_id,
            paid_user=paid_user,
        )

        if not access.get(
            "allowed",
            False,
        ):

            return {
                "success": False,
                "error": access.get(
                    "reason",
                    "Access denied.",
                ),
            }

        test = access.get(
            "test"
        )

        if not test:

            test = await test_manager.get_test(
                test_id
            )

        if not test:

            return {
                "success": False,
                "error": "Test metadata not found.",
            }

        # ----------------------------------------------------
        # Paid priority
        # ----------------------------------------------------

        priority = (
            "PREMIUM"
            if (
                paid_user
                and settings_service.paid_first()
            )
            else "NORMAL"
        )

        await self._progress(
            progress_message,
            (
                "🚀 <b>TEST EXTRACTION STARTED</b>\n\n"
                f"🆔 Test: <code>{test_id}</code>\n"
                f"⚡ Priority: <b>{priority}</b>\n"
                "⏳ Preparing source..."
            ),
        )

        # ----------------------------------------------------
        # Test lock
        # ----------------------------------------------------

        lock = self._get_lock(
            test_id
        )

        # Multiple users can extract the same test.
        # इसलिए test-level lock केवल short source read
        # को protect करता है।

        try:

            # ------------------------------------------------
            # Get GitHub JSON
            # ------------------------------------------------

            await self._progress(
                progress_message,
                (
                    "📡 <b>LOADING TEST</b>\n\n"
                    "🐙 GitHub source check हो रहा है...\n"
                    "⏳ Please wait..."
                ),
            )

            async with lock:

                test_json = (
                    await self.get_test_json(
                        test
                    )
                )

            if not test_json:

                await test_manager.update_status(
                    test_id,
                    test_manager.STATUS_FAILED,
                    progress=100,
                    message=(
                        "GitHub test JSON unavailable."
                    ),
                )

                await self._call_db(
                    "record_extraction",
                    {
                        "user_id": int(user_id),
                        "test_id": test_id,
                        "success": False,
                        "paid_user": bool(paid_user),
                        "error": (
                            "GitHub test JSON unavailable."
                        ),
                        "created_at": datetime.now(
                            timezone.utc
                        ),
                    },
                )

                return {
                    "success": False,
                    "error": (
                        "Test data अभी उपलब्ध नहीं है।"
                    ),
                }

            # ------------------------------------------------
            # Validate JSON
            # ------------------------------------------------

            await self._progress(
                progress_message,
                (
                    "🔍 <b>VERIFYING TEST DATA</b>\n\n"
                    "📄 Question JSON मिल गया।\n"
                    "⏳ Data verify हो रहा है..."
                ),
            )

            if not isinstance(
                test_json,
                dict,
            ):

                return {
                    "success": False,
                    "error": (
                        "Invalid test JSON."
                    ),
                }

            # ------------------------------------------------
            # Increment extraction
            # ------------------------------------------------

            await test_manager.increment_extraction(
                test_id=test_id,
                user_id=user_id,
                paid_user=paid_user,
            )

            # ------------------------------------------------
            # Record report
            # ------------------------------------------------

            try:

                from app.reports import (
                    record_extraction,
                )

                await record_extraction(
                    user_id=user_id,
                    test_id=test_id,
                    exam=test.get(
                        "exam",
                        "",
                    ),
                    test_name=test.get(
                        "test_name",
                        "",
                    ),
                    success=True,
                    paid_user=paid_user,
                )

            except Exception:

                logger.debug(
                    "Extraction report failed.",
                    exc_info=True,
                )

            # ------------------------------------------------
            # Complete
            # ------------------------------------------------

            question_count = safe_int(
                test.get(
                    "question_count",
                    test_json.get(
                        "question_count",
                        0,
                    ),
                ),
                0,
            )

            await self._progress(
                progress_message,
                (
                    "✅ <b>TEST READY</b>\n\n"
                    f"📚 {test.get('test_name', 'Test')}\n"
                    f"❓ Questions: <b>{question_count}</b>\n"
                    f"⚡ Priority: <b>{priority}</b>\n\n"
                    "📤 Test भेजा जा रहा है..."
                ),
            )

            return {
                "success": True,
                "test_id": test_id,
                "test": test,
                "test_json": test_json,
                "question_count": question_count,
                "priority": priority,
            }

        except Exception as exc:

            logger.exception(
                "Test delivery failed."
            )

            try:

                from app.reports import (
                    record_extraction,
                )

                await record_extraction(
                    user_id=user_id,
                    test_id=test_id,
                    exam=test.get(
                        "exam",
                        "",
                    ) if test else "",
                    test_name=test.get(
                        "test_name",
                        "",
                    ) if test else "",
                    success=False,
                    paid_user=paid_user,
                )

            except Exception:

                logger.debug(
                    "Failed extraction report failed.",
                    exc_info=True,
                )

            return {
                "success": False,
                "error": str(exc),
            }

    # ========================================================
    # SEND TEST
    # ========================================================

    async def send_test(
        self,
        update: Update,
        result: Dict[str, Any],
    ) -> bool:

        message = (
            update.effective_message
        )

        if not message:

            return False

        if not result.get(
            "success",
            False,
        ):

            await message.reply_text(
                (
                    "❌ <b>TEST EXTRACTION FAILED</b>\n\n"
                    f"{result.get('error', 'Unknown error')}"
                ),
                parse_mode="HTML",
            )

            return False

        test = result.get(
            "test",
            {}
        )

        test_json = result.get(
            "test_json"
        )

        question_count = safe_int(
            result.get(
                "question_count",
                0,
            ),
            0,
        )

        test_name = test.get(
            "test_name",
            "Test",
        )

        # ----------------------------------------------------
        # Test UI URL
        # ----------------------------------------------------

        test_url = (
            test.get(
                "test_url"
            )
            or test.get(
                "github_url"
            )
            or test.get(
                "url"
            )
        )

        text = (
            "🎯 <b>TEST EXTRACTED SUCCESSFULLY</b>\n\n"
            f"📝 <b>{test_name}</b>\n"
            f"❓ Questions: <b>{question_count}</b>\n"
            f"🌐 Language: "
            f"<b>{test.get('language', 'Hindi')}</b>\n"
        )

        keyboard = []

        if test_url:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        "🚀 START TEST",
                        url=test_url,
                    )
                ]
            )

        # ----------------------------------------------------
        # JSON Delivery
        # ----------------------------------------------------

        # JSON को MongoDB में नहीं रखा जाता।
        # User को raw JSON केवल तभी भेजें जब explicitly
        # configured हो।

        send_raw_json = bool(
            test.get(
                "send_raw_json",
                False,
            )
        )

        if send_raw_json:

            import json

            try:

                json_text = json.dumps(
                    test_json,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )

                # Telegram message limit protection.

                if len(json_text) <= 3800:

                    await message.reply_text(
                        (
                            "<pre>"
                            + json_text
                            + "</pre>"
                        ),
                        parse_mode="HTML",
                    )

                else:

                    await message.reply_document(
                        document=(
                            json_text.encode(
                                "utf-8"
                            )
                        ),
                        filename=(
                            f"{test.get('test_id', 'test')}.json"
                        ),
                        caption=(
                            "📄 Test Question JSON"
                        ),
                    )

            except Exception:

                logger.exception(
                    "Raw JSON delivery failed."
                )

        # ----------------------------------------------------
        # Main response
        # ----------------------------------------------------

        await message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=(
                InlineKeyboardMarkup(
                    keyboard
                )
                if keyboard
                else None
            ),
        )

        return True

    # ========================================================
    # USER EXTRACT HANDLER
    # ========================================================

    async def handle_extract(
        self,
        update: Update,
        context,
        test_id: str,
        paid_user: bool = False,
    ) -> bool:

        message = (
            update.effective_message
        )

        if not message:

            return False

        # ----------------------------------------------------
        # Immediate wait response
        # ----------------------------------------------------

        status_message = await message.reply_text(
            self.wait_text(
                paid_user=paid_user
            ),
            parse_mode="HTML",
        )

        # ----------------------------------------------------
        # Delivery
        # ----------------------------------------------------

        result = await self.deliver(
            user_id=update.effective_user.id,
            test_id=test_id,
            paid_user=paid_user,
            progress_message=status_message,
        )

        # ----------------------------------------------------
        # Error
        # ----------------------------------------------------

        if not result.get(
            "success",
            False,
        ):

            try:

                await status_message.edit_text(
                    (
                        "❌ <b>TEST EXTRACTION FAILED</b>\n\n"
                        f"{result.get('error', 'Unknown error')}"
                    ),
                    parse_mode="HTML",
                )

            except Exception:

                await message.reply_text(
                    (
                        "❌ Test extraction failed.\n\n"
                        f"{result.get('error', 'Unknown error')}"
                    )
                )

            return False

        # ----------------------------------------------------
        # Delete progress message
        # ----------------------------------------------------

        try:

            await status_message.delete()

        except Exception:

            pass

        # ----------------------------------------------------
        # Send test
        # ----------------------------------------------------

        return await self.send_test(
            update,
            result,
        )


# ============================================================
# GLOBAL INSTANCE
# ============================================================

test_delivery_service = (
    TestDeliveryService()
)


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

async def extract_test(
    update: Update,
    context,
    test_id: str,
    paid_user: bool = False,
):

    return await test_delivery_service.handle_extract(
        update=update,
        context=context,
        test_id=test_id,
        paid_user=paid_user,
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "TestDeliveryService",
    "test_delivery_service",
    "extract_test",
]

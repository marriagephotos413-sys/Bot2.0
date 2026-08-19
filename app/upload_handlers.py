import asyncio
import io
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from telegram import (
    Document,
    Message,
    Update,
)
from telegram.ext import ContextTypes

from .config import CONFIG
from .database import db
from .github import github
from .telegram_utils import telegram_utils
from .queue_manager import queue_manager

logger = logging.getLogger(__name__)


class UploadHandlers:
    """
    TEST UPLOAD PIPELINE

    Admin:
        HTML / JSON / TXT upload
                ↓
        Caption/details parse
                ↓
        Questions extract
                ↓
        JSON validation
                ↓
        TCS HTML generate/update
                ↓
        GitHub upload
                ↓
        MongoDB में केवल metadata
                ↓
        Database Channel में backup
                ↓
        Index में available

    IMPORTANT:
        MongoDB में complete questions JSON save नहीं किया जाता।
        Questions GitHub के TCS HTML में रहते हैं।
    """

    # ============================================================
    # START UPLOAD
    # ============================================================

    async def start_upload(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await telegram_utils.require_admin(
            update
        ):
            return

        context.user_data[
            "upload_mode"
        ] = "single"

        context.user_data[
            "upload_files"
        ] = []

        text = (
            "📤 **TEST UPLOAD**\n\n"
            "एक Test file भेजें।\n\n"
            "Supported:\n"
            "• `.html`\n"
            "• `.json`\n"
            "• `.txt`\n\n"
            "Caption में Test की details दें।\n\n"
            "💡 Bulk upload के लिए लगातार कई files "
            "भेज सकते हैं और अंत में **DONE** भेजें।"
        )

        await self._reply(
            update,
            context,
            text,
        )

    # ============================================================
    # BULK MODE
    # ============================================================

    async def start_bulk_upload(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not await telegram_utils.require_admin(
            update
        ):
            return

        context.user_data[
            "upload_mode"
        ] = "bulk"

        context.user_data[
            "upload_files"
        ] = []

        text = (
            "📦 **BULK TEST UPLOAD**\n\n"
            "अब सभी Test files एक-एक करके भेजें।\n\n"
            "हर file के caption में उसकी details रखें।\n\n"
            "सभी files भेजने के बाद:\n"
            "👉 `DONE` भेजें\n\n"
            "Bot सभी Tests को queue में डालकर "
            "एक साथ process करेगा।"
        )

        await self._reply(
            update,
            context,
            text,
        )

    # ============================================================
    # DOCUMENT HANDLER
    # ============================================================

    async def handle_document(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> bool:

        user = update.effective_user
        message = update.effective_message

        if not user or not message:
            return False

        if user.id not in CONFIG.admin_ids:
            return False

        upload_mode = context.user_data.get(
            "upload_mode"
        )

        admin_action = context.user_data.get(
            "admin_action"
        )

        if (
            upload_mode is None
            and admin_action != "upload_test"
        ):
            return False

        document = message.document

        if not document:
            return False

        filename = (
            document.file_name
            or "test_file"
        )

        extension = (
            filename.lower()
            .rsplit(
                ".",
                1,
            )[-1]
            if "." in filename
            else ""
        )

        if extension not in (
            "html",
            "htm",
            "json",
            "txt",
        ):

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                (
                    "❌ Unsupported file.\n\n"
                    "Allowed: HTML, JSON, TXT"
                ),
            )

            return True

        # --------------------------------------------------------
        # Download
        # --------------------------------------------------------

        status = await telegram_utils.send_message(
            context.bot,
            message.chat_id,
            (
                "📥 **File Received**\n\n"
                f"📄 `{filename}`\n"
                "⏳ Downloading..."
            ),
            parse_mode="Markdown",
        )

        try:

            tg_file = await document.get_file()

            data = await tg_file.download_as_bytearray()

            file_bytes = bytes(
                data
            )

        except Exception as exc:

            logger.exception(
                "Telegram file download failed"
            )

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                (
                    "❌ File download failed.\n"
                    "कृपया फिर से upload करें।"
                ),
            )

            return True

        # --------------------------------------------------------
        # Caption
        # --------------------------------------------------------

        caption = (
            message.caption
            or ""
        )

        item = {
            "message_id": message.message_id,
            "filename": filename,
            "extension": extension,
            "bytes": file_bytes,
            "caption": caption,
            "document": document,
        }

        # --------------------------------------------------------
        # Bulk
        # --------------------------------------------------------

        if (
            upload_mode == "bulk"
            or admin_action == "upload_test"
        ):

            files = context.user_data.setdefault(
                "upload_files",
                [],
            )

            files.append(
                item
            )

            await telegram_utils.update_progress_message(
                context,
                status,
                (
                    "📦 **BULK QUEUE**\n\n"
                    f"📄 Added: `{filename}`\n"
                    f"📚 Total queued: **{len(files)}**\n\n"
                    "और files भेजें या `DONE` भेजें।"
                ),
                force=True,
            )

            context.user_data[
                "upload_mode"
            ] = "bulk"

            context.user_data[
                "admin_action"
            ] = "upload_test"

            return True

        return True

    # ============================================================
    # DONE
    # ============================================================

    async def handle_text(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> bool:

        user = update.effective_user
        message = update.effective_message

        if not user or not message:
            return False

        if user.id not in CONFIG.admin_ids:
            return False

        text = (
            message.text
            or ""
        ).strip()

        upload_mode = context.user_data.get(
            "upload_mode"
        )

        if (
            upload_mode in (
                "bulk",
                "single",
            )
            and text.upper() == "DONE"
        ):

            return await self.finish_upload(
                update,
                context,
            )

        return False

    # ============================================================
    # FINISH UPLOAD
    # ============================================================

    async def finish_upload(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        user = update.effective_user
        message = update.effective_message

        if not user or not message:
            return

        files = context.user_data.get(
            "upload_files",
            [],
        )

        if not files:

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                "❌ कोई file queue में नहीं है।",
            )

            return

        status = await telegram_utils.send_message(
            context.bot,
            message.chat_id,
            (
                "📤 **UPLOAD PROCESS STARTED**\n\n"
                f"📚 Total Files: **{len(files)}**\n"
                "⏳ Queue में add किया जा रहा है..."
            ),
            parse_mode="Markdown",
        )

        job_ids = []

        # --------------------------------------------------------
        # हर Test अलग job
        # --------------------------------------------------------

        for index, item in enumerate(
            files,
            start=1,
        ):

            job_id = await queue_manager.add_job(
                user_id=user.id,
                job_type="test_upload",
                payload={
                    "filename": item[
                        "filename"
                    ],
                    "extension": item[
                        "extension"
                    ],
                    "bytes": item[
                        "bytes"
                    ],
                    "caption": item[
                        "caption"
                    ],
                    "message_id": item[
                        "message_id"
                    ],
                },
                is_admin=True,
            )

            job_ids.append(
                job_id
            )

        if status:

            await telegram_utils.update_progress_message(
                context,
                status,
                (
                    "⚙️ **UPLOAD QUEUED**\n\n"
                    f"📚 Files: **{len(files)}**\n"
                    f"🆔 Jobs: **{len(job_ids)}**\n\n"
                    "अब processing शुरू होगी।"
                ),
                force=True,
            )

        # --------------------------------------------------------
        # Clear temporary upload session
        # --------------------------------------------------------

        context.user_data.pop(
            "upload_files",
            None,
        )

        context.user_data.pop(
            "upload_mode",
            None,
        )

        context.user_data.pop(
            "admin_action",
            None,
        )

    # ============================================================
    # PROCESS ONE UPLOAD JOB
    # ============================================================

    async def process_upload_job(
        self,
        job: Dict[str, Any],
    ) -> Dict[str, Any]:

        job_id = job[
            "job_id"
        ]

        payload = job.get(
            "payload",
            {},
        )

        file_bytes = payload.get(
            "bytes",
            b"",
        )

        filename = payload.get(
            "filename",
            "test",
        )

        extension = payload.get(
            "extension",
            "",
        )

        caption = payload.get(
            "caption",
            "",
        )

        # --------------------------------------------------------
        # Progress
        # --------------------------------------------------------

        await queue_manager.progress(
            job_id,
            10,
            "📥 File validate हो रही है...",
        )

        if not file_bytes:

            raise ValueError(
                "Uploaded file empty है।"
            )

        # --------------------------------------------------------
        # Parse metadata
        # --------------------------------------------------------

        metadata = self.parse_caption(
            caption
        )

        await queue_manager.progress(
            job_id,
            25,
            "🔍 Test details detect हो रही हैं...",
        )

        # --------------------------------------------------------
        # Extract questions
        # --------------------------------------------------------

        questions = self.extract_questions(
            file_bytes,
            extension,
        )

        if not questions:

            raise ValueError(
                "Questions extract नहीं हुए।"
            )

        await queue_manager.progress(
            job_id,
            45,
            (
                f"❓ {len(questions)} questions "
                "extract हो गए।"
            ),
        )

        # --------------------------------------------------------
        # Normalize
        # --------------------------------------------------------

        questions = self.normalize_questions(
            questions
        )

        # --------------------------------------------------------
        # Validate
        # --------------------------------------------------------

        validation = self.validate_questions(
            questions
        )

        if not validation[
            "valid"
        ]:

            raise ValueError(
                "Question validation failed: "
                + "; ".join(
                    validation[
                        "errors"
                    ][:10]
                )
            )

        await queue_manager.progress(
            job_id,
            55,
            "✅ Questions validated.",
        )

        # --------------------------------------------------------
        # Metadata fallback
        # --------------------------------------------------------

        metadata = self.complete_metadata(
            metadata,
            questions,
            filename,
        )

        # --------------------------------------------------------
        # Generate TCS HTML
        # --------------------------------------------------------

        await queue_manager.progress(
            job_id,
            65,
            "🧩 TCS HTML generate हो रहा है...",
        )

        html = self.generate_tcs_html(
            metadata,
            questions,
        )

        # --------------------------------------------------------
        # GitHub path
        # --------------------------------------------------------

        github_path = self.build_github_path(
            metadata
        )

        await queue_manager.progress(
            job_id,
            75,
            (
                "☁️ GitHub पर TCS HTML upload हो रहा है..."
            ),
        )

        github_result = github.upload_test(
            path=github_path,
            content=html,
            message=(
                "Add test: "
                + metadata["title"]
            ),
        )

        github_url = (
            github_result.get(
                "html_url"
            )
            or github_result.get(
                "download_url"
            )
            or ""
        )

        await queue_manager.progress(
            job_id,
            82,
            "💾 Test metadata database में save हो रहा है...",
        )

        # --------------------------------------------------------
        # MongoDB metadata only
        #
        # QUESTIONS यहाँ save नहीं होते।
        # --------------------------------------------------------

        test_id = db.create_test(
            title=metadata[
                "title"
            ],
            category=metadata[
                "category"
            ],
            exam=metadata[
                "exam"
            ],
            test_type=metadata[
                "test_type"
            ],
            year=metadata[
                "year"
            ],
            section=metadata.get(
                "section",
                "",
            ),
            subsection=metadata.get(
                "subsection",
                "",
            ),
            question_count=len(
                questions
            ),
            language=metadata.get(
                "language",
                "Hindi",
            ),
            shift=metadata.get(
                "shift",
                "",
            ),
            github_path=github_path,
            github_url=github_url,
            source_filename=filename,
            source_message_id=payload.get(
                "message_id"
            ),
        )

        await queue_manager.progress(
            job_id,
            90,
            "📢 Database Channel backup भेजा जा रहा है...",
        )

        # --------------------------------------------------------
        # Database Channel
        # --------------------------------------------------------

        # HTML को Bytes में भेजना।
        html_bytes = html.encode(
            "utf-8"
        )

        await telegram_utils.send_database_backup(
            self._bot_from_job(job),
            html_bytes,
            "tcs.html",
            self.database_caption(
                test_id,
                metadata,
                len(questions),
                github_url,
            ),
        )

        await queue_manager.progress(
            job_id,
            98,
            "📊 Index metadata update हो रहा है...",
        )

        db.mark_test_ready(
            test_id,
            github_path=github_path,
            github_url=github_url,
        )

        return {
            "test_id": test_id,
            "title": metadata[
                "title"
            ],
            "question_count": len(
                questions
            ),
            "github_path": github_path,
            "github_url": github_url,
        }

    # ============================================================
    # CAPTION PARSER
    # ============================================================

    def parse_caption(
        self,
        caption: str,
    ) -> Dict[str, str]:

        caption = (
            caption
            or ""
        )

        result = {
            "title": "",
            "series": "",
            "category": "",
            "exam": "",
            "section": "",
            "subsection": "",
            "test_type": "",
            "year": "",
            "language": "Hindi",
            "shift": "",
        }

        # --------------------------------------------------------
        # Exact user format
        #
        # 📚 ꜱᴇʀɪᴇꜱ: SSC CGL...
        # 🗂 ꜱᴇᴄᴛɪᴏɴ: ...
        # 📁 ꜱᴜʙꜱᴇᴄᴛɪᴏɴ: 2018 - 2019
        # ✅ ᴛᴇꜱᴛ: SSC CGL Previous Paper...
        # ❓ 100 qᴜᴇꜱᴛɪᴏɴꜱ • 🌐 Hindi
        # --------------------------------------------------------

        result[
            "series"
        ] = self.find_value(
            caption,
            [
                r"SERIES\s*:\s*(.+)",
                r"ꜱᴇʀɪᴇꜱ\s*:\s*(.+)",
            ],
        )

        result[
            "section"
        ] = self.find_value(
            caption,
            [
                r"SECTION\s*:\s*(.+)",
                r"ꜱᴇᴄᴛɪᴏɴ\s*:\s*(.+)",
            ],
        )

        result[
            "subsection"
        ] = self.find_value(
            caption,
            [
                r"SUBSECTION\s*:\s*(.+)",
                r"ꜱᴜʙꜱᴇᴄᴛɪᴏɴ\s*:\s*(.+)",
            ],
        )

        result[
            "title"
        ] = self.find_value(
            caption,
            [
                r"TEST\s*:\s*(.+)",
                r"ᴛᴇꜱᴛ\s*:\s*(.+)",
            ],
        )

        # --------------------------------------------------------
        # Question count
        # --------------------------------------------------------

        question_match = re.search(
            r"(\d+)\s*(?:Q(?:UESTIONS)?|qᴜᴇꜱᴛɪᴏɴꜱ)",
            caption,
            re.IGNORECASE,
        )

        if question_match:

            result[
                "question_count"
            ] = question_match.group(
                1
            )

        # --------------------------------------------------------
        # Language
        # --------------------------------------------------------

        language_match = re.search(
            r"(Hindi|English|Bilingual|हिंदी|अंग्रेजी)",
            caption,
            re.IGNORECASE,
        )

        if language_match:

            language = (
                language_match.group(
                    1
                )
            )

            if language.lower() == "हिंदी":

                language = "Hindi"

            result[
                "language"
            ] = language

        # --------------------------------------------------------
        # Shift
        # --------------------------------------------------------

        shift_match = re.search(
            r"(?:Shift|शिफ्ट)\s*[:\-]?\s*([0-9]+)",
            caption,
            re.IGNORECASE,
        )

        if shift_match:

            result[
                "shift"
            ] = (
                "Shift "
                + shift_match.group(
                    1
                )
            )

        # --------------------------------------------------------
        # Year
        # --------------------------------------------------------

        year_match = re.search(
            r"\b(20\d{2})\b",
            result[
                "subsection"
            ]
            + " "
            + result[
                "title"
            ],
        )

        if year_match:

            result[
                "year"
            ] = year_match.group(
                1
            )

        # --------------------------------------------------------
        # Exam auto-detection
        # --------------------------------------------------------

        full_text = (
            result[
                "series"
            ]
            + " "
            + result[
                "title"
            ]
        ).lower()

        exam_map = [
            (
                [
                    "ssc cgl",
                    "cgl",
                ],
                "SSC CGL",
            ),
            (
                [
                    "ssc gd",
                    "gd constable",
                ],
                "SSC GD",
            ),
            (
                [
                    "ssc chsl",
                    "chsl",
                ],
                "SSC CHSL",
            ),
            (
                [
                    "ssc mts",
                    "mts",
            ],
                "SSC MTS",
            ),
            (
                [
                    "ntpc",
                    "rrb ntpc",
                ],
                "RRB NTPC",
            ),
            (
                [
                    "rrb group d",
                    "rrb d group",
                    "group d",
                ],
                "RRB Group D",
            ),
            (
                [
                    "upsc",
                ],
                "UPSC",
            ),
            (
                [
                    "up police",
                ],
                "UP Police",
            ),
            (
                [
                    "delhi police",
                ],
                "Delhi Police",
            ),
        ]

        for keywords, exam_name in exam_map:

            if any(
                keyword in full_text
                for keyword in keywords
            ):

                result[
                    "exam"
                ] = exam_name

                break

        # --------------------------------------------------------
        # Category auto-detection
        # --------------------------------------------------------

        exam = result[
            "exam"
        ].lower()

        if exam.startswith(
            "ssc"
        ):

            result[
                "category"
            ] = "SSC"

        elif exam.startswith(
            "rrb"
        ):

            result[
                "category"
            ] = "RRB"

        elif exam == "UPSC":

            result[
                "category"
            ] = "UPSC"

        elif "police" in exam:

            result[
                "category"
            ] = "POLICE"

        else:

            result[
                "category"
            ] = "OTHER"

        # --------------------------------------------------------
        # Test Type
        # --------------------------------------------------------

        lower_caption = caption.lower()

        if (
            "pyq" in lower_caption
            or "previous paper" in lower_caption
            or "previous year" in lower_caption
            or "पिछले वर्ष" in caption
        ):

            result[
                "test_type"
            ] = "PYQ"

        elif (
            "mock" in lower_caption
            or "मॉक" in caption
        ):

            result[
                "test_type"
            ] = "Mock Test"

        else:

            result[
                "test_type"
            ] = "Other"

        return result

    # ============================================================
    # QUESTION EXTRACTION
    # ============================================================

    def extract_questions(
        self,
        file_bytes: bytes,
        extension: str,
    ) -> List[Dict[str, Any]]:

        if extension == "json":

            return self.extract_json(
                file_bytes
            )

        text = file_bytes.decode(
            "utf-8",
            errors="ignore",
        )

        # --------------------------------------------------------
        # If HTML contains JSON
        # --------------------------------------------------------

        questions = self.extract_embedded_json(
            text
        )

        if questions:

            return questions

        # --------------------------------------------------------
        # Generic HTML parser
        # --------------------------------------------------------

        return self.extract_html_questions(
            text
        )

    # ============================================================
    # JSON EXTRACTION
    # ============================================================

    def extract_json(
        self,
        file_bytes: bytes,
    ) -> List[Dict[str, Any]]:

        data = json.loads(
            file_bytes.decode(
                "utf-8-sig"
            )
        )

        if isinstance(
            data,
            list,
        ):

            return data

        if isinstance(
            data,
            dict,
        ):

            for key in (
                "questions",
                "data",
                "quiz",
                "items",
            ):

                value = data.get(
                    key
                )

                if isinstance(
                    value,
                    list,
                ):

                    return value

        raise ValueError(
            "JSON में questions array नहीं मिला।"
        )

    # ============================================================
    # EMBEDDED JSON
    # ============================================================

    def extract_embedded_json(
        self,
        html: str,
    ) -> List[Dict[str, Any]]:

        patterns = [
            r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
            r'<script[^>]*id=["\']questions["\'][^>]*>(.*?)</script>',
            r'<script[^>]*id=["\']questionData["\'][^>]*>(.*?)</script>',
        ]

        for pattern in patterns:

            matches = re.findall(
                pattern,
                html,
                flags=re.IGNORECASE
                | re.DOTALL,
            )

            for match in matches:

                try:

                    data = json.loads(
                        match.strip()
                    )

                    if isinstance(
                        data,
                        list,
                    ):

                        return data

                    if isinstance(
                        data,
                        dict,
                    ):

                        for key in (
                            "questions",
                            "data",
                            "items",
                        ):

                            if isinstance(
                                data.get(
                                    key
                                ),
                                list,
                            ):

                                return data[
                                    key
                                ]

                except Exception:

                    continue

        # --------------------------------------------------------
        # JS variable
        # --------------------------------------------------------

        variable_patterns = [
            r"(?:const|let|var)\s+questions\s*=\s*(\[[\s\S]*?\]);",
            r"(?:const|let|var)\s+questionData\s*=\s*(\[[\s\S]*?\]);",
        ]

        for pattern in variable_patterns:

            match = re.search(
                pattern,
                html,
                flags=re.IGNORECASE,
            )

            if not match:

                continue

            try:

                data = json.loads(
                    match.group(
                        1
                    )
                )

                if isinstance(
                    data,
                    list,
                ):

                    return data

            except Exception:

                continue

        return []

    # ============================================================
    # HTML QUESTIONS
    # ============================================================

    def extract_html_questions(
        self,
        html: str,
    ) -> List[Dict[str, Any]]:

        """
        Generic fallback parser.

        यह केवल common structures handle करता है।
        अगर source HTML का custom structure है तो
        parser में उसका selector add किया जा सकता है।
        """

        questions = []

        # --------------------------------------------------------
        # Try common question blocks
        # --------------------------------------------------------

        blocks = re.findall(
            r'<(?:div|section|article)'
            r'[^>]*class=["\'][^"\']*question[^"\']*["\']'
            r'[^>]*>(.*?)</(?:div|section|article)>',
            html,
            flags=re.IGNORECASE
            | re.DOTALL,
        )

        for index, block in enumerate(
            blocks,
            start=1,
        ):

            text = self.strip_html(
                block
            )

            if not text:

                continue

            options = self.extract_options(
                block
            )

            questions.append(
                {
                    "id": index,
                    "question": text,
                    "options": options,
                    "answer": None,
                }
            )

        return questions

    # ============================================================
    # OPTIONS
    # ============================================================

    def extract_options(
        self,
        html: str,
    ) -> List[str]:

        options = []

        matches = re.findall(
            r'<(?:li|div|span|label)'
            r'[^>]*class=["\'][^"\']*option[^"\']*["\']'
            r'[^>]*>(.*?)</(?:li|div|span|label)>',
            html,
            flags=re.IGNORECASE
            | re.DOTALL,
        )

        for match in matches:

            value = self.strip_html(
                match
            )

            if value:

                options.append(
                    value
                )

        return options[:4]

    # ============================================================
    # NORMALIZE
    # ============================================================

    def normalize_questions(
        self,
        questions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        result = []

        for index, item in enumerate(
            questions,
            start=1,
        ):

            if not isinstance(
                item,
                dict,
            ):

                continue

            question = (
                item.get(
                    "question"
                )
                or item.get(
                    "questionText"
                )
                or item.get(
                    "text"
                )
                or ""
            )

            options = (
                item.get(
                    "options"
                )
                or item.get(
                    "choices"
                )
                or item.get(
                    "answers"
                )
                or []
            )

            if isinstance(
                options,
                dict,
            ):

                options = list(
                    options.values()
                )

            answer = (
                item.get(
                    "answer"
                )
                if "answer" in item
                else item.get(
                    "correctAnswer"
                )
            )

            explanation = (
                item.get(
                    "explanation"
                )
                or item.get(
                    "solution"
                )
                or ""
            )

            result.append(
                {
                    "id": index,
                    "question": str(
                        question
                    ).strip(),
                    "options": [
                        str(option).strip()
                        for option in options
                    ][:4],
                    "answer": answer,
                    "explanation": explanation,
                }
            )

        return result

    # ============================================================
    # VALIDATE
    # ============================================================

    def validate_questions(
        self,
        questions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        errors = []

        if not questions:

            errors.append(
                "No questions found"
            )

            return {
                "valid": False,
                "errors": errors,
            }

        for index, question in enumerate(
            questions,
            start=1,
        ):

            if not question.get(
                "question"
            ):

                errors.append(
                    f"Q{index}: question missing"
                )

            options = question.get(
                "options",
                [],
            )

            if len(options) < 2:

                errors.append(
                    f"Q{index}: options missing"
                )

            if len(errors) >= 50:

                break

        return {
            "valid": not errors,
            "errors": errors,
        }

    # ============================================================
    # COMPLETE METADATA
    # ============================================================

    def complete_metadata(
        self,
        metadata: Dict[str, str],
        questions: List[Dict[str, Any]],
        filename: str,
    ) -> Dict[str, str]:

        if not metadata.get(
            "title"
        ):

            metadata[
                "title"
            ] = (
                filename
                .rsplit(
                    ".",
                    1,
                )[0]
            )

        if not metadata.get(
            "year"
        ):

            year_match = re.search(
                r"(20\d{2})",
                metadata[
                    "title"
                ],
            )

            if year_match:

                metadata[
                    "year"
                ] = year_match.group(
                    1
                )

            else:

                metadata[
                    "year"
                ] = "Other"

        if not metadata.get(
            "exam"
        ):

            metadata[
                "exam"
            ] = "Other"

        if not metadata.get(
            "category"
        ):

            metadata[
                "category"
            ] = "OTHER"

        if not metadata.get(
            "test_type"
        ):

            metadata[
                "test_type"
            ] = "Other"

        return metadata

    # ============================================================
    # GITHUB PATH
    # ============================================================

    def build_github_path(
        self,
        metadata: Dict[str, str],
    ) -> str:

        category = self.safe_path(
            metadata.get(
                "category",
                "OTHER",
            )
        )

        exam = self.safe_path(
            metadata.get(
                "exam",
                "OTHER",
            )
        )

        test_type = self.safe_path(
            metadata.get(
                "test_type",
                "Other",
            )
        )

        year = self.safe_path(
            metadata.get(
                "year",
                "Other",
            )
        )

        title = self.safe_path(
            metadata.get(
                "title",
                "test",
            )
        )

        return (
            f"tests/"
            f"{category}/"
            f"{exam}/"
            f"{test_type}/"
            f"{year}/"
            f"{title}.html"
        )

    # ============================================================
    # TCS HTML GENERATOR
    # ============================================================

    def generate_tcs_html(
        self,
        metadata: Dict[str, str],
        questions: List[Dict[str, Any]],
    ) -> str:

        # --------------------------------------------------------
        # JSON safely embed
        # --------------------------------------------------------

        questions_json = json.dumps(
            questions,
            ensure_ascii=False,
        )

        title = self.escape_html(
            metadata.get(
                "title",
                "TCS Mock Test",
            )
        )

        exam = self.escape_html(
            metadata.get(
                "exam",
                "",
            )
        )

        year = self.escape_html(
            metadata.get(
                "year",
                "",
            )
        )

        return f"""<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width,initial-scale=1.0">

<title>{title}</title>

<style>
* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f2f4f8;
    color: #222;
}}

header {{
    background: #111827;
    color: white;
    padding: 16px;
    text-align: center;
}}

.container {{
    max-width: 1000px;
    margin: auto;
    padding: 20px;
}}

.question {{
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 3px 12px rgba(0,0,0,.08);
}}

.option {{
    display: block;
    padding: 12px;
    margin: 8px 0;
    border: 1px solid #ddd;
    border-radius: 8px;
    cursor: pointer;
}}

button {{
    border: 0;
    padding: 12px 18px;
    border-radius: 8px;
    cursor: pointer;
}}

#startBtn {{
    background: #2563eb;
    color: white;
}}

#submitBtn {{
    background: #16a34a;
    color: white;
}}

.hidden {{
    display: none;
}}

.result {{
    background: white;
    padding: 20px;
    border-radius: 12px;
}}
</style>
</head>

<body>

<header>
    <h2>{title}</h2>
    <div>{exam} • {year}</div>
</header>

<div class="container">

<div id="startScreen">
    <h3>📚 TCS Mock Test</h3>
    <p>Total Questions:
       <b>{len(questions)}</b>
    </p>

    <button id="startBtn"
            onclick="startTest()">
        🚀 Start Test
    </button>
</div>

<div id="testScreen"
     class="hidden">

    <div id="questionBox"></div>

    <button id="submitBtn"
            onclick="submitTest()">
        Submit Test
    </button>
</div>

<div id="result"
     class="result hidden">
</div>

</div>

<script>
const QUESTIONS = {questions_json};

let current = 0;
let answers = [];

function startTest() {{
    document
        .getElementById("startScreen")
        .classList.add("hidden");

    document
        .getElementById("testScreen")
        .classList.remove("hidden");

    renderQuestion();
}}

function renderQuestion() {{
    const q = QUESTIONS[current];

    let html = `
        <div class="question">
            <h3>
                Q${{current + 1}}.
                ${{q.question}}
            </h3>
    `;

    (q.options || []).forEach(
        (option, index) => {{
            const checked =
                answers[current] === index
                    ? "checked"
                    : "";

            html += `
                <label class="option">
                    <input
                        type="radio"
                        name="option"
                        value="${{index}}"
                        ${{checked}}
                        onchange="
                            answers[current] =
                            Number(this.value)
                        "
                    >
                    ${{option}}
                </label>
            `;
        }}
    );

    html += `
        <button onclick="previousQuestion()">
            ⬅️ Previous
        </button>

        <button onclick="nextQuestion()">
            Next ➡️
        </button>

        </div>
    `;

    document
        .getElementById("questionBox")
        .innerHTML = html;
}}

function nextQuestion() {{
    if (
        current <
        QUESTIONS.length - 1
    ) {{
        current++;
        renderQuestion();
    }}
}}

function previousQuestion() {{
    if (current > 0) {{
        current--;
        renderQuestion();
    }}
}}

function submitTest() {{
    let correct = 0;

    QUESTIONS.forEach(
        (q, index) => {{
            const answer =
                answers[index];

            const correctAnswer =
                q.answer;

            if (
                answer !== undefined &&
                (
                    answer === correctAnswer ||
                    String(answer) ===
                    String(correctAnswer)
                )
            ) {{
                correct++;
            }}
        }}
    );

    const total =
        QUESTIONS.length;

    const percentage =
        total
            ? ((correct / total) * 100)
                .toFixed(2)
            : 0;

    document
        .getElementById("testScreen")
        .classList.add("hidden");

    const result =
        document.getElementById("result");

    result.classList.remove("hidden");

    result.innerHTML = `
        <h2>📊 Result</h2>

        <p>
            Total:
            <b>${{total}}</b>
        </p>

        <p>
            Correct:
            <b>${{correct}}</b>
        </p>

        <p>
            Percentage:
            <b>${{percentage}}%</b>
        </p>
    `;
}}
</script>

</body>
</html>
"""

    # ============================================================
    # DATABASE CAPTION
    # ============================================================

    def database_caption(
        self,
        test_id: str,
        metadata: Dict[str, str],
        question_count: int,
        github_url: str,
    ) -> str:

        return (
            "📚 **TEST DATABASE BACKUP**\n\n"
            f"🆔 Test ID: `{test_id}`\n"
            f"📚 Series: {metadata.get('series', '-')}\n"
            f"🎯 Exam: {metadata.get('exam', '-')}\n"
            f"🗂 Section: {metadata.get('section', '-')}\n"
            f"📁 Subsection: {metadata.get('subsection', '-')}\n"
            f"📝 Test: {metadata.get('title', '-')}\n"
            f"❓ Questions: {question_count}\n"
            f"🌐 Language: {metadata.get('language', 'Hindi')}\n"
            f"📅 Year: {metadata.get('year', '-')}\n\n"
            f"🌐 GitHub: {github_url or '-'}"
        )

    # ============================================================
    # BOT FROM JOB
    # ============================================================

    def _bot_from_job(
        self,
        job: Dict[str, Any],
    ):
        """
        Queue worker में Bot object direct नहीं रखा जाता।

        इस implementation में Telegram bot instance
        context से pass करना बेहतर है।

        इसलिए upload processor को app startup पर
        Telegram bot reference दिया जाना चाहिए।
        """

        if hasattr(
            self,
            "bot",
        ):

            return self.bot

        raise RuntimeError(
            "Telegram Bot reference not configured."
        )

    # ============================================================
    # UTILS
    # ============================================================

    @staticmethod
    def find_value(
        text: str,
        patterns: List[str],
    ) -> str:

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE
                | re.MULTILINE,
            )

            if match:

                value = match.group(
                    1
                ).strip()

                # Emoji/extra formatting हटाना
                value = re.sub(
                    r"\s+",
                    " ",
                    value,
                )

                return value

        return ""

    @staticmethod
    def strip_html(
        value: str,
    ) -> str:

        value = re.sub(
            r"<script[\s\S]*?</script>",
            " ",
            value,
            flags=re.IGNORECASE,
        )

        value = re.sub(
            r"<style[\s\S]*?</style>",
            " ",
            value,
            flags=re.IGNORECASE,
        )

        value = re.sub(
            r"<[^>]+>",
            " ",
            value,
        )

        value = (
            value
            .replace(
                "&nbsp;",
                " ",
            )
            .replace(
                "&amp;",
                "&",
            )
            .replace(
                "&lt;",
                "<",
            )
            .replace(
                "&gt;",
                ">",
            )
            .replace(
                "&quot;",
                '"',
            )
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    @staticmethod
    def escape_html(
        value: str,
    ) -> str:

        return (
            str(value)
            .replace(
                "&",
                "&amp;",
            )
            .replace(
                "<",
                "&lt;",
            )
            .replace(
                ">",
                "&gt;",
            )
            .replace(
                '"',
                "&quot;",
            )
        )

    @staticmethod
    def safe_path(
        value: str,
    ) -> str:

        value = str(
            value or "other"
        )

        value = re.sub(
            r"[^\w\-. ]+",
            "",
            value,
            flags=re.UNICODE,
        )

        value = re.sub(
            r"\s+",
            "_",
            value,
        )

        return value[:100]

    async def _reply(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
    ):

        message = update.effective_message

        if message:

            await telegram_utils.send_message(
                context.bot,
                message.chat_id,
                text,
                parse_mode="Markdown",
            )


# ================================================================
# SINGLE INSTANCE
# ================================================================

upload_handlers = UploadHandlers()

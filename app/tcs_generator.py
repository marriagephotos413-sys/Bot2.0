import json
import logging
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TCSGeneratorError(Exception):
    """Raised when TCS HTML generation fails."""


class TCSGenerator:
    """
    Parsed questions को तुम्हारे master `tcs.html` template
    के अंदर inject करता है।

    IMPORTANT:

    MongoDB:
        ❌ Questions JSON नहीं

    GitHub:
        ✅ Generated tcs.html
        ✅ Embedded questions JSON

    Database Channel:
        ✅ Generated tcs.html backup
    """

    # ============================================================
    # PUBLIC METHOD
    # ============================================================

    def generate(
        self,
        template_html: bytes,
        parsed_test: Dict[str, Any],
        test_id: str,
    ) -> bytes:

        if not template_html:
            raise TCSGeneratorError(
                "TCS template खाली है।"
            )

        if not parsed_test:
            raise TCSGeneratorError(
                "Parsed test data उपलब्ध नहीं है।"
            )

        questions = parsed_test.get(
            "questions",
            [],
        )

        if not questions:
            raise TCSGeneratorError(
                "Questions नहीं मिले।"
            )

        title = (
            parsed_test.get(
                "source_title"
            )
            or parsed_test.get(
                "metadata",
                {},
            ).get(
                "title"
            )
            or "Test"
        )

        # --------------------------------------------------------
        # Standard test JSON
        # --------------------------------------------------------

        test_json = self.build_test_json(
            parsed_test,
            test_id,
            title,
        )

        # --------------------------------------------------------
        # Template decode
        # --------------------------------------------------------

        html = template_html.decode(
            "utf-8",
            errors="ignore",
        )

        # --------------------------------------------------------
        # Inject JSON
        # --------------------------------------------------------

        html = self.inject_json(
            html,
            test_json,
        )

        # --------------------------------------------------------
        # Update basic title
        # --------------------------------------------------------

        html = self.update_html_title(
            html,
            title,
        )

        # --------------------------------------------------------
        # Update optional metadata
        # --------------------------------------------------------

        html = self.inject_metadata(
            html,
            test_json,
        )

        # --------------------------------------------------------
        # Validate
        # --------------------------------------------------------

        self.validate_generated_html(
            html
        )

        return html.encode(
            "utf-8"
        )

    # ============================================================
    # BUILD TEST JSON
    # ============================================================

    def build_test_json(
        self,
        parsed_test: Dict[str, Any],
        test_id: str,
        title: str,
    ) -> Dict[str, Any]:

        metadata = deepcopy(
            parsed_test.get(
                "metadata",
                {},
            )
        )

        questions = deepcopy(
            parsed_test.get(
                "questions",
                [],
            )
        )

        # --------------------------------------------------------
        # Normalize question numbering
        # --------------------------------------------------------

        normalized_questions = []

        for index, question in enumerate(
            questions,
            start=1,
        ):

            q = deepcopy(
                question
            )

            q["n"] = q.get(
                "n",
                index,
            )

            q["text"] = str(
                q.get(
                    "text",
                    "",
                )
            )

            q["options"] = [
                str(option)
                for option in q.get(
                    "options",
                    [],
                )
            ]

            # ----------------------------------------------------
            # Preserve answer index
            # ----------------------------------------------------

            correct = q.get(
                "correct"
            )

            if correct is not None:

                try:

                    q["correct"] = int(
                        correct
                    )

                except Exception:

                    q["correct"] = None

            # ----------------------------------------------------
            # Preserve solution
            # ----------------------------------------------------

            q["solution"] = str(
                q.get(
                    "solution",
                    "",
                )
            )

            normalized_questions.append(
                q
            )

        return {
            "testId": test_id,

            "title": title,

            "exam": metadata.get(
                "exam",
                "Other",
            ),

            "testType": metadata.get(
                "test_type",
                "Other",
            ),

            "year": metadata.get(
                "year",
                "Other",
            ),

            "shift": metadata.get(
                "shift",
                "",
            ),

            "language": metadata.get(
                "language",
                "Hindi",
            ),

            "questionCount": len(
                normalized_questions
            ),

            "timeMinutes": metadata.get(
                "time_minutes",
                0,
            ),

            "positiveMarks": metadata.get(
                "positive_marks",
                0,
            ),

            "negativeMarks": metadata.get(
                "negative_marks",
                0,
            ),

            "totalMarks": metadata.get(
                "total_marks",
                0,
            ),

            "questions": (
                normalized_questions
            ),
        }

    # ============================================================
    # JSON INJECTION
    # ============================================================

    def inject_json(
        self,
        html: str,
        test_json: Dict[str, Any],
    ) -> str:

        # ========================================================
        # METHOD 1
        #
        # Our recommended template marker:
        #
        # <!-- TEST_JSON_START -->
        # ...
        # <!-- TEST_JSON_END -->
        # ========================================================

        marker_pattern = re.compile(
            r"<!--\s*TEST_JSON_START\s*-->"
            r".*?"
            r"<!--\s*TEST_JSON_END\s*-->",
            flags=re.I | re.S,
        )

        if marker_pattern.search(
            html
        ):

            block = self.build_marker_block(
                test_json
            )

            return marker_pattern.sub(
                block,
                html,
                count=1,
            )

        # ========================================================
        # METHOD 2
        #
        # Existing template:
        #
        # const hardjson = {...};
        # ========================================================

        replaced = self.replace_hardjson(
            html,
            test_json,
        )

        if replaced is not None:

            return replaced

        # ========================================================
        # METHOD 3
        #
        # Existing template:
        #
        # window.TEST_DATA = ...
        # ========================================================

        replaced = self.replace_test_data(
            html,
            test_json,
        )

        if replaced is not None:

            return replaced

        # ========================================================
        # METHOD 4
        #
        # Existing template:
        #
        # window.questionsData = ...
        # ========================================================

        replaced = self.replace_variable(
            html,
            "questionsData",
            test_json.get(
                "questions",
                [],
            ),
        )

        if replaced is not None:

            return replaced

        # ========================================================
        # METHOD 5
        #
        # Existing template:
        #
        # Q_DATA = [...]
        # ========================================================

        replaced = self.replace_variable(
            html,
            "Q_DATA",
            self.build_q_data(
                test_json
            ),
        )

        if replaced is not None:

            return replaced

        # ========================================================
        # Nothing found
        # ========================================================

        raise TCSGeneratorError(
            "TCS template में JSON injection point नहीं मिला.\n"
            "Template में TEST_JSON_START/END markers "
            "या hardjson variable होना चाहिए।"
        )

    # ============================================================
    # MARKER BLOCK
    # ============================================================

    def build_marker_block(
        self,
        test_json: Dict[str, Any],
    ) -> str:

        compact_json = json.dumps(
            test_json,
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
        )

        return (
            "<!-- TEST_JSON_START -->\n"
            "<script>\n"
            "window.TEST_DATA = "
            f"{compact_json};\n"
            "</script>\n"
            "<!-- TEST_JSON_END -->"
        )

    # ============================================================
    # HARDJSON REPLACEMENT
    # ============================================================

    def replace_hardjson(
        self,
        html: str,
        test_json: Dict[str, Any],
    ) -> Optional[str]:

        match = re.search(
            r"(\b(?:const|let|var)\s+hardjson\s*=\s*)",
            html,
            flags=re.I,
        )

        if not match:

            return None

        start = match.end()

        # First { after assignment
        object_start = html.find(
            "{",
            start,
        )

        if object_start < 0:

            return None

        object_end = self.find_balanced(
            html,
            object_start,
            "{",
            "}",
        )

        if object_end < 0:

            raise TCSGeneratorError(
                "hardjson object properly close नहीं हुआ।"
            )

        json_text = json.dumps(
            test_json,
            ensure_ascii=False,
            indent=2,
        )

        return (
            html[:object_start]
            + json_text
            + html[object_end + 1:]
        )

    # ============================================================
    # TEST DATA REPLACEMENT
    # ============================================================

    def replace_test_data(
        self,
        html: str,
        test_json: Dict[str, Any],
    ) -> Optional[str]:

        match = re.search(
            r"(\bwindow\.TEST_DATA\s*=\s*)",
            html,
            flags=re.I,
        )

        if not match:

            return None

        start = match.end()

        object_start = html.find(
            "{",
            start,
        )

        if object_start < 0:

            return None

        object_end = self.find_balanced(
            html,
            object_start,
            "{",
            "}",
        )

        if object_end < 0:

            return None

        replacement = json.dumps(
            test_json,
            ensure_ascii=False,
            indent=2,
        )

        return (
            html[:object_start]
            + replacement
            + html[object_end + 1:]
        )

    # ============================================================
    # GENERIC VARIABLE REPLACEMENT
    # ============================================================

    def replace_variable(
        self,
        html: str,
        variable_name: str,
        value: Any,
    ) -> Optional[str]:

        match = re.search(
            rf"(\b(?:const|let|var)\s+"
            rf"{re.escape(variable_name)}\s*=\s*)",
            html,
            flags=re.I,
        )

        if not match:

            return None

        start = match.end()

        first_array = html.find(
            "[",
            start,
        )

        if first_array < 0:

            return None

        array_end = self.find_balanced(
            html,
            first_array,
            "[",
            "]",
        )

        if array_end < 0:

            return None

        replacement = json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )

        return (
            html[:first_array]
            + replacement
            + html[array_end + 1:]
        )

    # ============================================================
    # Q_DATA CONVERSION
    # ============================================================

    def build_q_data(
        self,
        test_json: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        result = []

        for index, question in enumerate(
            test_json.get(
                "questions",
                [],
            ),
            start=1,
        ):

            result.append(
                {
                    "n": question.get(
                        "n",
                        index,
                    ),

                    "si": question.get(
                        "section",
                        0,
                    ),

                    "text": question.get(
                        "text",
                        "",
                    ),

                    "comp": "",

                    "opts": question.get(
                        "options",
                        [],
                    ),

                    "cidx": question.get(
                        "correct"
                    ),

                    "sol": question.get(
                        "solution",
                        "",
                    ),

                    "pos": question.get(
                        "marks",
                        0,
                    ),

                    "neg": question.get(
                        "negative",
                        0,
                    ),
                }
            )

        return result

    # ============================================================
    # HTML TITLE
    # ============================================================

    def update_html_title(
        self,
        html: str,
        title: str,
    ) -> str:

        safe_title = (
            self.escape_html(
                title
            )
        )

        pattern = re.compile(
            r"<title\b[^>]*>.*?</title>",
            flags=re.I | re.S,
        )

        replacement = (
            f"<title>{safe_title}</title>"
        )

        if pattern.search(
            html
        ):

            return pattern.sub(
                replacement,
                html,
                count=1,
            )

        return (
            "<title>"
            + safe_title
            + "</title>\n"
            + html
        )

    # ============================================================
    # OPTIONAL META INJECTION
    # ============================================================

    def inject_metadata(
        self,
        html: str,
        test_json: Dict[str, Any],
    ) -> str:

        marker = (
            "<!-- TEST_METADATA -->"
        )

        if marker not in html:

            return html

        metadata = {
            "testId": test_json.get(
                "testId"
            ),

            "exam": test_json.get(
                "exam"
            ),

            "type": test_json.get(
                "testType"
            ),

            "year": test_json.get(
                "year"
            ),

            "shift": test_json.get(
                "shift"
            ),

            "questions": test_json.get(
                "questionCount"
            ),
        }

        block = (
            marker
            + "\n"
            + "<script>\n"
            + "window.TEST_METADATA = "
            + json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
            )
            + ";\n"
            + "</script>"
        )

        return html.replace(
            marker,
            block,
            1,
        )

    # ============================================================
    # BALANCED OBJECT FINDER
    # ============================================================

    def find_balanced(
        self,
        text: str,
        start: int,
        opening: str,
        closing: str,
    ) -> int:

        depth = 0

        in_string = False
        quote = ""

        escape = False

        for index in range(
            start,
            len(text),
        ):

            char = text[index]

            if in_string:

                if escape:

                    escape = False

                    continue

                if char == "\\":
                    escape = True
                    continue

                if char == quote:
                    in_string = False

                continue

            if char in (
                '"',
                "'",
                "`",
            ):

                in_string = True
                quote = char

                continue

            if char == opening:

                depth += 1

            elif char == closing:

                depth -= 1

                if depth == 0:

                    return index

        return -1

    # ============================================================
    # VALIDATION
    # ============================================================

    def validate_generated_html(
        self,
        html: str,
    ) -> None:

        if not html.strip():

            raise TCSGeneratorError(
                "Generated HTML खाली है।"
            )

        # --------------------------------------------------------
        # Basic HTML
        # --------------------------------------------------------

        lower = html.lower()

        if "<html" not in lower:

            raise TCSGeneratorError(
                "Generated file में HTML document नहीं मिला।"
            )

        # --------------------------------------------------------
        # JSON markers
        # --------------------------------------------------------

        has_test_data = (
            "window.TEST_DATA"
            in html
        )

        has_hardjson = bool(
            re.search(
                r"\bhardjson\s*=",
                html,
                flags=re.I,
            )
        )

        has_q_data = bool(
            re.search(
                r"\bQ_DATA\s*=",
                html,
                flags=re.I,
            )
        )

        has_questions = (
            '"questions"'
            in html
        )

        if not (
            has_test_data
            or has_hardjson
            or has_q_data
            or has_questions
        ):

            raise TCSGeneratorError(
                "Generated HTML में Test JSON नहीं मिला।"
            )

    # ============================================================
    # HTML ESCAPE
    # ============================================================

    @staticmethod
    def escape_html(
        value: str,
    ) -> str:

        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )


# ================================================================
# SINGLE GENERATOR INSTANCE
# ================================================================

tcs_generator = TCSGenerator()

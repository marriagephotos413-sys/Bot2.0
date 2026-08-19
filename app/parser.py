import ast
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class TestParserError(Exception):
    """Raised when a Test HTML cannot be parsed."""


class UniversalTestParser:
    """
    Universal HTML Test Parser.

    Supported formats:

    FORMAT 1
    --------
    let questionsData = [
        ...
    ];

    FORMAT 2
    --------
    let Q_DATA = [
        ...
    ];

    + optional:

    let Q_MAP = {
        ...
    };

    Parser का output एक common structure होगा।

    IMPORTANT:
    Questions JSON MongoDB में save नहीं होगा।
    यह data आगे TCS HTML generator को दिया जाएगा।
    """

    # ============================================================
    # PUBLIC API
    # ============================================================

    def parse(
        self,
        html_bytes: bytes,
        filename: str = "",
    ) -> Dict[str, Any]:

        if not html_bytes:
            raise TestParserError(
                "HTML file खाली है।"
            )

        try:
            text = html_bytes.decode(
                "utf-8",
                errors="ignore",
            )
        except Exception as exc:
            raise TestParserError(
                "HTML को UTF-8 में पढ़ा नहीं जा सका।"
            ) from exc

        soup = BeautifulSoup(
            text,
            "html.parser",
        )

        title = self._extract_title(
            soup,
            text,
            filename,
        )

        # --------------------------------------------------------
        # Format detection
        # --------------------------------------------------------

        format_name = self.detect_format(
            text
        )

        if format_name == "questionsData":

            questions_raw = (
                self.extract_array_variable(
                    text,
                    "questionsData",
                )
            )

            qmap = {}

        elif format_name == "Q_DATA":

            questions_raw = (
                self.extract_array_variable(
                    text,
                    "Q_DATA",
                )
            )

            qmap = self.extract_object_variable(
                text,
                "Q_MAP",
            )

        else:

            raise TestParserError(
                "Supported question data नहीं मिला।\n"
                "Expected: questionsData या Q_DATA."
            )

        if not isinstance(
            questions_raw,
            list,
        ):

            raise TestParserError(
                "Question data array format में नहीं है।"
            )

        questions = []

        for index, raw_question in enumerate(
            questions_raw,
            start=1,
        ):

            try:

                normalized = (
                    self.normalize_question(
                        raw_question,
                        index,
                        qmap,
                    )
                )

                questions.append(
                    normalized
                )

            except Exception as exc:

                logger.exception(
                    "Question parse failed: %s",
                    index,
                )

                raise TestParserError(
                    f"Question {index} parse नहीं हुआ: "
                    f"{exc}"
                ) from exc

        if not questions:

            raise TestParserError(
                "एक भी valid question नहीं मिला।"
            )

        metadata = self.extract_metadata(
            text=text,
            soup=soup,
            title=title,
            question_count=len(questions),
        )

        return {
            "format": format_name,

            "source_filename": filename,

            "source_title": title,

            "metadata": metadata,

            "questions": questions,

            "question_count": len(
                questions
            ),
        }

    # ============================================================
    # FORMAT DETECTION
    # ============================================================

    def detect_format(
        self,
        text: str,
    ) -> Optional[str]:

        if re.search(
            r"\b(?:let|const|var)\s+questionsData\s*=",
            text,
            flags=re.I,
        ):

            return "questionsData"

        if re.search(
            r"\b(?:let|const|var)\s+Q_DATA\s*=",
            text,
            flags=re.I,
        ):

            return "Q_DATA"

        return None

    # ============================================================
    # JAVASCRIPT VARIABLE EXTRACTION
    # ============================================================

    def extract_array_variable(
        self,
        text: str,
        variable_name: str,
    ) -> List[Any]:

        match = re.search(
            rf"\b(?:let|const|var)\s+"
            rf"{re.escape(variable_name)}\s*=",
            text,
            flags=re.I,
        )

        if not match:

            raise TestParserError(
                f"{variable_name} variable नहीं मिला।"
            )

        start = match.end()

        # पहले "[" ढूँढेंगे।
        array_start = text.find(
            "[",
            start,
        )

        if array_start < 0:

            raise TestParserError(
                f"{variable_name} array start नहीं मिला।"
            )

        array_text = self.extract_balanced(
            text,
            array_start,
            "[",
            "]",
        )

        return self.parse_js_data(
            array_text
        )

    def extract_object_variable(
        self,
        text: str,
        variable_name: str,
    ) -> Dict[str, Any]:

        match = re.search(
            rf"\b(?:let|const|var)\s+"
            rf"{re.escape(variable_name)}\s*=",
            text,
            flags=re.I,
        )

        if not match:

            return {}

        start = match.end()

        object_start = text.find(
            "{",
            start,
        )

        if object_start < 0:

            return {}

        object_text = self.extract_balanced(
            text,
            object_start,
            "{",
            "}",
        )

        try:

            value = self.parse_js_data(
                object_text
            )

            if isinstance(
                value,
                dict,
            ):

                return value

        except Exception:

            logger.warning(
                "Unable to parse %s",
                variable_name,
            )

        return {}

    # ============================================================
    # BALANCED BRACKET EXTRACTOR
    # ============================================================

    def extract_balanced(
        self,
        text: str,
        start: int,
        opening: str,
        closing: str,
    ) -> str:

        depth = 0

        in_string = False

        string_char = ""

        escape = False

        # JS template literals
        in_template = False

        for index in range(
            start,
            len(text),
        ):

            char = text[index]

            # ----------------------------------------------------
            # String handling
            # ----------------------------------------------------

            if in_string:

                if escape:

                    escape = False

                    continue

                if char == "\\":

                    escape = True

                    continue

                if char == string_char:

                    in_string = False

                continue

            if in_template:

                if escape:

                    escape = False

                    continue

                if char == "\\":

                    escape = True

                    continue

                if char == "`":

                    in_template = False

                continue

            # ----------------------------------------------------
            # Start string
            # ----------------------------------------------------

            if char in (
                '"',
                "'",
            ):

                in_string = True

                string_char = char

                continue

            if char == "`":

                in_template = True

                continue

            # ----------------------------------------------------
            # Bracket depth
            # ----------------------------------------------------

            if char == opening:

                depth += 1

            elif char == closing:

                depth -= 1

                if depth == 0:

                    return text[
                        start:index + 1
                    ]

        raise TestParserError(
            "JavaScript data structure incomplete है।"
        )

    # ============================================================
    # JS DATA PARSER
    # ============================================================

    def parse_js_data(
        self,
        source: str,
    ) -> Any:

        source = source.strip()

        # --------------------------------------------------------
        # First try strict JSON
        # --------------------------------------------------------

        try:

            return json.loads(
                source
            )

        except Exception:
            pass

        # --------------------------------------------------------
        # Remove JS comments
        # --------------------------------------------------------

        cleaned = self.remove_js_comments(
            source
        )

        # --------------------------------------------------------
        # Convert common JS syntax to Python
        # --------------------------------------------------------

        cleaned = self.convert_js_to_python(
            cleaned
        )

        try:

            return ast.literal_eval(
                cleaned
            )

        except Exception as exc:

            raise TestParserError(
                "JavaScript object/array parse नहीं हुआ।"
            ) from exc

    # ============================================================
    # JS COMMENT REMOVAL
    # ============================================================

    def remove_js_comments(
        self,
        source: str,
    ) -> str:

        # Safe enough for normal test-data blocks.
        source = re.sub(
            r"/\*[\s\S]*?\*/",
            "",
            source,
        )

        source = re.sub(
            r"(^|\s)//.*?$",
            r"\1",
            source,
            flags=re.M,
        )

        return source

    # ============================================================
    # JS → PYTHON NORMALIZATION
    # ============================================================

    def convert_js_to_python(
        self,
        source: str,
    ) -> str:

        # --------------------------------------------------------
        # JS booleans
        # --------------------------------------------------------

        source = re.sub(
            r"\btrue\b",
            "True",
            source,
            flags=re.I,
        )

        source = re.sub(
            r"\bfalse\b",
            "False",
            source,
            flags=re.I,
        )

        source = re.sub(
            r"\bnull\b",
            "None",
            source,
            flags=re.I,
        )

        # --------------------------------------------------------
        # Object keys
        #
        # { question: "...", answer: 1 }
        #
        # becomes
        #
        # { "question": "...", "answer": 1 }
        # --------------------------------------------------------

        source = re.sub(
            r"([{\[,]\s*)"
            r"([A-Za-z_$][A-Za-z0-9_$-]*)"
            r"\s*:",
            r'\1"\2":',
            source,
        )

        return source

    # ============================================================
    # QUESTION NORMALIZATION
    # ============================================================

    def normalize_question(
        self,
        question: Any,
        index: int,
        qmap: Dict[str, Any],
    ) -> Dict[str, Any]:

        if not isinstance(
            question,
            dict,
        ):

            raise TestParserError(
                "Question object नहीं है।"
            )

        # --------------------------------------------------------
        # Question number
        # --------------------------------------------------------

        number = (
            question.get("n")
            or question.get("qid")
            or question.get("id")
            or index
        )

        # --------------------------------------------------------
        # Question text
        # --------------------------------------------------------

        text = (
            question.get("text")
            or question.get("question")
            or question.get("q")
            or ""
        )

        # --------------------------------------------------------
        # Options
        # --------------------------------------------------------

        options = (
            question.get("opts")
            or question.get("options")
            or question.get("choices")
            or []
        )

        if isinstance(
            options,
            dict,
        ):

            options = list(
                options.values()
            )

        if not isinstance(
            options,
            list,
        ):

            options = [
                options
            ]

        # --------------------------------------------------------
        # Correct answer
        # --------------------------------------------------------

        correct = (
            question.get("cidx")
        )

        if correct is None:

            correct = (
                question.get("correct")
            )

        if correct is None:

            correct = (
                question.get("answer")
            )

        # Q_MAP fallback
        map_item = qmap.get(
            str(number),
            {}
        )

        if isinstance(
            map_item,
            dict,
        ):

            if correct is None:

                correct = (
                    map_item.get(
                        "correct"
                    )
                )

            if correct is None:

                correct = (
                    map_item.get(
                        "cidx"
                    )
                )

        # --------------------------------------------------------
        # Solution
        # --------------------------------------------------------

        solution = (
            question.get("sol")
            or question.get("solution")
            or question.get("exp")
            or question.get("explanation")
            or ""
        )

        # --------------------------------------------------------
        # Images
        # --------------------------------------------------------

        image_link = (
            question.get(
                "image_link"
            )
            or question.get(
                "image"
            )
            or question.get(
                "imageUrl"
            )
            or ""
        )

        solution_image = (
            question.get(
                "exp_image_link"
            )
            or question.get(
                "solution_image"
            )
            or question.get(
                "solutionImage"
            )
            or ""
        )

        # --------------------------------------------------------
        # Section
        # --------------------------------------------------------

        section_index = (
            question.get("si")
            or question.get("section")
            or 0
        )

        # --------------------------------------------------------
        # Marks
        # --------------------------------------------------------

        positive = self.to_number(
            question.get(
                "pos",
                question.get(
                    "marks",
                    0
                ),
            )
        )

        negative = self.to_number(
            question.get(
                "neg",
                0
            )
        )

        # Q_MAP fallback
        if isinstance(
            map_item,
            dict,
        ):

            if positive == 0:

                positive = self.to_number(
                    map_item.get(
                        "pos",
                        0
                    )
                )

            if negative == 0:

                negative = self.to_number(
                    map_item.get(
                        "neg",
                        0
                    )
                )

        # --------------------------------------------------------
        # Final common format
        # --------------------------------------------------------

        return {
            "n": number,

            "text": str(
                text or ""
            ),

            "options": [
                str(x)
                for x in options
            ],

            "correct": (
                self.to_int_or_none(
                    correct
                )
            ),

            "solution": str(
                solution or ""
            ),

            "image_link": str(
                image_link or ""
            ),

            "solution_image": str(
                solution_image or ""
            ),

            "section": section_index,

            "marks": positive,

            "negative": negative,
        }

    # ============================================================
    # METADATA EXTRACTION
    # ============================================================

    def extract_metadata(
        self,
        text: str,
        soup: BeautifulSoup,
        title: str,
        question_count: int,
    ) -> Dict[str, Any]:

        full_text = soup.get_text(
            " ",
            strip=True,
        )

        combined = (
            title
            + " "
            + full_text
        )

        # --------------------------------------------------------
        # Time
        # --------------------------------------------------------

        time_minutes = (
            self.find_number_by_patterns(
                combined,
                [
                    r"(\d+)\s*(?:minutes?|mins?|मिनट)",
                    r"time\s*[:\-]?\s*(\d+)",
                    r"समय\s*[:\-]?\s*(\d+)",
                ],
            )
        )

        # --------------------------------------------------------
        # Positive marks
        # --------------------------------------------------------

        positive_marks = (
            self.find_number_by_patterns(
                combined,
                [
                    r"positive\s*[:\-]?\s*([0-9.]+)",
                    r"correct\s*[:\-]?\s*([0-9.]+)",
                    r"प्रश्न.*?अंक\s*[:\-]?\s*([0-9.]+)",
                ],
            )
        )

        # --------------------------------------------------------
        # Negative marks
        # --------------------------------------------------------

        negative_marks = (
            self.find_number_by_patterns(
                combined,
                [
                    r"negative\s*[:\-]?\s*([0-9.]+)",
                    r"negative\s*marking\s*[:\-]?\s*([0-9.]+)",
                    r"ऋणात्मक.*?([0-9.]+)",
                ],
            )
        )

        # --------------------------------------------------------
        # Total marks
        # --------------------------------------------------------

        total_marks = (
            self.find_number_by_patterns(
                combined,
                [
                    r"total\s*marks?\s*[:\-]?\s*([0-9.]+)",
                    r"कुल\s*अंक\s*[:\-]?\s*([0-9.]+)",
                ],
            )
        )

        # --------------------------------------------------------
        # Language
        # --------------------------------------------------------

        language = "Hindi"

        lower = combined.lower()

        if "english" in lower:

            language = "English"

        if (
            "hindi" in lower
            and "english" in lower
        ):

            language = "Hindi + English"

        # --------------------------------------------------------
        # Exam detection
        # --------------------------------------------------------

        exam = self.detect_exam(
            combined
        )

        # --------------------------------------------------------
        # Test type
        # --------------------------------------------------------

        test_type = self.detect_test_type(
            combined
        )

        # --------------------------------------------------------
        # Year
        # --------------------------------------------------------

        years = re.findall(
            r"\b20\d{2}\b",
            combined,
        )

        year = (
            years[-1]
            if years
            else "Other"
        )

        # --------------------------------------------------------
        # Shift
        # --------------------------------------------------------

        shift = self.find_shift(
            combined
        )

        return {
            "time_minutes": (
                self.to_number(
                    time_minutes
                )
                if time_minutes is not None
                else 0
            ),

            "positive_marks": (
                self.to_number(
                    positive_marks
                )
                if positive_marks is not None
                else 0
            ),

            "negative_marks": (
                self.to_number(
                    negative_marks
                )
                if negative_marks is not None
                else 0
            ),

            "total_marks": (
                self.to_number(
                    total_marks
                )
                if total_marks is not None
                else 0
            ),

            "question_count": question_count,

            "language": language,

            "exam": exam,

            "test_type": test_type,

            "year": year,

            "shift": shift,
        }

    # ============================================================
    # TITLE
    # ============================================================

    def _extract_title(
        self,
        soup: BeautifulSoup,
        text: str,
        filename: str,
    ) -> str:

        title_tag = soup.find(
            "title"
        )

        if title_tag:

            value = title_tag.get_text(
                " ",
                strip=True,
            )

            if value:

                return value

        # H1 fallback

        h1 = soup.find(
            "h1"
        )

        if h1:

            value = h1.get_text(
                " ",
                strip=True,
            )

            if value:

                return value

        # Filename fallback

        if filename:

            return re.sub(
                r"\.(html?|HTML?)$",
                "",
                filename,
            )

        return "Untitled Test"

    # ============================================================
    # EXAM DETECTION
    # ============================================================

    def detect_exam(
        self,
        text: str,
    ) -> str:

        exams = [
            (
                "SSC GD",
                [
                    "ssc gd",
                    "ssc-gd",
                    "ssc constable gd",
                ],
            ),

            (
                "SSC CGL",
                [
                    "ssc cgl",
                ],
            ),

            (
                "SSC CHSL",
                [
                    "ssc chsl",
                ],
            ),

            (
                "SSC MTS",
                [
                    "ssc mts",
                ],
            ),

            (
                "SSC CPO",
                [
                    "ssc cpo",
                ],
            ),

            (
                "RRB NTPC",
                [
                    "rrb ntpc",
                    "ntpc",
                ],
            ),

            (
                "RRB Group D",
                [
                    "rrb group d",
                    "group d",
                ],
            ),

            (
                "RRB ALP",
                [
                    "rrb alp",
            ],
            ),

            (
                "RRB Technician",
                [
                    "rrb technician",
                    "technician",
                ],
            ),

            (
                "UPSC",
                [
                    "upsc",
                ],
            ),

            (
                "Rajasthan CET",
                [
                    "rajasthan cet",
                    "cet graduate",
                    "cet 12th",
                ],
            ),

            (
                "Delhi Police",
                [
                    "delhi police",
                ],
            ),

            (
                "UP Police",
                [
                    "up police",
                ],
            ),

            (
                "Banking",
                [
                    "ibps",
                    "sbi clerk",
                    "sbi po",
                    "banking",
                ],
            ),
        ]

        lower = text.lower()

        for name, patterns in exams:

            for pattern in patterns:

                if pattern in lower:

                    return name

        return "Other"

    # ============================================================
    # TEST TYPE
    # ============================================================

    def detect_test_type(
        self,
        text: str,
    ) -> str:

        lower = text.lower()

        if (
            "previous year"
            in lower
            or "previous paper"
            in lower
            or "pyq"
            in lower
            or "पिछले वर्ष"
            in text
            or "पूर्व वर्ष"
            in text
        ):

            return "PYQ"

        if (
            "mock"
            in lower
            or "मॉक"
            in text
        ):

            return "Mock Test"

        return "Other"

    # ============================================================
    # SHIFT
    # ============================================================

    def find_shift(
        self,
        text: str,
    ) -> str:

        patterns = [
            r"shift\s*[-:]?\s*(\d+)",
            r"shift\s*(\d+)",
            r"शिफ्ट\s*[-:]?\s*(\d+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                flags=re.I,
            )

            if match:

                return (
                    f"Shift {match.group(1)}"
                )

        return ""

    # ============================================================
    # NUMBER HELPERS
    # ============================================================

    @staticmethod
    def to_number(
        value: Any,
    ) -> float:

        if value is None:

            return 0.0

        if isinstance(
            value,
            (int, float),
        ):

            return float(
                value
            )

        match = re.search(
            r"-?\d+(?:\.\d+)?",
            str(value),
        )

        if not match:

            return 0.0

        try:

            return float(
                match.group(0)
            )

        except Exception:

            return 0.0

    @staticmethod
    def to_int_or_none(
        value: Any,
    ) -> Optional[int]:

        if value is None:

            return None

        try:

            return int(
                float(value)
            )

        except Exception:

            return None

    # ============================================================
    # PATTERN NUMBER
    # ============================================================

    def find_number_by_patterns(
        self,
        text: str,
        patterns: List[str],
    ) -> Optional[float]:

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                flags=re.I,
            )

            if match:

                try:

                    return float(
                        match.group(1)
                    )

                except Exception:

                    continue

        return None


# ================================================================
# SINGLE PARSER INSTANCE
# ================================================================

parser = UniversalTestParser()

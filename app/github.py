import base64
import logging
import re
from typing import Optional, Tuple

import requests

from .config import CONFIG


logger = logging.getLogger(__name__)


class GitHubError(Exception):
    """GitHub operation failed."""


class GitHubManager:
    """
    GitHub repository manager.

    Repository structure:

    templates/
        tcs.html
            ↓
            Master TCS UI

    published/
        TEST_ID/
            tcs.html
                ↓
                Individual published test

    IMPORTANT:
    GitHub में generated tcs.html के अंदर पूरा Test JSON embedded रहेगा।
    MongoDB में पूरा JSON save नहीं होगा।
    """

    API_BASE = "https://api.github.com"

    def __init__(self):

        self.token = CONFIG.github_token
        self.owner = CONFIG.github_owner
        self.repo = CONFIG.github_repo
        self.branch = CONFIG.github_branch

        self.template_path = (
            CONFIG.github_template_path
        )

        self.tests_directory = (
            CONFIG.github_tests_directory
        )

        self.session = requests.Session()

        self.session.headers.update(
            {
                "Authorization":
                    f"Bearer {self.token}",

                "Accept":
                    "application/vnd.github+json",

                "X-GitHub-Api-Version":
                    "2022-11-28",

                "User-Agent":
                    "Telegram-Test-Index-Bot",
            }
        )

    # ============================================================
    # BASIC HELPERS
    # ============================================================

    def _contents_url(
        self,
        path: str = "",
    ) -> str:

        path = path.strip("/")

        return (
            f"{self.API_BASE}/repos/"
            f"{self.owner}/{self.repo}/contents/"
            f"{path}"
        )

    def _raw_url(
        self,
        path: str,
    ) -> str:

        path = path.strip("/")

        return (
            f"https://raw.githubusercontent.com/"
            f"{self.owner}/{self.repo}/"
            f"{self.branch}/{path}"
        )

    def _pages_url(
        self,
        path: str,
    ) -> str:

        path = path.strip("/")

        return (
            f"https://{self.owner}.github.io/"
            f"{self.repo}/{path}"
        )

    # ============================================================
    # CONNECTION TEST
    # ============================================================

    def test_connection(self) -> bool:

        try:

            url = (
                f"{self.API_BASE}/repos/"
                f"{self.owner}/{self.repo}"
            )

            response = self.session.get(
                url,
                timeout=20,
            )

            return response.ok

        except Exception:

            logger.exception(
                "GitHub connection test failed"
            )

            return False

    # ============================================================
    # GET FILE
    # ============================================================

    def get_file(
        self,
        path: str,
    ) -> Tuple[Optional[bytes], Optional[str]]:

        url = self._contents_url(path)

        response = self.session.get(
            url,
            params={
                "ref": self.branch
            },
            timeout=30,
        )

        if response.status_code == 404:

            return None, None

        if not response.ok:

            raise GitHubError(
                f"GitHub GET failed "
                f"{response.status_code}: "
                f"{response.text[:500]}"
            )

        data = response.json()

        encoded = data.get(
            "content",
            "",
        ).replace("\n", "")

        try:

            content = base64.b64decode(
                encoded
            )

        except Exception as exc:

            raise GitHubError(
                "Unable to decode GitHub file."
            ) from exc

        return (
            content,
            data.get("sha"),
        )

    # ============================================================
    # GET MASTER TCS TEMPLATE
    # ============================================================

    def get_tcs_template(self) -> bytes:

        content, sha = self.get_file(
            self.template_path
        )

        if content is None:

            raise GitHubError(
                "Master TCS template not found: "
                f"{self.template_path}"
            )

        return content

    # ============================================================
    # CREATE / UPDATE FILE
    # ============================================================

    def upload_file(
        self,
        path: str,
        content: bytes,
        commit_message: str,
    ) -> dict:

        path = path.strip("/")

        url = self._contents_url(path)

        # --------------------------------------------------------
        # Check existing file
        # --------------------------------------------------------

        response = self.session.get(
            url,
            params={
                "ref": self.branch
            },
            timeout=30,
        )

        sha = None

        if response.status_code == 200:

            existing = response.json()

            sha = existing.get(
                "sha"
            )

        elif response.status_code != 404:

            raise GitHubError(
                f"Unable to check GitHub file: "
                f"{response.status_code} "
                f"{response.text[:500]}"
            )

        # --------------------------------------------------------
        # Upload
        # --------------------------------------------------------

        payload = {
            "message": commit_message,

            "content": base64.b64encode(
                content
            ).decode("ascii"),

            "branch": self.branch,
        }

        # Existing file को update करने के लिए SHA जरूरी है।
        if sha:
            payload["sha"] = sha

        response = self.session.put(
            url,
            json=payload,
            timeout=60,
        )

        if not response.ok:

            raise GitHubError(
                f"GitHub upload failed: "
                f"{response.status_code} "
                f"{response.text[:1000]}"
            )

        return response.json()

    # ============================================================
    # UPLOAD GENERATED TCS TEST
    # ============================================================

    def upload_test(
        self,
        test_id: str,
        html_content: bytes,
        title: str = "",
    ) -> dict:

        safe_id = self.safe_path_component(
            test_id
        )

        path = (
            f"{self.tests_directory}/"
            f"{safe_id}/tcs.html"
        )

        result = self.upload_file(
            path=path,
            content=html_content,
            commit_message=(
                f"Add test: "
                f"{title or test_id}"
            ),
        )

        return {
            "path": path,

            # Raw GitHub URL
            "raw_url": self._raw_url(
                path
            ),

            # GitHub Pages URL
            "pages_url": self._pages_url(
                path
            ),

            "html_url": (
                result
                .get("content", {})
                .get("html_url", "")
            ),

            "commit_url": (
                result
                .get("commit", {})
                .get("html_url", "")
            ),

            "sha": (
                result
                .get("content", {})
                .get("sha")
            ),
        }

    # ============================================================
    # DOWNLOAD TEST
    # ============================================================

    def download_test(
        self,
        path: str,
    ) -> bytes:

        content, _ = self.get_file(
            path
        )

        if content is None:

            raise GitHubError(
                f"Test file not found: {path}"
            )

        return content

    # ============================================================
    # DELETE FILE
    # ============================================================

    def delete_file(
        self,
        path: str,
        commit_message: str,
    ) -> bool:

        url = self._contents_url(
            path
        )

        response = self.session.get(
            url,
            params={
                "ref": self.branch
            },
            timeout=30,
        )

        if response.status_code == 404:

            return True

        if not response.ok:

            raise GitHubError(
                f"Unable to locate file: "
                f"{response.text[:500]}"
            )

        data = response.json()

        sha = data.get(
            "sha"
        )

        if not sha:

            raise GitHubError(
                "GitHub file SHA missing."
            )

        response = self.session.delete(
            url,
            json={
                "message": commit_message,
                "sha": sha,
                "branch": self.branch,
            },
            timeout=30,
        )

        if not response.ok:

            raise GitHubError(
                f"GitHub delete failed: "
                f"{response.status_code} "
                f"{response.text[:500]}"
            )

        return True

    # ============================================================
    # CREATE DIRECTORY PLACEHOLDER
    # ============================================================

    def ensure_directory(
        self,
        directory: str,
    ):

        """
        GitHub में empty directory technically नहीं रहती।

        इसलिए जरूरत होने पर .gitkeep बनाया जाता है।
        """

        directory = directory.strip(
            "/"
        )

        if not directory:

            return

        path = (
            f"{directory}/.gitkeep"
        )

        content, _ = self.get_file(
            path
        )

        if content is not None:

            return

        self.upload_file(
            path=path,
            content=b"",
            commit_message=(
                f"Initialize directory "
                f"{directory}"
            ),
        )

    # ============================================================
    # LIST DIRECTORY
    # ============================================================

    def list_directory(
        self,
        directory: str = "",
    ) -> list:

        url = self._contents_url(
            directory
        )

        response = self.session.get(
            url,
            params={
                "ref": self.branch
            },
            timeout=30,
        )

        if response.status_code == 404:

            return []

        if not response.ok:

            raise GitHubError(
                f"GitHub directory listing failed: "
                f"{response.status_code}"
            )

        data = response.json()

        if not isinstance(
            data,
            list
        ):

            return []

        return data

    # ============================================================
    # TEST PATH
    # ============================================================

    def test_path(
        self,
        test_id: str,
    ) -> str:

        safe_id = self.safe_path_component(
            test_id
        )

        return (
            f"{self.tests_directory}/"
            f"{safe_id}/tcs.html"
        )

    # ============================================================
    # TEST URL
    # ============================================================

    def test_url(
        self,
        test_id: str,
    ) -> str:

        path = self.test_path(
            test_id
        )

        return self._pages_url(
            path
        )

    # ============================================================
    # SAFE PATH
    # ============================================================

    @staticmethod
    def safe_path_component(
        value: str,
    ) -> str:

        value = str(
            value or ""
        ).strip()

        value = re.sub(
            r"[^a-zA-Z0-9._-]+",
            "-",
            value,
        )

        value = re.sub(
            r"-+",
            "-",
            value,
        )

        value = value.strip(
            "-."
        )

        return (
            value[:100]
            or "test"
        )

    # ============================================================
    # VERIFY TEMPLATE
    # ============================================================

    def verify_tcs_template(
        self,
        html: bytes,
    ) -> dict:

        text = html.decode(
            "utf-8",
            errors="ignore",
        )

        result = {
            "valid": True,
            "has_hardjson": False,
            "has_template": False,
            "size": len(html),
            "errors": [],
        }

        # --------------------------------------------------------
        # hardjson
        # --------------------------------------------------------

        if re.search(
            r"\bconst\s+hardjson\s*=",
            text,
        ):

            result["has_hardjson"] = True

        # --------------------------------------------------------
        # TCS template
        # --------------------------------------------------------

        if (
            "TCS" in text
            or "CBT" in text
            or "Mock Test" in text
        ):

            result["has_template"] = True

        if not result["has_hardjson"]:

            result["errors"].append(
                "const hardjson marker not found"
            )

        if not result["has_template"]:

            result["errors"].append(
                "TCS/CBT template marker not found"
            )

        result["valid"] = not bool(
            result["errors"]
        )

        return result


# ================================================================
# SINGLE GITHUB INSTANCE
# ================================================================

github = GitHubManager()

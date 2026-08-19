from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ================================================================
# USER
# ================================================================

@dataclass
class UserModel:
    user_id: int

    name: str = ""
    username: str = ""
    language: str = ""

    created_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    banned: bool = False
    ban_reason: Optional[str] = None

    # -----------------------------
    # Premium
    # -----------------------------

    paid: bool = False
    paid_plan: Optional[str] = None
    paid_at: Optional[datetime] = None
    paid_expiry: Optional[datetime] = None

    # -----------------------------
    # Free Trial
    # -----------------------------

    trial_used: bool = False
    trial_locked: bool = False

    trial_started_at: Optional[datetime] = None
    trial_expiry: Optional[datetime] = None

    trial_extract_limit: int = 0
    trial_extract_used: int = 0

    # -----------------------------
    # Statistics
    # -----------------------------

    extract_count: int = 0
    successful_extracts: int = 0
    failed_extracts: int = 0

    last_extract_at: Optional[datetime] = None
    last_payment_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserModel":
        return cls(
            user_id=int(data["user_id"]),

            name=data.get("name", ""),
            username=data.get("username", ""),
            language=data.get("language", ""),

            created_at=data.get("created_at"),
            last_seen=data.get("last_seen"),

            banned=bool(data.get("banned", False)),
            ban_reason=data.get("ban_reason"),

            paid=bool(data.get("paid", False)),
            paid_plan=data.get("paid_plan"),
            paid_at=data.get("paid_at"),
            paid_expiry=data.get("paid_expiry"),

            trial_used=bool(data.get("trial_used", False)),
            trial_locked=bool(
                data.get("trial_locked", False)
            ),

            trial_started_at=data.get(
                "trial_started_at"
            ),
            trial_expiry=data.get(
                "trial_expiry"
            ),

            trial_extract_limit=int(
                data.get("trial_extract_limit", 0)
            ),
            trial_extract_used=int(
                data.get("trial_extract_used", 0)
            ),

            extract_count=int(
                data.get("extract_count", 0)
            ),
            successful_extracts=int(
                data.get("successful_extracts", 0)
            ),
            failed_extracts=int(
                data.get("failed_extracts", 0)
            ),

            last_extract_at=data.get(
                "last_extract_at"
            ),
            last_payment_at=data.get(
                "last_payment_at"
            ),
        )


# ================================================================
# TEST METADATA
# ================================================================

@dataclass
class TestModel:
    """
    IMPORTANT:

    इस model में questions JSON नहीं रखा जाता।

    Test का actual HTML + embedded JSON:
        GitHub / Database Channel

    MongoDB:
        केवल metadata + URLs + statistics
    """

    test_id: str

    title: str

    category: str = "Other"
    exam: str = "Other"

    series: str = ""
    section: str = ""
    subsection: str = ""

    test_type: str = "Mock Test"

    year: str = "Other"

    language: str = "Hindi"

    question_count: int = 0

    # -----------------------------
    # GitHub
    # -----------------------------

    github_path: str = ""
    github_url: str = ""

    # -----------------------------
    # Database Channel
    # -----------------------------

    database_channel_id: Optional[int] = None
    database_message_id: Optional[int] = None

    # -----------------------------
    # Statistics
    # -----------------------------

    extract_count: int = 0
    successful_extracts: int = 0
    failed_extracts: int = 0

    last_extract_at: Optional[datetime] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestModel":

        return cls(
            test_id=str(data["test_id"]),

            title=data.get(
                "title",
                "Untitled Test"
            ),

            category=data.get(
                "category",
                "Other"
            ),

            exam=data.get(
                "exam",
                "Other"
            ),

            series=data.get(
                "series",
                ""
            ),

            section=data.get(
                "section",
                ""
            ),

            subsection=data.get(
                "subsection",
                ""
            ),

            test_type=data.get(
                "type",
                data.get(
                    "test_type",
                    "Mock Test"
                )
            ),

            year=str(
                data.get(
                    "year",
                    "Other"
                )
            ),

            language=data.get(
                "language",
                "Hindi"
            ),

            question_count=int(
                data.get(
                    "question_count",
                    0
                ) or 0
            ),

            github_path=data.get(
                "github_path",
                ""
            ),

            github_url=data.get(
                "github_url",
                ""
            ),

            database_channel_id=data.get(
                "database_channel_id"
            ),

            database_message_id=data.get(
                "database_message_id"
            ),

            extract_count=int(
                data.get(
                    "extract_count",
                    0
                )
            ),

            successful_extracts=int(
                data.get(
                    "successful_extracts",
                    0
                )
            ),

            failed_extracts=int(
                data.get(
                    "failed_extracts",
                    0
                )
            ),

            last_extract_at=data.get(
                "last_extract_at"
            ),

            created_at=data.get(
                "created_at"
            ),

            updated_at=data.get(
                "updated_at"
            ),
        )


# ================================================================
# QUEUE JOB
# ================================================================

@dataclass
class JobModel:

    job_id: str

    user_id: int

    job_type: str

    priority: int = 0

    status: str = "queued"

    payload: Dict[str, Any] = field(
        default_factory=dict
    )

    retry_count: int = 0

    error: Optional[str] = None

    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_paid_priority(self) -> bool:
        return self.priority > 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobModel":

        return cls(
            job_id=str(data["job_id"]),

            user_id=int(
                data["user_id"]
            ),

            job_type=data.get(
                "job_type",
                ""
            ),

            priority=int(
                data.get(
                    "priority",
                    0
                )
            ),

            status=data.get(
                "status",
                "queued"
            ),

            payload=data.get(
                "payload",
                {}
            ),

            retry_count=int(
                data.get(
                    "retry_count",
                    0
                )
            ),

            error=data.get(
                "error"
            ),

            created_at=data.get(
                "created_at"
            ),

            started_at=data.get(
                "started_at"
            ),

            finished_at=data.get(
                "finished_at"
            ),

            updated_at=data.get(
                "updated_at"
            ),
        )


# ================================================================
# PAYMENT
# ================================================================

@dataclass
class PaymentModel:

    payment_id: str

    user_id: int

    amount: float

    plan: str

    status: str = "pending"

    screenshot_message_id: Optional[int] = None

    created_at: Optional[datetime] = None

    reviewed_at: Optional[datetime] = None

    reviewed_by: Optional[int] = None

    reject_reason: Optional[str] = None

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any]
    ) -> "PaymentModel":

        return cls(
            payment_id=str(
                data["payment_id"]
            ),

            user_id=int(
                data["user_id"]
            ),

            amount=float(
                data.get(
                    "amount",
                    0
                )
            ),

            plan=data.get(
                "plan",
                ""
            ),

            status=data.get(
                "status",
                "pending"
            ),

            screenshot_message_id=data.get(
                "screenshot_message_id"
            ),

            created_at=data.get(
                "created_at"
            ),

            reviewed_at=data.get(
                "reviewed_at"
            ),

            reviewed_by=data.get(
                "reviewed_by"
            ),

            reject_reason=data.get(
                "reject_reason"
            ),
        )


# ================================================================
# CHANNEL CONFIGURATION
# ================================================================

@dataclass
class ChannelModel:

    channel_type: str

    channel_id: Any

    title: str = ""

    username: str = ""

    added_by: Optional[int] = None

    added_at: Optional[datetime] = None

    enabled: bool = True

    @classmethod
    def from_dict(
        cls,
        channel_type: str,
        data: Dict[str, Any]
    ) -> "ChannelModel":

        return cls(
            channel_type=channel_type,

            channel_id=data.get(
                "channel_id"
            ),

            title=data.get(
                "title",
                ""
            ),

            username=data.get(
                "username",
                ""
            ),

            added_by=data.get(
                "added_by"
            ),

            added_at=data.get(
                "added_at"
            ),

            enabled=bool(
                data.get(
                    "enabled",
                    True
                )
            ),
        )


# ================================================================
# FORCE JOIN CHANNEL
# ================================================================

@dataclass
class ForceJoinChannelModel:

    channel_id: Any

    title: str = ""

    username: str = ""

    invite_link: str = ""

    enabled: bool = True

    added_by: Optional[int] = None

    added_at: Optional[datetime] = None

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any]
    ) -> "ForceJoinChannelModel":

        return cls(
            channel_id=data.get(
                "channel_id"
            ),

            title=data.get(
                "title",
                ""
            ),

            username=data.get(
                "username",
                ""
            ),

            invite_link=data.get(
                "invite_link",
                ""
            ),

            enabled=bool(
                data.get(
                    "enabled",
                    True
                )
            ),

            added_by=data.get(
                "added_by"
            ),

            added_at=data.get(
                "added_at"
            ),
        )


# ================================================================
# EXTRACT RECORD
# ================================================================

@dataclass
class ExtractModel:

    user_id: int

    test_id: str

    status: str

    job_id: Optional[str] = None

    created_at: Optional[datetime] = None

    finished_at: Optional[datetime] = None

    error: Optional[str] = None

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any]
    ) -> "ExtractModel":

        return cls(
            user_id=int(
                data["user_id"]
            ),

            test_id=str(
                data["test_id"]
            ),

            status=data.get(
                "status",
                "queued"
            ),

            job_id=data.get(
                "job_id"
            ),

            created_at=data.get(
                "created_at"
            ),

            finished_at=data.get(
                "finished_at"
            ),

            error=data.get(
                "error"
            ),
        )


# ================================================================
# BACKUP RECORD
# ================================================================

@dataclass
class BackupModel:

    test_id: str

    channel_id: Any

    message_id: int

    github_path: str

    github_url: str

    created_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any]
    ) -> "BackupModel":

        return cls(
            test_id=str(
                data["test_id"]
            ),

            channel_id=data.get(
                "channel_id"
            ),

            message_id=int(
                data["message_id"]
            ),

            github_path=data.get(
                "github_path",
                ""
            ),

            github_url=data.get(
                "github_url",
                ""
            ),

            created_at=data.get(
                "created_at"
            ),

            updated_at=data.get(
                "updated_at"
            ),
        )


# ================================================================
# BOT SETTINGS
# ================================================================

@dataclass
class BotSettingsModel:

    # -----------------------------
    # Welcome
    # -----------------------------

    welcome_enabled: bool = True

    welcome_message: str = (
        "👋 Welcome!\n\n"
        "📚 Test Extract करने के लिए "
        "नीचे button दबाएँ।"
    )

    welcome_button_text: str = ""

    welcome_button_url: str = ""

    # -----------------------------
    # Free Trial
    # -----------------------------

    trial_enabled: bool = True

    trial_days: int = 1

    trial_extract_limit: int = 1

    trial_allowed: bool = True

    # -----------------------------
    # Premium
    # -----------------------------

    premium_enabled: bool = True

    # Example:
    #
    # {
    #     "7_days": 49,
    #     "30_days": 149,
    #     "90_days": 299,
    #     "365_days": 799
    # }

    prices: Dict[str, float] = field(
        default_factory=dict
    )

    # -----------------------------
    # Queue
    # -----------------------------

    queue_enabled: bool = True

    paid_priority_enabled: bool = True

    # -----------------------------
    # Maintenance
    # -----------------------------

    maintenance_mode: bool = False

    maintenance_message: str = (
        "🛠️ Bot अभी maintenance में है।\n"
        "कृपया थोड़ी देर बाद कोशिश करें।"
    )

    # -----------------------------
    # Upload
    # -----------------------------

    upload_enabled: bool = True

    bulk_upload_enabled: bool = True

    # -----------------------------
    # Extract
    # -----------------------------

    extract_enabled: bool = True

    # -----------------------------
    # Forced Join
    # -----------------------------

    force_join_enabled: bool = False

    # -----------------------------
    # Broadcast
    # -----------------------------

    broadcast_enabled: bool = True

    # -----------------------------
    # Backup
    # -----------------------------

    backup_enabled: bool = True

    # -----------------------------
    # Reports
    # -----------------------------

    reports_enabled: bool = True

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any]
    ) -> "BotSettingsModel":

        return cls(
            welcome_enabled=bool(
                data.get(
                    "welcome_enabled",
                    True
                )
            ),

            welcome_message=data.get(
                "welcome_message",
                cls.welcome_message
            ),

            welcome_button_text=data.get(
                "welcome_button_text",
                ""
            ),

            welcome_button_url=data.get(
                "welcome_button_url",
                ""
            ),

            trial_enabled=bool(
                data.get(
                    "trial_enabled",
                    True
                )
            ),

            trial_days=int(
                data.get(
                    "trial_days",
                    1
                )
            ),

            trial_extract_limit=int(
                data.get(
                    "trial_extract_limit",
                    1
                )
            ),

            trial_allowed=bool(
                data.get(
                    "trial_allowed",
                    True
                )
            ),

            premium_enabled=bool(
                data.get(
                    "premium_enabled",
                    True
                )
            ),

            prices=data.get(
                "prices",
                {}
            ),

            queue_enabled=bool(
                data.get(
                    "queue_enabled",
                    True
                )
            ),

            paid_priority_enabled=bool(
                data.get(
                    "paid_priority_enabled",
                    True
                )
            ),

            maintenance_mode=bool(
                data.get(
                    "maintenance_mode",
                    False
                )
            ),

            maintenance_message=data.get(
                "maintenance_message",
                cls.maintenance_message
            ),

            upload_enabled=bool(
                data.get(
                    "upload_enabled",
                    True
                )
            ),

            bulk_upload_enabled=bool(
                data.get(
                    "bulk_upload_enabled",
                    True
                )
            ),

            extract_enabled=bool(
                data.get(
                    "extract_enabled",
                    True
                )
            ),

            force_join_enabled=bool(
                data.get(
                    "force_join_enabled",
                    False
                )
            ),

            broadcast_enabled=bool(
                data.get(
                    "broadcast_enabled",
                    True
                )
            ),

            backup_enabled=bool(
                data.get(
                    "backup_enabled",
                    True
                )
            ),

            reports_enabled=bool(
                data.get(
                    "reports_enabled",
                    True
                )
            ),
        )

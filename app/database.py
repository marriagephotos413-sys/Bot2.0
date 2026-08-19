import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from .config import CONFIG


logger = logging.getLogger(__name__)


class MongoDatabase:
    """
    MongoDB manager.

    IMPORTANT:
    MongoDB में Test का पूरा questions JSON save नहीं किया जाएगा।

    MongoDB में केवल:
    - Test metadata
    - GitHub URL/path
    - Database Channel message ID
    - User data
    - Payment data
    - Queue/job data
    - Settings
    - Reports/statistics
    save होंगे।

    Actual TCS HTML + embedded JSON:
        GitHub
            +
        Database Channel backup
    """

    def __init__(self):
        self.client: MongoClient = MongoClient(
            CONFIG.mongo_url,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
            socketTimeoutMS=20000,
            retryWrites=True,
        )

        self.db: Database = self.client[CONFIG.mongo_database]

        # ========================================================
        # COLLECTIONS
        # ========================================================

        self.users: Collection = self.db["users"]

        self.tests: Collection = self.db["tests"]

        self.jobs: Collection = self.db["jobs"]

        self.payments: Collection = self.db["payments"]

        self.settings: Collection = self.db["settings"]

        self.extracts: Collection = self.db["extracts"]

        self.events: Collection = self.db["events"]

        self.broadcasts: Collection = self.db["broadcasts"]

        self.backups: Collection = self.db["backups"]

        # ========================================================
        # INDEXES
        # ========================================================

        self._create_indexes()

    # ============================================================
    # GENERAL
    # ============================================================

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    def ping(self) -> bool:
        """
        MongoDB connection check.
        """
        try:
            self.client.admin.command("ping")
            return True

        except Exception:
            logger.exception("MongoDB ping failed")
            return False

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass

    # ============================================================
    # INDEXES
    # ============================================================

    def _create_indexes(self):

        # -------------------------
        # Users
        # -------------------------

        self.users.create_index(
            [("user_id", ASCENDING)],
            unique=True,
            name="unique_user_id",
        )

        self.users.create_index(
            [("paid", ASCENDING)],
            name="paid_users",
        )

        self.users.create_index(
            [("banned", ASCENDING)],
            name="banned_users",
        )

        self.users.create_index(
            [("created_at", DESCENDING)],
            name="users_created_at",
        )

        self.users.create_index(
            [("last_seen", DESCENDING)],
            name="users_last_seen",
        )

        # -------------------------
        # Tests
        # -------------------------

        self.tests.create_index(
            [("test_id", ASCENDING)],
            unique=True,
            name="unique_test_id",
        )

        self.tests.create_index(
            [
                ("category", ASCENDING),
                ("exam", ASCENDING),
                ("type", ASCENDING),
                ("year", DESCENDING),
            ],
            name="test_index_tree",
        )

        self.tests.create_index(
            [("created_at", DESCENDING)],
            name="tests_created_at",
        )

        self.tests.create_index(
            [("extract_count", DESCENDING)],
            name="tests_extract_count",
        )

        # -------------------------
        # Jobs
        # -------------------------

        self.jobs.create_index(
            [
                ("status", ASCENDING),
                ("priority", DESCENDING),
                ("created_at", ASCENDING),
            ],
            name="queue_priority",
        )

        self.jobs.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)],
            name="user_jobs",
        )

        # -------------------------
        # Payments
        # -------------------------

        self.payments.create_index(
            [("payment_id", ASCENDING)],
            unique=True,
            name="unique_payment_id",
        )

        self.payments.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)],
            name="user_payments",
        )

        self.payments.create_index(
            [("status", ASCENDING), ("created_at", ASCENDING)],
            name="pending_payments",
        )

        # -------------------------
        # Extract history
        # -------------------------

        self.extracts.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)],
            name="user_extract_history",
        )

        self.extracts.create_index(
            [("test_id", ASCENDING), ("created_at", DESCENDING)],
            name="test_extract_history",
        )

        # -------------------------
        # Events
        # -------------------------

        self.events.create_index(
            [("event_type", ASCENDING), ("created_at", DESCENDING)],
            name="event_type_time",
        )

        # -------------------------
        # Settings
        # -------------------------

        self.settings.create_index(
            [("key", ASCENDING)],
            unique=True,
            name="unique_setting_key",
        )

        # -------------------------
        # Backup
        # -------------------------

        self.backups.create_index(
            [("test_id", ASCENDING)],
            unique=True,
            name="unique_test_backup",
        )

        # -------------------------
        # Broadcast
        # -------------------------

        self.broadcasts.create_index(
            [("broadcast_id", ASCENDING)],
            unique=True,
            name="unique_broadcast_id",
        )

    # ============================================================
    # USERS
    # ============================================================

    def create_or_update_user(
        self,
        user_id: int,
        name: str = "",
        username: str = "",
        language: str = "",
        is_bot: bool = False,
    ) -> Dict[str, Any]:

        current = self.users.find_one(
            {"user_id": user_id}
        )

        update = {
            "$set": {
                "name": name,
                "username": username,
                "language": language,
                "is_bot": is_bot,
                "last_seen": self.utc_now(),
            },
            "$setOnInsert": {
                "user_id": user_id,
                "created_at": self.utc_now(),

                # User state
                "banned": False,

                # Premium
                "paid": False,
                "paid_plan": None,
                "paid_at": None,
                "paid_expiry": None,

                # Trial
                "trial_used": False,
                "trial_locked": False,
                "trial_started_at": None,
                "trial_expiry": None,
                "trial_extract_limit": 0,
                "trial_extract_used": 0,

                # Statistics
                "extract_count": 0,
                "successful_extracts": 0,
                "failed_extracts": 0,

                # Activity
                "last_extract_at": None,
                "last_payment_at": None,
            },
        }

        self.users.update_one(
            {"user_id": user_id},
            update,
            upsert=True,
        )

        return self.users.find_one(
            {"user_id": user_id}
        )

    def get_user(
        self,
        user_id: int,
    ) -> Optional[Dict[str, Any]]:

        return self.users.find_one(
            {"user_id": user_id}
        )

    def user_exists(
        self,
        user_id: int,
    ) -> bool:

        return (
            self.users.count_documents(
                {"user_id": user_id},
                limit=1,
            )
            > 0
        )

    def ban_user(
        self,
        user_id: int,
        reason: str = "",
        admin_id: Optional[int] = None,
    ):

        return self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "banned": True,
                    "ban_reason": reason,
                    "banned_at": self.utc_now(),
                    "banned_by": admin_id,
                }
            },
        )

    def unban_user(
        self,
        user_id: int,
    ):

        return self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "banned": False,
                    "ban_reason": None,
                    "banned_at": None,
                    "banned_by": None,
                }
            },
        )

    # ============================================================
    # PAID USERS
    # ============================================================

    def activate_paid_user(
        self,
        user_id: int,
        plan_name: str,
        expiry: datetime,
        amount: float = 0,
        payment_id: Optional[str] = None,
    ):

        return self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "paid": True,
                    "paid_plan": plan_name,
                    "paid_at": self.utc_now(),
                    "paid_expiry": expiry,
                    "last_payment_at": self.utc_now(),
                }
            },
        )

    def deactivate_paid_user(
        self,
        user_id: int,
    ):

        return self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "paid": False,
                }
            },
        )

    def is_paid_user(
        self,
        user_id: int,
    ) -> bool:

        user = self.get_user(user_id)

        if not user:
            return False

        if not user.get("paid", False):
            return False

        expiry = user.get("paid_expiry")

        if expiry and expiry < self.utc_now():

            self.deactivate_paid_user(user_id)

            return False

        return True

    def get_paid_users(
        self,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:

        return list(
            self.users.find(
                {"paid": True}
            )
            .sort("paid_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )

    # ============================================================
    # FREE TRIAL
    # ============================================================

    def mark_trial_started(
        self,
        user_id: int,
        expiry: datetime,
        extract_limit: int,
    ):

        return self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "trial_used": True,
                    "trial_locked": False,
                    "trial_started_at": self.utc_now(),
                    "trial_expiry": expiry,
                    "trial_extract_limit": extract_limit,
                    "trial_extract_used": 0,
                }
            },
        )

    def lock_trial(
        self,
        user_id: int,
    ):

        return self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "trial_locked": True,
                }
            },
        )

    def increment_trial_extract(
        self,
        user_id: int,
    ):

        return self.users.update_one(
            {"user_id": user_id},
            {
                "$inc": {
                    "trial_extract_used": 1,
                }
            },
        )

    # ============================================================
    # TESTS
    # ============================================================

    def create_or_update_test(
        self,
        test_id: str,
        metadata: Dict[str, Any],
    ):

        data = {
            "test_id": test_id,
            **metadata,
            "updated_at": self.utc_now(),
        }

        return self.tests.update_one(
            {"test_id": test_id},
            {
                "$set": data,
                "$setOnInsert": {
                    "created_at": self.utc_now(),
                    "extract_count": 0,
                    "successful_extracts": 0,
                    "failed_extracts": 0,
                },
            },
            upsert=True,
        )

    def get_test(
        self,
        test_id: str,
    ) -> Optional[Dict[str, Any]]:

        return self.tests.find_one(
            {"test_id": test_id}
        )

    def get_categories(self) -> List[str]:

        values = self.tests.distinct(
            "category"
        )

        return sorted(
            [x for x in values if x]
        )

    def get_exams(
        self,
        category: str,
    ) -> List[str]:

        values = self.tests.distinct(
            "exam",
            {"category": category},
        )

        return sorted(
            [x for x in values if x]
        )

    def get_test_types(
        self,
        category: str,
        exam: str,
    ) -> List[str]:

        values = self.tests.distinct(
            "type",
            {
                "category": category,
                "exam": exam,
            },
        )

        return sorted(
            [x for x in values if x]
        )

    def get_years(
        self,
        category: str,
        exam: str,
        test_type: str,
    ) -> List[str]:

        values = self.tests.distinct(
            "year",
            {
                "category": category,
                "exam": exam,
                "type": test_type,
            },
        )

        return sorted(
            [str(x) for x in values if x],
            reverse=True,
        )

    def get_tests(
        self,
        category: str,
        exam: str,
        test_type: str,
        year: str,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:

        return list(
            self.tests.find(
                {
                    "category": category,
                    "exam": exam,
                    "type": test_type,
                    "year": year,
                }
            )
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )

    def search_tests(
        self,
        query: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        regex = {
            "$regex": query,
            "$options": "i",
        }

        return list(
            self.tests.find(
                {
                    "$or": [
                        {"title": regex},
                        {"exam": regex},
                        {"series": regex},
                        {"section": regex},
                        {"subsection": regex},
                    ]
                }
            )
            .sort("created_at", DESCENDING)
            .limit(limit)
        )

    # ============================================================
    # TEST EXTRACT STATISTICS
    # ============================================================

    def increment_test_extract(
        self,
        test_id: str,
        success: bool = True,
    ):

        update = {
            "$inc": {
                "extract_count": 1,
            },
            "$set": {
                "last_extract_at": self.utc_now(),
            },
        }

        if success:
            update["$inc"]["successful_extracts"] = 1
        else:
            update["$inc"]["failed_extracts"] = 1

        return self.tests.update_one(
            {"test_id": test_id},
            update,
        )

    def create_extract_record(
        self,
        user_id: int,
        test_id: str,
        status: str,
        job_id: Optional[str] = None,
    ):

        return self.extracts.insert_one(
            {
                "user_id": user_id,
                "test_id": test_id,
                "status": status,
                "job_id": job_id,
                "created_at": self.utc_now(),
            }
        )

    def get_user_extracts(
        self,
        user_id: int,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        return list(
            self.extracts.find(
                {"user_id": user_id}
            )
            .sort("created_at", DESCENDING)
            .limit(limit)
        )

    # ============================================================
    # QUEUE / JOBS
    # ============================================================

    def create_job(
        self,
        job_id: str,
        user_id: int,
        job_type: str,
        priority: int = 0,
        payload: Optional[Dict[str, Any]] = None,
    ):

        return self.jobs.insert_one(
            {
                "job_id": job_id,
                "user_id": user_id,
                "job_type": job_type,

                # Paid = high priority
                "priority": priority,

                "status": "queued",

                "payload": payload or {},

                "retry_count": 0,

                "created_at": self.utc_now(),
                "started_at": None,
                "finished_at": None,

                "error": None,
            }
        )

    def get_job(
        self,
        job_id: str,
    ):

        return self.jobs.find_one(
            {"job_id": job_id}
        )

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        **fields,
    ):

        update = {
            "$set": {
                **fields,
                "updated_at": self.utc_now(),
            }
        }

        if status:
            update["$set"]["status"] = status

        return self.jobs.update_one(
            {"job_id": job_id},
            update,
        )

    def increment_job_retry(
        self,
        job_id: str,
        error: str = "",
    ):

        return self.jobs.update_one(
            {"job_id": job_id},
            {
                "$inc": {
                    "retry_count": 1,
                },
                "$set": {
                    "error": error,
                    "updated_at": self.utc_now(),
                },
            },
        )

    # ============================================================
    # PAYMENT
    # ============================================================

    def create_payment(
        self,
        payment_id: str,
        user_id: int,
        amount: float,
        plan: str,
        screenshot_message_id: Optional[int] = None,
    ):

        return self.payments.insert_one(
            {
                "payment_id": payment_id,
                "user_id": user_id,
                "amount": amount,
                "plan": plan,

                "status": "pending",

                "screenshot_message_id": screenshot_message_id,

                "created_at": self.utc_now(),

                "reviewed_at": None,
                "reviewed_by": None,
                "reject_reason": None,
            }
        )

    def get_payment(
        self,
        payment_id: str,
    ):

        return self.payments.find_one(
            {"payment_id": payment_id}
        )

    def update_payment(
        self,
        payment_id: str,
        status: str,
        admin_id: Optional[int] = None,
        reject_reason: Optional[str] = None,
    ):

        return self.payments.update_one(
            {"payment_id": payment_id},
            {
                "$set": {
                    "status": status,
                    "reviewed_at": self.utc_now(),
                    "reviewed_by": admin_id,
                    "reject_reason": reject_reason,
                }
            },
        )

    # ============================================================
    # SETTINGS
    # ============================================================

    def set_setting(
        self,
        key: str,
        value: Any,
        updated_by: Optional[int] = None,
    ):

        return self.settings.update_one(
            {"key": key},
            {
                "$set": {
                    "value": value,
                    "updated_at": self.utc_now(),
                    "updated_by": updated_by,
                }
            },
            upsert=True,
        )

    def get_setting(
        self,
        key: str,
        default: Any = None,
    ):

        item = self.settings.find_one(
            {"key": key}
        )

        if not item:
            return default

        return item.get(
            "value",
            default,
        )

    def delete_setting(
        self,
        key: str,
    ):

        return self.settings.delete_one(
            {"key": key}
        )

    # ============================================================
    # CHANNEL SETTINGS
    # ============================================================

    def set_channel(
        self,
        channel_type: str,
        channel_id: Any,
        title: str = "",
        username: str = "",
        added_by: Optional[int] = None,
    ):

        return self.set_setting(
            f"channel:{channel_type}",
            {
                "channel_id": channel_id,
                "title": title,
                "username": username,
                "added_by": added_by,
            },
            added_by,
        )

    def get_channel(
        self,
        channel_type: str,
    ):

        return self.get_setting(
            f"channel:{channel_type}"
        )

    def remove_channel(
        self,
        channel_type: str,
    ):

        return self.delete_setting(
            f"channel:{channel_type}"
        )

    # ============================================================
    # FORCE JOIN
    # ============================================================

    def set_force_join_channels(
        self,
        channels: List[Dict[str, Any]],
        updated_by: Optional[int] = None,
    ):

        return self.set_setting(
            "force_join_channels",
            channels,
            updated_by,
        )

    def get_force_join_channels(self) -> List[Dict[str, Any]]:

        return self.get_setting(
            "force_join_channels",
            [],
        )

    # ============================================================
    # BACKUP
    # ============================================================

    def save_backup_record(
        self,
        test_id: str,
        channel_id: Any,
        message_id: int,
        github_path: str,
        github_url: str,
    ):

        return self.backups.update_one(
            {"test_id": test_id},
            {
                "$set": {
                    "test_id": test_id,
                    "channel_id": channel_id,
                    "message_id": message_id,
                    "github_path": github_path,
                    "github_url": github_url,
                    "updated_at": self.utc_now(),
                },
                "$setOnInsert": {
                    "created_at": self.utc_now(),
                },
            },
            upsert=True,
        )

    def get_backup(
        self,
        test_id: str,
    ):

        return self.backups.find_one(
            {"test_id": test_id}
        )

    # ============================================================
    # EVENTS / AUDIT LOG
    # ============================================================

    def log_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        test_id: Optional[str] = None,
        job_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):

        return self.events.insert_one(
            {
                "event_type": event_type,
                "user_id": user_id,
                "test_id": test_id,
                "job_id": job_id,
                "data": data or {},
                "created_at": self.utc_now(),
            }
        )

    # ============================================================
    # BROADCAST
    # ============================================================

    def create_broadcast(
        self,
        broadcast_id: str,
        admin_id: int,
        message: Dict[str, Any],
        audience: str = "all",
    ):

        return self.broadcasts.insert_one(
            {
                "broadcast_id": broadcast_id,
                "admin_id": admin_id,
                "message": message,
                "audience": audience,
                "status": "queued",
                "sent": 0,
                "failed": 0,
                "created_at": self.utc_now(),
                "finished_at": None,
            }
        )

    # ============================================================
    # STATS
    # ============================================================

    def get_stats(self) -> Dict[str, Any]:

        total_users = self.users.count_documents({})

        paid_users = self.users.count_documents(
            {"paid": True}
        )

        trial_users = self.users.count_documents(
            {"trial_used": True}
        )

        banned_users = self.users.count_documents(
            {"banned": True}
        )

        total_tests = self.tests.count_documents({})

        total_jobs = self.jobs.count_documents({})

        queued_jobs = self.jobs.count_documents(
            {"status": "queued"}
        )

        completed_jobs = self.jobs.count_documents(
            {"status": "done"}
        )

        failed_jobs = self.jobs.count_documents(
            {"status": "failed"}
        )

        total_extracts = self.extracts.count_documents({})

        return {
            "total_users": total_users,
            "paid_users": paid_users,
            "trial_users": trial_users,
            "banned_users": banned_users,

            "total_tests": total_tests,

            "total_jobs": total_jobs,
            "queued_jobs": queued_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,

            "total_extracts": total_extracts,
        }

    # ============================================================
    # REPORT — MOST EXTRACTED EXAMS
    # ============================================================

    def most_extracted_exams(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        pipeline = [
            {
                "$group": {
                    "_id": "$exam",
                    "extracts": {
                        "$sum": "$extract_count"
                    },
                    "tests": {
                        "$sum": 1
                    },
                }
            },
            {
                "$sort": {
                    "extracts": -1
                }
            },
            {
                "$limit": limit
            },
        ]

        return list(
            self.tests.aggregate(pipeline)
        )

    # ============================================================
    # REPORT — MOST EXTRACTED TESTS
    # ============================================================

    def most_extracted_tests(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        return list(
            self.tests.find(
                {},
                {
                    "test_id": 1,
                    "title": 1,
                    "exam": 1,
                    "type": 1,
                    "year": 1,
                    "extract_count": 1,
                },
            )
            .sort(
                "extract_count",
                DESCENDING,
            )
            .limit(limit)
        )

    # ============================================================
    # PAGINATION
    # ============================================================

    def get_users_page(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> List[Dict[str, Any]]:

        page = max(1, page)

        skip = (page - 1) * per_page

        return list(
            self.users.find({})
            .sort(
                "created_at",
                DESCENDING,
            )
            .skip(skip)
            .limit(per_page)
        )

    def get_tests_page(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> List[Dict[str, Any]]:

        page = max(1, page)

        skip = (page - 1) * per_page

        return list(
            self.tests.find({})
            .sort(
                "created_at",
                DESCENDING,
            )
            .skip(skip)
            .limit(per_page)
        )


# ================================================================
# SINGLE DATABASE INSTANCE
# ================================================================

db = MongoDatabase()

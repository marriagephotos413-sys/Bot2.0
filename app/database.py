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

    MongoDB में:
    - Test metadata
    - GitHub URL/path
    - Database Channel message ID
    - User data
    - Payment data
    - Queue/job data
    - Settings
    - Reports/statistics
    - Extract history
    save होंगे।

    Actual TCS HTML + embedded JSON:
        GitHub
            +
        Database Channel backup
    """

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        # ----------------------------------------------------
        # MongoDB URL
        # ----------------------------------------------------

        mongo_url = getattr(
            CONFIG,
            "mongo_url",
            None,
        )

        if not mongo_url:

            raise RuntimeError(
                "MONGO_URL is missing. "
                "Add MONGO_URL in Render Environment Variables."
            )

        mongo_url = str(
            mongo_url
        ).strip()

        if not mongo_url:

            raise RuntimeError(
                "MONGO_URL is empty. "
                "Add a valid MongoDB connection string."
            )

        # ----------------------------------------------------
        # Database name
        # ----------------------------------------------------

        mongo_database = getattr(
            CONFIG,
            "mongo_database",
            None,
        )

        if not mongo_database:

            mongo_database = (
                "telegram_test_bot"
            )

        mongo_database = str(
            mongo_database
        ).strip()

        if not mongo_database:

            mongo_database = (
                "telegram_test_bot"
            )

        # ----------------------------------------------------
        # Mongo client
        # ----------------------------------------------------

        self.client: MongoClient = MongoClient(
            mongo_url,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
            socketTimeoutMS=20000,
            retryWrites=True,
            appname="telegram-test-bot",
        )

        self.db: Database = self.client[
            mongo_database
        ]

        # ====================================================
        # COLLECTIONS
        # ====================================================

        self.users: Collection = self.db[
            "users"
        ]

        self.tests: Collection = self.db[
            "tests"
        ]

        self.jobs: Collection = self.db[
            "jobs"
        ]

        self.payments: Collection = self.db[
            "payments"
        ]

        self.settings: Collection = self.db[
            "settings"
        ]

        self.extracts: Collection = self.db[
            "extracts"
        ]

        self.events: Collection = self.db[
            "events"
        ]

        self.broadcasts: Collection = self.db[
            "broadcasts"
        ]

        self.backups: Collection = self.db[
            "backups"
        ]

        # ====================================================
        # CREATE INDEXES
        # ====================================================

        try:

            self._create_indexes()

            logger.info(
                "MongoDB indexes initialized."
            )

        except Exception:

            logger.exception(
                "MongoDB index creation failed."
            )

    # ========================================================
    # GENERAL
    # ========================================================

    @staticmethod
    def utc_now() -> datetime:

        return datetime.now(
            timezone.utc
        )

    # ========================================================
    # PING
    # ========================================================

    def ping(self) -> bool:

        try:

            self.client.admin.command(
                "ping"
            )

            return True

        except Exception:

            logger.exception(
                "MongoDB ping failed."
            )

            return False

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        try:

            self.client.close()

            logger.info(
                "MongoDB connection closed."
            )

        except Exception:

            logger.exception(
                "MongoDB close failed."
            )

    # ========================================================
    # INDEXES
    # ========================================================

    def _create_indexes(self):

        # ====================================================
        # USERS
        # ====================================================

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

        # ====================================================
        # TESTS
        # ====================================================

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

        # ====================================================
        # JOBS
        # ====================================================

        self.jobs.create_index(
            [
                ("status", ASCENDING),
                ("priority", DESCENDING),
                ("created_at", ASCENDING),
            ],
            name="queue_priority",
        )

        self.jobs.create_index(
            [
                ("user_id", ASCENDING),
                ("created_at", DESCENDING),
            ],
            name="user_jobs",
        )

        self.jobs.create_index(
            [("job_id", ASCENDING)],
            unique=True,
            name="unique_job_id",
        )

        # ====================================================
        # PAYMENTS
        # ====================================================

        self.payments.create_index(
            [("payment_id", ASCENDING)],
            unique=True,
            name="unique_payment_id",
        )

        self.payments.create_index(
            [
                ("user_id", ASCENDING),
                ("created_at", DESCENDING),
            ],
            name="user_payments",
        )

        self.payments.create_index(
            [
                ("status", ASCENDING),
                ("created_at", ASCENDING),
            ],
            name="pending_payments",
        )

        # ====================================================
        # EXTRACT HISTORY
        # ====================================================

        self.extracts.create_index(
            [
                ("user_id", ASCENDING),
                ("created_at", DESCENDING),
            ],
            name="user_extract_history",
        )

        self.extracts.create_index(
            [
                ("test_id", ASCENDING),
                ("created_at", DESCENDING),
            ],
            name="test_extract_history",
        )

        # ====================================================
        # EVENTS
        # ====================================================

        self.events.create_index(
            [
                ("event_type", ASCENDING),
                ("created_at", DESCENDING),
            ],
            name="event_type_time",
        )

        # ====================================================
        # SETTINGS
        # ====================================================

        self.settings.create_index(
            [("key", ASCENDING)],
            unique=True,
            name="unique_setting_key",
        )

        # ====================================================
        # BACKUPS
        # ====================================================

        self.backups.create_index(
            [("test_id", ASCENDING)],
            unique=True,
            name="unique_test_backup",
        )

        # ====================================================
        # BROADCASTS
        # ====================================================

        self.broadcasts.create_index(
            [("broadcast_id", ASCENDING)],
            unique=True,
            name="unique_broadcast_id",
        )

        logger.info(
            "All MongoDB indexes created/verified."
        )

    # ========================================================
    # IMPORTANT COMPATIBILITY METHOD
    # ========================================================

    def ensure_indexes(self) -> bool:
        """
        Public method used by main.py.

        This fixes:
            AttributeError:
            'MongoDatabase' object has no attribute
            'ensure_indexes'
        """

        try:

            self._create_indexes()

            logger.info(
                "MongoDB indexes ensured successfully."
            )

            return True

        except Exception:

            logger.exception(
                "MongoDB index initialization failed."
            )

            return False

    # ========================================================
    # USERS
    # ========================================================

    def create_or_update_user(
        self,
        user_id: int,
        name: str = "",
        username: str = "",
        language: str = "",
        is_bot: bool = False,
    ) -> Dict[str, Any]:

        now = self.utc_now()

        update = {
            "$set": {
                "name": name,
                "username": username,
                "language": language,
                "is_bot": is_bot,
                "last_seen": now,
            },
            "$setOnInsert": {
                "user_id": user_id,
                "created_at": now,

                "banned": False,

                "paid": False,
                "paid_plan": None,
                "paid_at": None,
                "paid_expiry": None,

                "trial_used": False,
                "trial_locked": False,
                "trial_started_at": None,
                "trial_expiry": None,
                "trial_extract_limit": 0,
                "trial_extract_used": 0,

                "extract_count": 0,
                "successful_extracts": 0,
                "failed_extracts": 0,

                "last_extract_at": None,
                "last_payment_at": None,
            },
        }

        self.users.update_one(
            {"user_id": user_id},
            update,
            upsert=True,
        )

        user = self.users.find_one(
            {"user_id": user_id}
        )

        return user or {}

    # ========================================================
    # GET USER
    # ========================================================

    def get_user(
        self,
        user_id: int,
    ) -> Optional[Dict[str, Any]]:

        return self.users.find_one(
            {"user_id": user_id}
        )

    # ========================================================
    # USER EXISTS
    # ========================================================

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

    # ========================================================
    # BAN USER
    # ========================================================

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

    # ========================================================
    # UNBAN USER
    # ========================================================

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

    # ========================================================
    # PAID USER
    # ========================================================

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

    # ========================================================
    # DEACTIVATE PAID USER
    # ========================================================

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

    # ========================================================
    # IS PAID USER
    # ========================================================

    def is_paid_user(
        self,
        user_id: int,
    ) -> bool:

        user = self.get_user(
            user_id
        )

        if not user:
            return False

        if not user.get(
            "paid",
            False,
        ):
            return False

        expiry = user.get(
            "paid_expiry"
        )

        if expiry:

            try:

                if expiry < self.utc_now():

                    self.deactivate_paid_user(
                        user_id
                    )

                    return False

            except TypeError:

                logger.warning(
                    "Invalid paid_expiry for user %s",
                    user_id,
                )

        return True

    # ========================================================
    # GET PAID USERS
    # ========================================================

    def get_paid_users(
        self,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:

        return list(
            self.users.find(
                {"paid": True}
            )
            .sort(
                "paid_at",
                DESCENDING,
            )
            .skip(skip)
            .limit(limit)
        )

    # ========================================================
    # TRIAL
    # ========================================================

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

    # ========================================================
    # LOCK TRIAL
    # ========================================================

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

    # ========================================================
    # INCREMENT TRIAL EXTRACT
    # ========================================================

    def increment_trial_extract(
        self,
        user_id: int,
    ):

        return self.users.update_one(
            {"user_id": user_id},
            {
                "$inc": {
                    "trial_extract_used": 1,
                    "extract_count": 1,
                },
                "$set": {
                    "last_extract_at": self.utc_now(),
                },
            },
        )

    # ========================================================
    # TESTS
    # ========================================================

    def create_or_update_test(
        self,
        test_id: str,
        metadata: Dict[str, Any],
    ):

        now = self.utc_now()

        data = {
            "test_id": test_id,
            **metadata,
            "updated_at": now,
        }

        return self.tests.update_one(
            {"test_id": test_id},
            {
                "$set": data,
                "$setOnInsert": {
                    "created_at": now,
                    "extract_count": 0,
                    "successful_extracts": 0,
                    "failed_extracts": 0,
                },
            },
            upsert=True,
        )

    # ========================================================
    # GET TEST
    # ========================================================

    def get_test(
        self,
        test_id: str,
    ) -> Optional[Dict[str, Any]]:

        return self.tests.find_one(
            {"test_id": test_id}
        )

    # ========================================================
    # CATEGORIES
    # ========================================================

    def get_categories(self) -> List[str]:

        values = self.tests.distinct(
            "category"
        )

        return sorted(
            [
                x
                for x in values
                if x
            ]
        )

    # ========================================================
    # EXAMS
    # ========================================================

    def get_exams(
        self,
        category: str,
    ) -> List[str]:

        values = self.tests.distinct(
            "exam",
            {
                "category": category
            },
        )

        return sorted(
            [
                x
                for x in values
                if x
            ]
        )

    # ========================================================
    # TEST TYPES
    # ========================================================

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
            [
                x
                for x in values
                if x
            ]
        )

    # ========================================================
    # YEARS
    # ========================================================

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
            [
                str(x)
                for x in values
                if x
            ],
            reverse=True,
        )

    # ========================================================
    # GET TESTS
    # ========================================================

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
            .sort(
                "created_at",
                DESCENDING,
            )
            .skip(skip)
            .limit(limit)
        )

    # ========================================================
    # SEARCH TESTS
    # ========================================================

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
                        {
                            "title": regex
                        },
                        {
                            "exam": regex
                        },
                        {
                            "series": regex
                        },
                        {
                            "section": regex
                        },
                        {
                            "subsection": regex
                        },
                    ]
                }
            )
            .sort(
                "created_at",
                DESCENDING,
            )
            .limit(limit)
        )

    # ========================================================
    # TEST EXTRACT STATISTICS
    # ========================================================

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

            update["$inc"][
                "successful_extracts"
            ] = 1

        else:

            update["$inc"][
                "failed_extracts"
            ] = 1

        return self.tests.update_one(
            {"test_id": test_id},
            update,
        )

    # ========================================================
    # EXTRACT RECORD
    # ========================================================

    def create_extract_record(
        self,
        user_id: int,
        test_id: str,
        status: str,
        job_id: Optional[str] = None,
    ):

        now = self.utc_now()

        result = self.extracts.insert_one(
            {
                "user_id": user_id,
                "test_id": test_id,
                "status": status,
                "job_id": job_id,
                "created_at": now,
            }
        )

        self.users.update_one(
            {"user_id": user_id},
            {
                "$inc": {
                    "extract_count": 1,
                },
                "$set": {
                    "last_extract_at": now,
                },
            },
        )

        return result

    # ========================================================
    # USER EXTRACT HISTORY
    # ========================================================

    def get_user_extracts(
        self,
        user_id: int,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        return list(
            self.extracts.find(
                {
                    "user_id": user_id
                }
            )
            .sort(
                "created_at",
                DESCENDING,
            )
            .limit(limit)
        )

    # ========================================================
    # JOBS
    # ========================================================

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

    # ========================================================
    # GET JOB
    # ========================================================

    def get_job(
        self,
        job_id: str,
    ):

        return self.jobs.find_one(
            {"job_id": job_id}
        )

    # ========================================================
    # UPDATE JOB
    # ========================================================

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

            update["$set"][
                "status"
            ] = status

        return self.jobs.update_one(
            {"job_id": job_id},
            update,
        )

    # ========================================================
    # RETRY JOB
    # ========================================================

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

    # ========================================================
    # PAYMENTS
    # ========================================================

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
                "screenshot_message_id": (
                    screenshot_message_id
                ),
                "created_at": self.utc_now(),
                "reviewed_at": None,
                "reviewed_by": None,
                "reject_reason": None,
            }
        )

    # ========================================================
    # GET PAYMENT
    # ========================================================

    def get_payment(
        self,
        payment_id: str,
    ):

        return self.payments.find_one(
            {"payment_id": payment_id}
        )

    # ========================================================
    # UPDATE PAYMENT
    # ========================================================

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

    # ========================================================
    # SETTINGS
    # ========================================================

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

    # ========================================================
    # GET SETTING
    # ========================================================

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

    # ========================================================
    # DELETE SETTING
    # ========================================================

    def delete_setting(
        self,
        key: str,
    ):

        return self.settings.delete_one(
            {"key": key}
        )

    # ========================================================
    # CHANNEL SETTINGS
    # ========================================================

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

    # ========================================================
    # GET CHANNEL
    # ========================================================

    def get_channel(
        self,
        channel_type: str,
    ):

        return self.get_setting(
            f"channel:{channel_type}"
        )

    # ========================================================
    # REMOVE CHANNEL
    # ========================================================

    def remove_channel(
        self,
        channel_type: str,
    ):

        return self.delete_setting(
            f"channel:{channel_type}"
        )

    # ========================================================
    # FORCE JOIN
    # ========================================================

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

    # ========================================================
    # GET FORCE JOIN CHANNELS
    # ========================================================

    def get_force_join_channels(
        self,
    ) -> List[Dict[str, Any]]:

        return self.get_setting(
            "force_join_channels",
            [],
        )

    # ========================================================
    # BACKUP
    # ========================================================

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

    # ========================================================
    # GET BACKUP
    # ========================================================

    def get_backup(
        self,
        test_id: str,
    ):

        return self.backups.find_one(
            {"test_id": test_id}
        )

    # ========================================================
    # EVENTS / AUDIT LOG
    # ========================================================

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

    # ========================================================
    # BROADCAST
    # ========================================================

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

    # ========================================================
    # STATS
    # ========================================================

    def get_stats(
        self,
    ) -> Dict[str, Any]:

        total_users = (
            self.users.count_documents({})
        )

        paid_users = (
            self.users.count_documents(
                {"paid": True}
            )
        )

        trial_users = (
            self.users.count_documents(
                {"trial_used": True}
            )
        )

        banned_users = (
            self.users.count_documents(
                {"banned": True}
            )
        )

        total_tests = (
            self.tests.count_documents({})
        )

        total_jobs = (
            self.jobs.count_documents({})
        )

        queued_jobs = (
            self.jobs.count_documents(
                {"status": "queued"}
            )
        )

        completed_jobs = (
            self.jobs.count_documents(
                {"status": "done"}
            )
        )

        failed_jobs = (
            self.jobs.count_documents(
                {"status": "failed"}
            )
        )

        total_extracts = (
            self.extracts.count_documents({})
        )

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

    # ========================================================
    # MOST EXTRACTED EXAMS
    # ========================================================

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
            self.tests.aggregate(
                pipeline
            )
        )

    # ========================================================
    # MOST EXTRACTED TESTS
    # ========================================================

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

    # ========================================================
    # USERS PAGINATION
    # ========================================================

    def get_users_page(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> List[Dict[str, Any]]:

        page = max(
            1,
            page,
        )

        skip = (
            page - 1
        ) * per_page

        return list(
            self.users.find({})
            .sort(
                "created_at",
                DESCENDING,
            )
            .skip(skip)
            .limit(per_page)
        )

    # ========================================================
    # TESTS PAGINATION
    # ========================================================

    def get_tests_page(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> List[Dict[str, Any]]:

        page = max(
            1,
            page,
        )

        skip = (
            page - 1
        ) * per_page

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
# COMPATIBILITY / COMPLETE BOT API
# ================================================================
# The project contains several feature modules written against a
# richer DB interface. These methods keep every command working
# while retaining the same Mongo collections.

import uuid as _uuid
from datetime import timedelta as _timedelta


def _create_test(self, title, category="Other", exam="General", test_type="Mock", year="2026",
                 section="", subsection="", question_count=0, language="Hindi", shift="",
                 github_path="", github_url="", source_filename="", source_message_id=None, **extra):
    test_id = str(extra.pop("test_id", "")) or _uuid.uuid4().hex[:12]
    metadata = {
        "title": title, "category": category or "Other", "exam": exam or "General",
        "type": test_type or "Mock", "test_type": test_type or "Mock", "year": str(year or "2026"),
        "section": section or "", "subsection": subsection or "", "question_count": int(question_count or 0),
        "language": language or "Hindi", "shift": shift or "", "github_path": github_path or "",
        "github_url": github_url or "", "source_filename": source_filename or "",
        "source_message_id": source_message_id, "extract_count": 0, "successful_extracts": 0,
        "failed_extracts": 0, "status": "ready", **extra,
    }
    self.create_or_update_test(test_id, metadata)
    return test_id


def _mark_test_ready(self, test_id, github_path="", github_url=""):
    return self.tests.update_one({"test_id": test_id}, {"$set": {
        "status": "ready", "github_path": github_path or "", "github_url": github_url or "",
        "updated_at": self.utc_now(),
    }})


def _count_users(self): return self.users.count_documents({})
def _count_paid_users(self): return self.users.count_documents({"paid": True})

def _get_users(self, page=1, per_page=20): return self.get_users_page(page, per_page)

def _get_all_user_ids(self): return [int(x["user_id"]) for x in self.users.find({}, {"user_id": 1}) if x.get("user_id") is not None]

def _get_bot_stats(self):
    total_users = self.users.count_documents({})
    active_users = self.users.count_documents({"last_seen": {"$ne": None}})
    paid_users = self.users.count_documents({"paid": True})
    banned_users = self.users.count_documents({"banned": True})
    total_tests = self.tests.count_documents({})
    total_extracts = self.extracts.count_documents({})
    successful = self.extracts.count_documents({"status": "completed"})
    failed = self.extracts.count_documents({"status": "failed"})
    revenue = sum(float(x.get("amount", 0) or 0) for x in self.payments.find({"status": "approved"}, {"amount": 1}))
    q = self.get_queue_status()
    return {"total_users": total_users, "active_users": active_users, "paid_users": paid_users,
            "banned_users": banned_users, "total_tests": total_tests, "total_extracts": total_extracts,
            "successful_extracts": successful, "failed_extracts": failed, "revenue": revenue,
            "queue_size": q.get("total_queued", 0)}


def _get_queue_status(self):
    priority = self.jobs.count_documents({"status": "queued", "priority": {"$gte": 100}})
    normal = self.jobs.count_documents({"status": "queued", "priority": {"$lt": 100}})
    running = self.jobs.count_documents({"status": "running"})
    return {"priority_queued": priority, "normal_queued": normal, "total_queued": priority + normal,
            "running": running, "completed": self.jobs.count_documents({"status": "done"}),
            "failed": self.jobs.count_documents({"status": "failed"})}


def _get_all_tests_for_backup(self): return list(self.tests.find({}).sort("created_at", DESCENDING))

def _get_extract_report(self):
    return {"total": self.extracts.count_documents({}),
            "queued": self.extracts.count_documents({"status": {"$in": ["queued", "running"]}}),
            "completed": self.extracts.count_documents({"status": "completed"}),
            "failed": self.extracts.count_documents({"status": "failed"})}


def _create_report(self, user_id, text):
    result = self.db["reports"].insert_one({"report_id": _uuid.uuid4().hex[:12], "user_id": user_id,
        "text": text, "status": "open", "created_at": self.utc_now()})
    return str(result.inserted_id)


def _activate_trial(self, user_id):
    user = self.get_user(user_id) or {}
    if user.get("paid"):
        return {"success": False, "reason": "आप पहले से Premium user हैं।"}
    if user.get("trial_used"):
        return {"success": False, "reason": "आपका Free Trial पहले ही use हो चुका है।"}
    if not self.get_setting("trial_enabled", True) or not self.get_setting("trial_allowed", True):
        return {"success": False, "reason": "Free Trial अभी बंद है।"}
    days = int(self.get_setting("trial_days", 1) or 1)
    limit = int(self.get_setting("trial_extract_limit", 1) or 1)
    expiry = self.utc_now() + _timedelta(days=days)
    self.mark_trial_started(user_id, expiry, limit)
    return {"success": True, "trial_days": days, "trial_limit": limit, "trial_expiry": expiry.strftime("%d-%m-%Y %H:%M UTC")}


def _get_prices(self):
    prices = self.get_setting("prices", None)
    if isinstance(prices, dict):
        return {"7_days": prices.get("7_days", 49), "30_days": prices.get("30_days", 149),
                "90_days": prices.get("90_days", 299), "lifetime": prices.get("lifetime", 999)}
    return {"7_days": 49, "30_days": 149, "90_days": 299, "lifetime": 999}


def _create_payment(self, user_id, amount, plan, payment_id=None, screenshot_message_id=None):
    payment_id = payment_id or ("PAY-" + _uuid.uuid4().hex[:12].upper())
    self.payments.update_one({"payment_id": payment_id}, {"$setOnInsert": {
        "payment_id": payment_id, "user_id": user_id, "amount": float(amount or 0), "plan": plan,
        "status": "pending", "screenshot_message_id": screenshot_message_id, "created_at": self.utc_now(),
        "reviewed_at": None, "reviewed_by": None, "reject_reason": None,
    }}, upsert=True)
    return payment_id


def _attach_payment_screenshot(self, payment_id, file_id, file_type="photo", message_id=None):
    return self.payments.update_one({"payment_id": payment_id}, {"$set": {
        "screenshot_file_id": file_id, "screenshot_file_type": file_type,
        "screenshot_message_id": message_id, "updated_at": self.utc_now(),
    }})


def _get_user_payments(self, user_id, limit=10):
    return list(self.payments.find({"user_id": user_id}).sort("created_at", DESCENDING).limit(limit))


def _add_force_join_channel(self, channel):
    channels = self.get_force_join_channels()
    channels.append(channel if isinstance(channel, dict) else {"channel_id": channel})
    return self.set_force_join_channels(channels)


def _create_extract_job(self, user_id, test_id, priority=10, is_paid=False, retry_of=None):
    job_id = "EXT-" + _uuid.uuid4().hex[:12].upper()
    self.extracts.insert_one({"job_id": job_id, "queue_job_id": None, "user_id": user_id, "test_id": test_id,
        "priority": priority, "is_paid": is_paid, "retry_of": retry_of, "status": "queued",
        "progress": 0, "status_message_id": None, "created_at": self.utc_now(), "updated_at": self.utc_now(),
        "error": None, "retry_count": 0})
    return job_id


def _get_extract_job(self, job_id): return self.extracts.find_one({"job_id": job_id})
def _get_extract_job_by_queue_id(self, queue_job_id): return self.extracts.find_one({"queue_job_id": queue_job_id})
def _get_active_extract_job(self, user_id, test_id): return self.extracts.find_one({"user_id": user_id, "test_id": test_id, "status": {"$in": ["queued", "running"]}})
def _attach_queue_job(self, job_id, queue_job_id): return self.extracts.update_one({"job_id": job_id}, {"$set": {"queue_job_id": queue_job_id, "updated_at": self.utc_now()}})
def _attach_status_message(self, job_id, message_id): return self.extracts.update_one({"job_id": job_id}, {"$set": {"status_message_id": message_id, "updated_at": self.utc_now()}})
def _get_status_message_id(self, job_id):
    x=self.get_extract_job(job_id) or {}; return x.get("status_message_id")

def _mark_extract_failed(self, job_id, error=""):
    return self.extracts.update_one({"job_id": job_id}, {"$set": {"status": "failed", "error": error, "updated_at": self.utc_now()}})
def _mark_extract_success(self, job_id):
    return self.extracts.update_one({"job_id": job_id}, {"$set": {"status": "completed", "progress": 100, "updated_at": self.utc_now()}})
def _finalize_extract(self, job_id, success=True, error=None): return self._mark_extract_success(job_id) if success else self._mark_extract_failed(job_id, error or "Unknown error")
def _increment_extract_retry(self, job_id): return self.extracts.update_one({"job_id": job_id}, {"$inc": {"retry_count": 1}, "$set": {"updated_at": self.utc_now()}})
def _should_update_progress(self, job_id, percent, force=False): return True
def _update_extract_progress(self, job_id, percent, message=""):
    return self.extracts.update_one({"job_id": job_id}, {"$set": {"progress": int(percent), "progress_message": message, "status": "running", "updated_at": self.utc_now()}})
def _increment_extract_count(self, test_id):
    return self.tests.update_one({"test_id": test_id}, {"$inc": {"extract_count": 1, "successful_extracts": 1}, "$set": {"last_extract_at": self.utc_now()}})
def _reserve_extract(self, user_id, test_id, job_id):
    self.users.update_one({"user_id": user_id}, {"$inc": {"extract_count": 1}, "$set": {"last_extract_at": self.utc_now()}})
    return self.extracts.update_one({"job_id": job_id}, {"$set": {"reserved": True, "updated_at": self.utc_now()}})
def _check_extract_access(self, user_id):
    if not self.get_setting("test_extraction_enabled", True): return {"allowed": False, "reason": "Test extraction अभी बंद है।"}
    user=self.get_user(user_id) or {}
    if user.get("banned"): return {"allowed": False, "reason": "आपका account banned है।"}
    return {"allowed": True}

# Demo test: lets an admin verify the complete Index -> Details -> Extract UI
# without GitHub credentials. The HTML is kept in the backup collection as a
# fallback source; normal uploads still prefer GitHub.
def _seed_demo_test(self):
    test_id = "DEMO-2026-001"
    html = "<!doctype html><html><head><meta charset='utf-8'><title>Demo TCS Test</title></head><body><h1>Demo Test</h1><p>This is a bot system test.</p></body></html>"
    self.create_or_update_test(test_id, {
        "title": "Demo SSC GD TCS Test", "category": "SSC", "exam": "SSC GD", "type": "Mock",
        "test_type": "Mock", "year": "2026", "section": "General", "subsection": "Demo",
        "question_count": 5, "language": "Hindi", "shift": "Demo", "github_path": "", "github_url": "",
        "status": "ready", "source_filename": "demo.html", "extract_count": 0,
    })
    self.backups.update_one({"test_id": test_id}, {"$set": {"test_id": test_id, "html": html,
        "github_path": "", "github_url": "", "updated_at": self.utc_now()}, "$setOnInsert": {"created_at": self.utc_now()}}, upsert=True)
    return test_id

# Bind compatibility methods.
MongoDatabase.create_test = _create_test
MongoDatabase.mark_test_ready = _mark_test_ready
MongoDatabase.count_users = _count_users
MongoDatabase.count_paid_users = _count_paid_users
MongoDatabase.get_users = _get_users
MongoDatabase.get_all_user_ids = _get_all_user_ids
MongoDatabase.get_bot_stats = _get_bot_stats
MongoDatabase.get_queue_status = _get_queue_status
MongoDatabase.get_all_tests_for_backup = _get_all_tests_for_backup
MongoDatabase.get_extract_report = _get_extract_report
MongoDatabase.create_report = _create_report
MongoDatabase.activate_trial = _activate_trial
MongoDatabase.get_prices = _get_prices
MongoDatabase.create_payment = _create_payment
MongoDatabase.attach_payment_screenshot = _attach_payment_screenshot
MongoDatabase.get_user_payments = _get_user_payments
MongoDatabase.add_force_join_channel = _add_force_join_channel
MongoDatabase.create_extract_job = _create_extract_job
MongoDatabase.get_extract_job = _get_extract_job
MongoDatabase.get_extract_job_by_queue_id = _get_extract_job_by_queue_id
MongoDatabase.get_active_extract_job = _get_active_extract_job
MongoDatabase.attach_queue_job = _attach_queue_job
MongoDatabase.attach_status_message = _attach_status_message
MongoDatabase.get_status_message_id = _get_status_message_id
MongoDatabase.mark_extract_failed = _mark_extract_failed
MongoDatabase.mark_extract_success = _mark_extract_success
MongoDatabase.finalize_extract = _finalize_extract
MongoDatabase.increment_extract_retry = _increment_extract_retry
MongoDatabase.should_update_progress = _should_update_progress
MongoDatabase.update_extract_progress = _update_extract_progress
MongoDatabase.increment_extract_count = _increment_extract_count
MongoDatabase.reserve_extract = _reserve_extract
MongoDatabase.check_extract_access = _check_extract_access
MongoDatabase.seed_demo_test = _seed_demo_test



def _get_channel_setting(self, name):
    return self.get_channel(name) or self.get_setting(name)


def _set_payment_verification_message(self, payment_id, channel_id, message_id):
    return self.payments.update_one({"payment_id": payment_id}, {"$set": {
        "verification_channel_id": channel_id, "verification_message_id": message_id,
        "updated_at": self.utc_now(),
    }})


def _approve_payment(self, payment_id, admin_id=None):
    result = self.payments.update_one({"payment_id": payment_id, "status": "pending"}, {"$set": {
        "status": "approved", "reviewed_at": self.utc_now(), "reviewed_by": admin_id,
    }})
    return result.modified_count > 0


def _reject_payment(self, payment_id, admin_id=None, reason=None):
    result = self.payments.update_one({"payment_id": payment_id, "status": "pending"}, {"$set": {
        "status": "rejected", "reviewed_at": self.utc_now(), "reviewed_by": admin_id,
        "reject_reason": reason,
    }})
    return result.modified_count > 0


def _cancel_payment(self, payment_id):
    return self.payments.update_one({"payment_id": payment_id, "status": "pending"}, {"$set": {
        "status": "cancelled", "updated_at": self.utc_now(),
    }})


def _add_paid_user(self, user_id, plan, payment_id=None):
    plan_days = {"7_days": 7, "30_days": 30, "90_days": 90, "lifetime": None}
    days = plan_days.get(str(plan))
    expiry = None if days is None else self.utc_now() + _timedelta(days=days)
    return self.activate_paid_user(user_id, str(plan), expiry, payment_id=payment_id)

MongoDatabase.get_channel_setting = _get_channel_setting
MongoDatabase.set_payment_verification_message = _set_payment_verification_message
MongoDatabase.approve_payment = _approve_payment
MongoDatabase.reject_payment = _reject_payment
MongoDatabase.cancel_payment = _cancel_payment
MongoDatabase.add_paid_user = _add_paid_user


# ================================================================
# SINGLE DATABASE INSTANCE
# ================================================================

db = MongoDatabase()

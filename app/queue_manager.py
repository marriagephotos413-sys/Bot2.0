import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from .config import CONFIG
from .database import db

logger = logging.getLogger(__name__)


class QueueManagerError(Exception):
    """Queue manager error."""


class QueueManager:
    """
    High-load queue manager.

    Priority:

        💎 PAID USER
              ↓
        🟢 FREE/TRIAL USER

    Upload jobs और Extract jobs दोनों queue में जा सकते हैं।

    MongoDB में job metadata रहता है।
    Actual Test JSON MongoDB में नहीं रखा जाता।
    """

    def __init__(self):

        self.running = False

        self.workers = []

        # --------------------------------------------------------
        # Internal queues
        #
        # PriorityQueue में:
        #
        # priority = 100  → Paid
        # priority = 50   → Admin upload
        # priority = 10   → Trial/Free
        # --------------------------------------------------------

        self.queue = asyncio.PriorityQueue()

        self.active_jobs = set()

        self.job_handlers: Dict[
            str,
            Callable[
                [Dict[str, Any]],
                Awaitable[Any]
            ]
        ] = {}

        # --------------------------------------------------------
        # Progress callbacks
        #
        # job_id -> callback
        # --------------------------------------------------------

        self.progress_callbacks = {}

    # ============================================================
    # START
    # ============================================================

    async def start(self):

        if self.running:
            return

        self.running = True

        total_workers = max(
            1,
            CONFIG.worker_count,
        )

        logger.info(
            "Starting %s queue workers",
            total_workers,
        )

        for index in range(
            total_workers
        ):

            worker = asyncio.create_task(
                self.worker_loop(
                    index
                )
            )

            self.workers.append(
                worker
            )

    # ============================================================
    # STOP
    # ============================================================

    async def stop(self):

        self.running = False

        for worker in self.workers:

            worker.cancel()

        if self.workers:

            await asyncio.gather(
                *self.workers,
                return_exceptions=True,
            )

        self.workers.clear()

        logger.info(
            "Queue workers stopped"
        )

    # ============================================================
    # REGISTER HANDLER
    # ============================================================

    def register_handler(
        self,
        job_type: str,
        handler: Callable[
            [Dict[str, Any]],
            Awaitable[Any]
        ],
    ):

        self.job_handlers[
            job_type
        ] = handler

        logger.info(
            "Queue handler registered: %s",
            job_type,
        )

    # ============================================================
    # PRIORITY
    # ============================================================

    @staticmethod
    def get_priority(
        is_paid: bool = False,
        is_admin: bool = False,
        is_trial: bool = False,
    ) -> int:

        # Admin highest
        if is_admin:
            return 1000

        # Paid user
        if is_paid:
            return 500

        # Trial
        if is_trial:
            return 100

        # Free user
        return 10

    # ============================================================
    # ADD JOB
    # ============================================================

    async def add_job(
        self,
        user_id: int,
        job_type: str,
        payload: Optional[
            Dict[str, Any]
        ] = None,
        is_paid: bool = False,
        is_admin: bool = False,
        is_trial: bool = False,
        callback=None,
    ) -> str:

        job_id = uuid.uuid4().hex

        priority = self.get_priority(
            is_paid=is_paid,
            is_admin=is_admin,
            is_trial=is_trial,
        )

        payload = payload or {}

        # --------------------------------------------------------
        # Save job metadata
        # --------------------------------------------------------

        db.create_job(
            job_id=job_id,
            user_id=user_id,
            job_type=job_type,
            priority=priority,
            payload=payload,
        )

        # --------------------------------------------------------
        # Progress callback
        # --------------------------------------------------------

        if callback:

            self.progress_callbacks[
                job_id
            ] = callback

        # --------------------------------------------------------
        # PriorityQueue
        #
        # Negative priority इसलिए:
        #
        # 1000 पहले
        # 500 उसके बाद
        # 10 सबसे बाद
        # --------------------------------------------------------

        await self.queue.put(
            (
                -priority,
                datetime.now(
                    timezone.utc
                ).timestamp(),
                job_id,
            )
        )

        logger.info(
            "Job queued: %s priority=%s type=%s",
            job_id,
            priority,
            job_type,
        )

        return job_id

    # ============================================================
    # WORKER
    # ============================================================

    async def worker_loop(
        self,
        worker_id: int,
    ):

        logger.info(
            "Queue worker %s started",
            worker_id,
        )

        while self.running:

            try:

                (
                    negative_priority,
                    created_timestamp,
                    job_id,
                ) = await self.queue.get()

                try:

                    await self.process_job(
                        job_id
                    )

                finally:

                    self.queue.task_done()

            except asyncio.CancelledError:

                break

            except Exception:

                logger.exception(
                    "Worker %s crashed while processing job",
                    worker_id,
                )

                # Worker crash होने पर पूरा worker बंद
                # नहीं होगा।
                await asyncio.sleep(
                    1
                )

        logger.info(
            "Queue worker %s stopped",
            worker_id,
        )

    # ============================================================
    # PROCESS JOB
    # ============================================================

    async def process_job(
        self,
        job_id: str,
    ):

        if job_id in self.active_jobs:

            logger.warning(
                "Job already active: %s",
                job_id,
            )

            return

        job = db.get_job(
            job_id
        )

        if not job:

            logger.error(
                "Job not found: %s",
                job_id,
            )

            return

        job_type = job.get(
            "job_type"
        )

        handler = self.job_handlers.get(
            job_type
        )

        if not handler:

            db.update_job(
                job_id,
                status="failed",
                error=(
                    f"No handler registered "
                    f"for {job_type}"
                ),
            )

            return

        self.active_jobs.add(
            job_id
        )

        try:

            # ----------------------------------------------------
            # Mark processing
            # ----------------------------------------------------

            db.update_job(
                job_id,
                status="processing",
                started_at=datetime.now(
                    timezone.utc
                ),
            )

            await self.emit_progress(
                job_id,
                "processing",
                5,
                "⚙️ Processing शुरू...",
            )

            # ----------------------------------------------------
            # Handler
            # ----------------------------------------------------

            result = await handler(
                job
            )

            # ----------------------------------------------------
            # Success
            # ----------------------------------------------------

            db.update_job(
                job_id,
                status="done",
                finished_at=datetime.now(
                    timezone.utc
                ),
                result=result,
            )

            await self.emit_progress(
                job_id,
                "done",
                100,
                "✅ Processing complete",
                result=result,
            )

        except asyncio.CancelledError:

            db.update_job(
                job_id,
                status="cancelled",
                finished_at=datetime.now(
                    timezone.utc
                ),
            )

            await self.emit_progress(
                job_id,
                "cancelled",
                100,
                "⚠️ Job cancelled",
            )

        except Exception as exc:

            logger.exception(
                "Job failed: %s",
                job_id,
            )

            await self.handle_failure(
                job,
                exc,
            )

        finally:

            self.active_jobs.discard(
                job_id
            )

            self.progress_callbacks.pop(
                job_id,
                None,
            )

    # ============================================================
    # FAILURE + RETRY
    # ============================================================

    async def handle_failure(
        self,
        job: Dict[str, Any],
        error: Exception,
    ):

        job_id = job["job_id"]

        retry_count = int(
            job.get(
                "retry_count",
                0,
            )
        )

        error_text = str(
            error
        )[:2000]

        # --------------------------------------------------------
        # Automatic retry
        # --------------------------------------------------------

        if (
            retry_count
            < CONFIG.max_retry_count
        ):

            db.increment_job_retry(
                job_id,
                error=error_text,
            )

            db.update_job(
                job_id,
                status="retrying",
            )

            await self.emit_progress(
                job_id,
                "retrying",
                0,
                (
                    "🔄 Failed हुआ। "
                    f"Retry {retry_count + 1}/"
                    f"{CONFIG.max_retry_count}"
                ),
            )

            # थोड़ा delay ताकि transient error ठीक हो सके।
            await asyncio.sleep(
                min(
                    2 ** retry_count,
                    30,
                )
            )

            # ----------------------------------------------------
            # Same priority के साथ वापस queue में
            # ----------------------------------------------------

            priority = int(
                job.get(
                    "priority",
                    10,
                )
            )

            await self.queue.put(
                (
                    -priority,
                    datetime.now(
                        timezone.utc
                    ).timestamp(),
                    job_id,
                )
            )

            return

        # --------------------------------------------------------
        # Final failure
        # --------------------------------------------------------

        db.update_job(
            job_id,
            status="failed",
            finished_at=datetime.now(
                timezone.utc
            ),
            error=error_text,
        )

        await self.emit_progress(
            job_id,
            "failed",
            100,
            (
                "❌ Processing failed.\n"
                "Retry button available."
            ),
        )

    # ============================================================
    # MANUAL RETRY
    # ============================================================

    async def retry_job(
        self,
        job_id: str,
    ) -> bool:

        job = db.get_job(
            job_id
        )

        if not job:

            return False

        status = job.get(
            "status"
        )

        if status not in (
            "failed",
            "cancelled",
            "retrying",
        ):

            return False

        # --------------------------------------------------------
        # Reset retry state
        # --------------------------------------------------------

        db.update_job(
            job_id,
            status="queued",
            error=None,
        )

        priority = int(
            job.get(
                "priority",
                10,
            )
        )

        await self.queue.put(
            (
                -priority,
                datetime.now(
                    timezone.utc
                ).timestamp(),
                job_id,
            )
        )

        await self.emit_progress(
            job_id,
            "queued",
            0,
            "🔄 Retry queue में डाल दिया गया।",
        )

        return True

    # ============================================================
    # CANCEL JOB
    # ============================================================

    async def cancel_job(
        self,
        job_id: str,
    ) -> bool:

        job = db.get_job(
            job_id
        )

        if not job:

            return False

        if job.get(
            "status"
        ) in (
            "done",
            "failed",
            "cancelled",
        ):

            return False

        db.update_job(
            job_id,
            status="cancelled",
            finished_at=datetime.now(
                timezone.utc
            ),
        )

        await self.emit_progress(
            job_id,
            "cancelled",
            100,
            "❌ Job cancelled.",
        )

        return True

    # ============================================================
    # PROGRESS CALLBACK
    # ============================================================

    async def emit_progress(
        self,
        job_id: str,
        status: str,
        percent: int,
        message: str,
        **extra,
    ):

        callback = (
            self.progress_callbacks.get(
                job_id
            )
        )

        if not callback:

            return

        payload = {
            "job_id": job_id,
            "status": status,
            "percent": max(
                0,
                min(
                    100,
                    percent,
                ),
            ),
            "message": message,
            **extra,
        }

        try:

            result = callback(
                payload
            )

            if asyncio.iscoroutine(
                result
            ):

                await result

        except Exception:

            logger.exception(
                "Progress callback failed: %s",
                job_id,
            )

    # ============================================================
    # UPDATE PROGRESS FROM HANDLER
    # ============================================================

    async def progress(
        self,
        job_id: str,
        percent: int,
        message: str,
    ):

        db.update_job(
            job_id,
            progress=max(
                0,
                min(
                    100,
                    percent,
                ),
            ),
            progress_message=message,
        )

        await self.emit_progress(
            job_id,
            "processing",
            percent,
            message,
        )

    # ============================================================
    # QUEUE SIZE
    # ============================================================

    def queue_size(self) -> int:

        return self.queue.qsize()

    # ============================================================
    # ACTIVE JOBS
    # ============================================================

    def active_count(self) -> int:

        return len(
            self.active_jobs
        )

    # ============================================================
    # USER POSITION
    # ============================================================

    def get_user_position(
        self,
        user_id: int,
    ) -> Optional[int]:

        """
        Approximate queue position.

        Paid users को priority के हिसाब से पहले
        रखा जाता है।
        """

        jobs = list(
            db.jobs.find(
                {
                    "status": {
                        "$in": [
                            "queued",
                            "retrying",
                        ]
                    }
                },
                {
                    "job_id": 1,
                    "user_id": 1,
                    "priority": 1,
                    "created_at": 1,
                },
            ).sort(
                [
                    (
                        "priority",
                        -1,
                    ),
                    (
                        "created_at",
                        1,
                    ),
                ]
            )
        )

        position = 0

        for job in jobs:

            position += 1

            if job.get(
                "user_id"
            ) == user_id:

                return position

        return None

    # ============================================================
    # LOAD STATUS
    # ============================================================

    def load_status(self) -> Dict[str, Any]:

        return {
            "queue_size":
                self.queue_size(),

            "active_jobs":
                self.active_count(),

            "running":
                self.running,

            "workers":
                len(self.workers),
        }


# ================================================================
# SINGLE INSTANCE
# ================================================================

queue_manager = QueueManager()

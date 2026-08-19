import asyncio
import heapq
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass(order=True)
class QueueItem:
    """
    Priority queue item.

    Higher priority पहले process होगा।
    heapq smallest value पहले निकालता है,
    इसलिए priority को negative रखा जाता है।
    """

    sort_priority: int
    created_at: float
    sequence: int

    job_id: str = field(compare=False)
    user_id: int = field(compare=False)
    job_type: str = field(compare=False)
    payload: Dict[str, Any] = field(compare=False, default_factory=dict)

    priority: int = field(compare=False, default=10)


class QueueManager:
    """
    Centralized high-load queue manager.

    Priority:

        PAID USER
             ↓
        priority = 100

        FREE USER
             ↓
        priority = 10

    इससे paid users को पहले processing मिलेगी।

    Important:
        हर user के लिए अलग worker नहीं बनता।
        Limited workers ही jobs process करते हैं।

    इससे बहुत ज्यादा users आने पर
    Render पर अचानक हजारों tasks spawn नहीं होंगे।
    """

    def __init__(
        self,
        max_workers: int = 3,
        max_queue_size: int = 5000,
    ):

        self.max_workers = max(
            1,
            int(max_workers),
        )

        self.max_queue_size = max(
            100,
            int(max_queue_size),
        )

        # --------------------------------------------------------
        # Priority Heap
        # --------------------------------------------------------

        self._queue = []

        self._sequence = 0

        self._queue_lock = asyncio.Lock()

        self._queue_event = asyncio.Event()

        # --------------------------------------------------------
        # Running jobs
        # --------------------------------------------------------

        self.running_jobs = {}

        self.running_users = {}

        # --------------------------------------------------------
        # Workers
        # --------------------------------------------------------

        self.workers = []

        self.started = False

        self.stopping = False

        # --------------------------------------------------------
        # Telegram bot
        # --------------------------------------------------------

        self.bot = None

        # --------------------------------------------------------
        # Processors
        # --------------------------------------------------------

        self.processors = {}

        # --------------------------------------------------------
        # Stats
        # --------------------------------------------------------

        self.stats = {
            "total_added": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_retried": 0,
        }

    # ============================================================
    # CONFIGURE BOT
    # ============================================================

    def set_bot(
        self,
        bot,
    ):

        """
        Telegram Bot reference.

        Extract/upload workers को direct Telegram
        notification भेजने के लिए use होता है।
        """

        self.bot = bot

    # ============================================================
    # REGISTER PROCESSOR
    # ============================================================

    def register_processor(
        self,
        job_type: str,
        processor,
    ):

        """
        Example:

            queue_manager.register_processor(
                "test_extract",
                extract_handlers.process_extract_job
            )

        processor async function होना चाहिए।
        """

        if not job_type:

            raise ValueError(
                "job_type required"
            )

        if not callable(
            processor
        ):

            raise TypeError(
                "processor must be callable"
            )

        self.processors[
            job_type
        ] = processor

        logger.info(
            "Registered queue processor: %s",
            job_type,
        )

    # ============================================================
    # START
    # ============================================================

    async def start(
        self,
    ):

        if self.started:

            return

        self.stopping = False

        self.started = True

        self.workers = []

        for index in range(
            self.max_workers
        ):

            worker = asyncio.create_task(
                self._worker(
                    index + 1
                ),
                name=(
                    f"queue-worker-{index + 1}"
                ),
            )

            self.workers.append(
                worker
            )

        logger.info(
            "Queue manager started with %s workers",
            self.max_workers,
        )

    # ============================================================
    # STOP
    # ============================================================

    async def stop(
        self,
        wait: bool = True,
    ):

        if not self.started:

            return

        self.stopping = True

        self._queue_event.set()

        if wait and self.workers:

            results = await asyncio.gather(
                *self.workers,
                return_exceptions=True,
            )

            for result in results:

                if isinstance(
                    result,
                    Exception,
                ):

                    logger.error(
                        "Queue worker stopped with error: %s",
                        result,
                    )

        self.workers = []

        self.started = False

        logger.info(
            "Queue manager stopped"
        )

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
        priority: int = 10,
        is_admin: bool = False,
    ) -> str:

        """
        Job queue में add करता है।

        Priority:

            Admin = 200
            Paid  = 100
            Free  = 10
        """

        if self.stopping:

            raise RuntimeError(
                "Queue manager is stopping."
            )

        if not self.started:

            # Safety:
            # Application startup के दौरान अगर
            # worker start नहीं हुआ है तो automatically start.
            await self.start()

        # --------------------------------------------------------
        # Queue capacity
        # --------------------------------------------------------

        async with self._queue_lock:

            if len(
                self._queue
            ) >= self.max_queue_size:

                raise RuntimeError(
                    "Server queue is full."
                )

            # ----------------------------------------------------
            # Normalize priority
            # ----------------------------------------------------

            if is_admin:

                priority = max(
                    priority,
                    200,
                )

            else:

                priority = max(
                    priority,
                    1,
                )

            # ----------------------------------------------------
            # ID
            # ----------------------------------------------------

            job_id = (
                f"JOB-"
                f"{int(time.time())}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )

            self._sequence += 1

            item = QueueItem(
                sort_priority=-priority,
                created_at=time.time(),
                sequence=self._sequence,
                job_id=job_id,
                user_id=int(
                    user_id
                ),
                job_type=job_type,
                payload=payload or {},
                priority=priority,
            )

            heapq.heappush(
                self._queue,
                item,
            )

            self.stats[
                "total_added"
            ] += 1

        # --------------------------------------------------------
        # Wake workers
        # --------------------------------------------------------

        self._queue_event.set()

        logger.info(
            "Job queued: %s priority=%s type=%s user=%s",
            job_id,
            priority,
            job_type,
            user_id,
        )

        return job_id

    # ============================================================
    # WORKER
    # ============================================================

    async def _worker(
        self,
        worker_id: int,
    ):

        logger.info(
            "Worker %s started",
            worker_id,
        )

        while not self.stopping:

            item = None

            try:

                item = await self._get_next_job()

                if item is None:

                    continue

                await self._run_job(
                    worker_id,
                    item,
                )

            except asyncio.CancelledError:

                logger.info(
                    "Worker %s cancelled",
                    worker_id,
                )

                raise

            except Exception:

                logger.exception(
                    "Worker %s unexpected error",
                    worker_id,
                )

                # Worker crash नहीं होना चाहिए।
                await asyncio.sleep(
                    1
                )

        logger.info(
            "Worker %s stopped",
            worker_id,
        )

    # ============================================================
    # GET NEXT JOB
    # ============================================================

    async def _get_next_job(
        self,
    ) -> Optional[QueueItem]:

        while not self.stopping:

            async with self._queue_lock:

                if self._queue:

                    item = heapq.heappop(
                        self._queue
                    )

                    self.running_jobs[
                        item.job_id
                    ] = item

                    self.running_users[
                        item.user_id
                    ] = (
                        self.running_users.get(
                            item.user_id,
                            0,
                        )
                        + 1
                    )

                    return item

                self._queue_event.clear()

            try:

                await asyncio.wait_for(
                    self._queue_event.wait(),
                    timeout=5,
                )

            except asyncio.TimeoutError:

                continue

        return None

    # ============================================================
    # RUN JOB
    # ============================================================

    async def _run_job(
        self,
        worker_id: int,
        item: QueueItem,
    ):

        logger.info(
            "Worker %s processing %s",
            worker_id,
            item.job_id,
        )

        processor = self.processors.get(
            item.job_type
        )

        if processor is None:

            logger.error(
                "No processor registered for %s",
                item.job_type,
            )

            await self._job_failed(
                item,
                "Processor not registered.",
            )

            return

        max_retries = self._get_retry_limit(
            item.job_type
        )

        attempt = 0

        while attempt <= max_retries:

            try:

                result = await processor(
                    {
                        "job_id": item.job_id,
                        "user_id": item.user_id,
                        "job_type": item.job_type,
                        "payload": item.payload,
                        "priority": item.priority,
                        "attempt": attempt,
                    }
                )

                await self._job_completed(
                    item,
                    result,
                )

                return

            except asyncio.CancelledError:

                raise

            except Exception as exc:

                attempt += 1

                logger.exception(
                    "Job %s failed attempt %s/%s",
                    item.job_id,
                    attempt,
                    max_retries + 1,
                )

                if attempt > max_retries:

                    await self._job_failed(
                        item,
                        str(exc),
                    )

                    return

                self.stats[
                    "total_retried"
                ] += 1

                # ------------------------------------------------
                # Exponential retry delay
                # ------------------------------------------------

                delay = min(
                    2 ** attempt,
                    30,
                )

                await asyncio.sleep(
                    delay
                )

        # Safety fallback
        await self._job_failed(
            item,
            "Unknown queue failure.",
        )

    # ============================================================
    # JOB COMPLETE
    # ============================================================

    async def _job_completed(
        self,
        item: QueueItem,
        result: Any,
    ):

        self.stats[
            "total_completed"
        ] += 1

        self._remove_running(
            item
        )

        logger.info(
            "Job completed: %s",
            item.job_id,
        )

        # --------------------------------------------------------
        # Completion callbacks
        # --------------------------------------------------------

        callback = self.processors.get(
            f"{item.job_type}:complete"
        )

        if callback:

            try:

                await callback(
                    result
                )

            except Exception:

                logger.exception(
                    "Completion callback failed for %s",
                    item.job_id,
                )

    # ============================================================
    # JOB FAILED
    # ============================================================

    async def _job_failed(
        self,
        item: QueueItem,
        error: str,
    ):

        self.stats[
            "total_failed"
        ] += 1

        self._remove_running(
            item
        )

        logger.error(
            "Job failed: %s - %s",
            item.job_id,
            error,
        )

        callback = self.processors.get(
            f"{item.job_type}:failed"
        )

        if callback:

            try:

                await callback(
                    {
                        "job_id": item.job_id,
                        "user_id": item.user_id,
                        "job_type": item.job_type,
                        "payload": item.payload,
                        "error": error,
                    }
                )

            except Exception:

                logger.exception(
                    "Failure callback failed for %s",
                    item.job_id,
                )

    # ============================================================
    # REMOVE RUNNING
    # ============================================================

    def _remove_running(
        self,
        item: QueueItem,
    ):

        self.running_jobs.pop(
            item.job_id,
            None,
        )

        current = self.running_users.get(
            item.user_id,
            0,
        )

        if current <= 1:

            self.running_users.pop(
                item.user_id,
                None,
            )

        else:

            self.running_users[
                item.user_id
            ] = current - 1

    # ============================================================
    # RETRY LIMIT
    # ============================================================

    @staticmethod
    def _get_retry_limit(
        job_type: str,
    ) -> int:

        if job_type == "test_upload":

            return 2

        if job_type == "test_extract":

            return 2

        return 1

    # ============================================================
    # MANUAL RETRY
    # ============================================================

    async def retry_job(
        self,
        old_job: Dict[str, Any],
    ) -> str:

        user_id = int(
            old_job[
                "user_id"
            ]
        )

        job_type = old_job[
            "job_type"
        ]

        payload = dict(
            old_job.get(
                "payload",
                {},
            )
        )

        payload[
            "retry_of"
        ] = old_job.get(
            "job_id"
        )

        priority = int(
            old_job.get(
                "priority",
                10,
            )
        )

        new_job_id = await self.add_job(
            user_id=user_id,
            job_type=job_type,
            payload=payload,
            priority=priority,
        )

        return new_job_id

    # ============================================================
    # CANCEL JOB
    # ============================================================

    async def cancel_job(
        self,
        job_id: str,
    ) -> bool:

        # --------------------------------------------------------
        # Running job cancel
        # --------------------------------------------------------

        item = self.running_jobs.get(
            job_id
        )

        if item:

            # Processor को cancellation event देना
            # architecture के next stage में supported होगा।
            logger.warning(
                "Cancel requested for running job: %s",
                job_id,
            )

            return False

        # --------------------------------------------------------
        # Queued job
        # --------------------------------------------------------

        async with self._queue_lock:

            found = False

            new_queue = []

            for queued in self._queue:

                if queued.job_id == job_id:

                    found = True

                    continue

                new_queue.append(
                    queued
                )

            if found:

                heapq.heapify(
                    new_queue
                )

                self._queue = (
                    new_queue
                )

        return found

    # ============================================================
    # PROGRESS
    # ============================================================

    async def progress(
        self,
        job_id: str,
        percentage: int,
        message: str,
    ):

        """
        Queue-level progress hook.

        Actual progress MongoDB में handler द्वारा save होगी।
        यहाँ event/log level पर भी information available रहती है।
        """

        percentage = max(
            0,
            min(
                100,
                int(
                    percentage
                ),
            ),
        )

        logger.info(
            "JOB_PROGRESS job=%s progress=%s%% message=%s",
            job_id,
            percentage,
            message,
        )

    # ============================================================
    # QUEUE STATUS
    # ============================================================

    async def get_status(
        self,
    ) -> Dict[str, Any]:

        async with self._queue_lock:

            queued = list(
                self._queue
            )

        priority_queued = sum(
            1
            for item in queued
            if item.priority >= 100
        )

        normal_queued = sum(
            1
            for item in queued
            if item.priority < 100
        )

        return {
            "queued": len(
                queued
            ),
            "priority_queued": priority_queued,
            "normal_queued": normal_queued,
            "running": len(
                self.running_jobs
            ),
            "workers": len(
                self.workers
            ),
            "max_workers": self.max_workers,
            "capacity": self.max_queue_size,
            "stopping": self.stopping,
            "stats": dict(
                self.stats
            ),
        }

    # ============================================================
    # SYNC STATUS
    # ============================================================

    def get_status_sync(
        self,
    ) -> Dict[str, Any]:

        priority_queued = sum(
            1
            for item in self._queue
            if item.priority >= 100
        )

        normal_queued = sum(
            1
            for item in self._queue
            if item.priority < 100
        )

        return {
            "queued": len(
                self._queue
            ),
            "priority_queued": priority_queued,
            "normal_queued": normal_queued,
            "running": len(
                self.running_jobs
            ),
            "workers": len(
                self.workers
            ),
            "max_workers": self.max_workers,
            "capacity": self.max_queue_size,
            "stopping": self.stopping,
            "stats": dict(
                self.stats
            ),
        }

    # ============================================================
    # QUEUE POSITION
    # ============================================================

    async def get_position(
        self,
        job_id: str,
    ) -> Optional[int]:

        async with self._queue_lock:

            ordered = sorted(
                self._queue
            )

            for index, item in enumerate(
                ordered,
                start=1,
            ):

                if item.job_id == job_id:

                    return index

        return None

    # ============================================================
    # USER RUNNING JOB COUNT
    # ============================================================

    def user_running_count(
        self,
        user_id: int,
    ) -> int:

        return self.running_users.get(
            int(user_id),
            0,
        )

    # ============================================================
    # USER QUEUE LIMIT
    # ============================================================

    async def can_user_queue(
        self,
        user_id: int,
        max_jobs: int = 3,
    ) -> bool:

        async with self._queue_lock:

            queued_for_user = sum(
                1
                for item in self._queue
                if item.user_id == int(user_id)
            )

            running_for_user = self.running_users.get(
                int(user_id),
                0,
            )

        return (
            queued_for_user
            + running_for_user
            < max_jobs
        )

    # ============================================================
    # CLEAR QUEUE
    # ============================================================

    async def clear_queue(
        self,
        keep_priority: bool = True,
    ) -> int:

        async with self._queue_lock:

            if keep_priority:

                old_length = len(
                    self._queue
                )

                self._queue = [
                    item
                    for item in self._queue
                    if item.priority >= 100
                ]

                heapq.heapify(
                    self._queue
                )

                return (
                    old_length
                    - len(
                        self._queue
                    )
                )

            count = len(
                self._queue
            )

            self._queue.clear()

            return count

    # ============================================================
    # ADMIN QUEUE RESET
    # ============================================================

    async def emergency_pause(
        self,
    ):

        """
        New jobs process नहीं होंगे,
        लेकिन running jobs को जबरदस्ती kill नहीं किया जाता।
        """

        self.stopping = True

        self._queue_event.set()

        logger.warning(
            "Queue emergency pause enabled."
        )

    async def resume(
        self,
    ):

        if self.started:

            return

        self.stopping = False

        await self.start()

        logger.info(
            "Queue resumed."
        )


# =================================================================
# SINGLE GLOBAL INSTANCE
# =================================================================

queue_manager = QueueManager(
    max_workers=3,
    max_queue_size=5000,
)

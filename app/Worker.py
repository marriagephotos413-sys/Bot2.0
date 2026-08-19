import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional


logger = logging.getLogger(
    "telegram-test-series-bot.worker"
)


# ============================================================
# JOB
# ============================================================

@dataclass
class WorkerJob:
    """
    Queue में process होने वाली एक job.
    """

    job_id: str
    user_id: int
    job_type: str

    callback: Callable[..., Awaitable[Any]]

    args: tuple = field(
        default_factory=tuple
    )

    kwargs: dict = field(
        default_factory=dict
    )

    priority: int = 10

    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    attempts: int = 0
    max_attempts: int = 3

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================
# WORKER
# ============================================================

class TestWorker:
    """
    Background worker.

    Priority:
        1 = highest
        10 = normal
        20 = low
    """

    def __init__(
        self,
        worker_id: int,
        concurrency: int = 1,
    ):

        self.worker_id = worker_id

        self.concurrency = max(
            1,
            int(concurrency),
        )

        self.queue: asyncio.PriorityQueue = (
            asyncio.PriorityQueue()
        )

        self.running = False

        self.tasks = []

        self._sequence = 0

        self.completed = 0
        self.failed = 0

    # ========================================================
    # START
    # ========================================================

    async def start(self):

        if self.running:
            return

        self.running = True

        logger.info(
            "Worker %s started.",
            self.worker_id,
        )

        for index in range(
            self.concurrency
        ):

            task = asyncio.create_task(
                self._worker_loop(
                    index
                )
            )

            self.tasks.append(
                task
            )

    # ========================================================
    # STOP
    # ========================================================

    async def stop(self):

        if not self.running:
            return

        self.running = False

        logger.info(
            "Stopping worker %s...",
            self.worker_id,
        )

        for task in self.tasks:

            task.cancel()

        if self.tasks:

            await asyncio.gather(
                *self.tasks,
                return_exceptions=True,
            )

        self.tasks.clear()

        logger.info(
            "Worker %s stopped.",
            self.worker_id,
        )

    # ========================================================
    # ADD JOB
    # ========================================================

    async def add_job(
        self,
        job: WorkerJob,
    ) -> bool:

        if not self.running:

            await self.start()

        self._sequence += 1

        await self.queue.put(
            (
                job.priority,
                self._sequence,
                job,
            )
        )

        logger.info(
            "Job %s added to worker %s.",
            job.job_id,
            self.worker_id,
        )

        return True

    # ========================================================
    # WORKER LOOP
    # ========================================================

    async def _worker_loop(
        self,
        slot: int,
    ):

        logger.info(
            "Worker %s slot %s ready.",
            self.worker_id,
            slot,
        )

        while self.running:

            try:

                item = await self.queue.get()

                _, _, job = item

                try:

                    await self._process_job(
                        job
                    )

                finally:

                    self.queue.task_done()

            except asyncio.CancelledError:

                break

            except Exception:

                logger.exception(
                    "Unexpected worker error."
                )

                await asyncio.sleep(
                    1
                )

    # ========================================================
    # PROCESS JOB
    # ========================================================

    async def _process_job(
        self,
        job: WorkerJob,
    ):

        job.attempts += 1

        logger.info(
            (
                "Processing job=%s "
                "type=%s "
                "user=%s "
                "attempt=%s"
            ),
            job.job_id,
            job.job_type,
            job.user_id,
            job.attempts,
        )

        try:

            result = await job.callback(
                *job.args,
                **job.kwargs,
            )

            self.completed += 1

            logger.info(
                "Job %s completed.",
                job.job_id,
            )

            return result

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            logger.error(
                (
                    "Job %s failed: %s"
                ),
                job.job_id,
                exc,
            )

            if (
                job.attempts
                < job.max_attempts
            ):

                logger.warning(
                    (
                        "Retrying job %s "
                        "(%s/%s)"
                    ),
                    job.job_id,
                    job.attempts,
                    job.max_attempts,
                )

                await asyncio.sleep(
                    min(
                        2 ** job.attempts,
                        30,
                    )
                )

                self._sequence += 1

                await self.queue.put(
                    (
                        job.priority,
                        self._sequence,
                        job,
                    )
                )

                return None

            self.failed += 1

            logger.error(
                (
                    "Job %s permanently "
                    "failed."
                ),
                job.job_id,
            )

            await self._handle_failure(
                job,
                exc,
            )

            return None

    # ========================================================
    # FAILURE
    # ========================================================

    async def _handle_failure(
        self,
        job: WorkerJob,
        error: Exception,
    ):

        callback = job.metadata.get(
            "on_failure"
        )

        if not callback:
            return

        try:

            if asyncio.iscoroutinefunction(
                callback
            ):

                await callback(
                    job,
                    error,
                )

            else:

                callback(
                    job,
                    error,
                )

        except Exception:

            logger.error(
                (
                    "Failure callback "
                    "failed for job %s"
                ),
                job.job_id,
            )

            logger.debug(
                traceback.format_exc()
            )

    # ========================================================
    # WAIT
    # ========================================================

    async def wait_until_empty(
        self,
        timeout: Optional[float] = None,
    ):

        if timeout is None:

            await self.queue.join()

            return True

        try:

            await asyncio.wait_for(
                self.queue.join(),
                timeout=timeout,
            )

            return True

        except asyncio.TimeoutError:

            return False

    # ========================================================
    # STATS
    # ========================================================

    def stats(self) -> Dict[str, Any]:

        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "queue_size": self.queue.qsize(),
            "completed": self.completed,
            "failed": self.failed,
            "concurrency": self.concurrency,
        }


# ============================================================
# WORKER POOL
# ============================================================

class WorkerPool:

    def __init__(
        self,
        worker_count: int = 4,
        concurrency_per_worker: int = 1,
    ):

        self.worker_count = max(
            1,
            int(worker_count),
        )

        self.concurrency_per_worker = max(
            1,
            int(concurrency_per_worker),
        )

        self.workers = [
            TestWorker(
                worker_id=index + 1,
                concurrency=self.concurrency_per_worker,
            )
            for index in range(
                self.worker_count
            )
        ]

        self.running = False

        self._next_worker = 0

    # ========================================================
    # START
    # ========================================================

    async def start(self):

        if self.running:
            return

        self.running = True

        await asyncio.gather(
            *[
                worker.start()
                for worker in self.workers
            ]
        )

        logger.info(
            "Worker pool started with %s workers.",
            self.worker_count,
        )

    # ========================================================
    # STOP
    # ========================================================

    async def stop(self):

        if not self.running:
            return

        self.running = False

        await asyncio.gather(
            *[
                worker.stop()
                for worker in self.workers
            ],
            return_exceptions=True,
        )

        logger.info(
            "Worker pool stopped."
        )

    # ========================================================
    # SELECT WORKER
    # ========================================================

    def _select_worker(
        self,
    ) -> TestWorker:

        # सबसे छोटी queue वाला worker चुनें।
        #
        # इससे load distribution बेहतर रहता है।

        worker = min(
            self.workers,
            key=lambda item: item.queue.qsize(),
        )

        return worker

    # ========================================================
    # SUBMIT
    # ========================================================

    async def submit(
        self,
        job: WorkerJob,
    ) -> bool:

        if not self.running:

            await self.start()

        worker = self._select_worker()

        return await worker.add_job(
            job
        )

    # ========================================================
    # WAIT
    # ========================================================

    async def wait(
        self,
        timeout: Optional[float] = None,
    ) -> bool:

        results = await asyncio.gather(
            *[
                worker.wait_until_empty(
                    timeout
                )
                for worker in self.workers
            ]
        )

        return all(
            results
        )

    # ========================================================
    # STATS
    # ========================================================

    def stats(self) -> Dict[str, Any]:

        workers = [
            worker.stats()
            for worker in self.workers
        ]

        return {
            "running": self.running,
            "workers": workers,
            "total_queue": sum(
                worker["queue_size"]
                for worker in workers
            ),
            "completed": sum(
                worker["completed"]
                for worker in workers
            ),
            "failed": sum(
                worker["failed"]
                for worker in workers
            ),
        }


# ============================================================
# GLOBAL POOL
# ============================================================

try:

    from app.config import CONFIG

    _worker_count = (
        CONFIG.WORKER_COUNT
    )

except Exception:

    _worker_count = 4


worker_pool = WorkerPool(
    worker_count=_worker_count,
    concurrency_per_worker=1,
)


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

async def submit_job(
    job_id: str,
    user_id: int,
    job_type: str,
    callback: Callable[..., Awaitable[Any]],
    *args,
    priority: int = 10,
    max_attempts: int = 3,
    metadata: Optional[
        Dict[str, Any]
    ] = None,
    **kwargs,
):

    job = WorkerJob(
        job_id=job_id,
        user_id=user_id,
        job_type=job_type,
        callback=callback,
        args=args,
        kwargs=kwargs,
        priority=priority,
        max_attempts=max_attempts,
        metadata=metadata or {},
    )

    await worker_pool.submit(
        job
    )

    return job


__all__ = [
    "WorkerJob",
    "TestWorker",
    "WorkerPool",
    "worker_pool",
    "submit_job",
]

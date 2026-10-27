"""One running LLM generation per student.

Open edX does not propagate a browser disconnect to TutorIA: when a student
closes the chat or sends a new message, the previous generation would keep
running in Ollama and queue every later request behind it. The provider
endpoint therefore runs each generation as a task registered here. A new
request for the same student cancels the previous task and waits for it to
finish its cleanup (closing the LLM stream and persisting the interrupted
turn) before the new turn is prepared, so the history keeps its order.

In-process only: correct for a single uvicorn worker. Several workers or
backend replicas would need a shared mechanism instead (e.g. a per-student
lock in PostgreSQL or Redis plus a cancellation signal that the worker
running the old generation listens to).
"""
import asyncio
import logging
from collections.abc import Callable, Coroutine
from functools import partial
from typing import Any

logger = logging.getLogger(__name__)

# How long a new request waits for the previous generation's cleanup.
CANCEL_TIMEOUT_SECONDS = 10.0


class GenerationRegistry:
    def __init__(self) -> None:
        self._tasks: dict[int, asyncio.Task] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    async def start(
        self, student_id: int, generation: Callable[[], Coroutine[Any, Any, None]]
    ) -> asyncio.Task:
        """Cancel the student's running generation, wait for its cleanup, then
        run `generation()` as the student's new task."""
        lock = self._locks.setdefault(student_id, asyncio.Lock())
        async with lock:
            previous = self._tasks.get(student_id)
            if previous is not None and not previous.done():
                logger.info("Cancelling the previous generation of student %s", student_id)
                previous.cancel()
                done, _ = await asyncio.wait({previous}, timeout=CANCEL_TIMEOUT_SECONDS)
                if not done:
                    logger.warning(
                        "Previous generation of student %s did not finish its cleanup "
                        "within %.0fs; starting the new turn anyway",
                        student_id,
                        CANCEL_TIMEOUT_SECONDS,
                    )

            task = asyncio.create_task(generation())
            self._tasks[student_id] = task
            task.add_done_callback(partial(self._forget, student_id))
            return task

    def _forget(self, student_id: int, task: asyncio.Task) -> None:
        if self._tasks.get(student_id) is task:
            del self._tasks[student_id]


generations = GenerationRegistry()

"""Bounded background warm-up for a scale-to-zero retriever endpoint."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)


class RetrieverWarmup:
    """Keep a synchronous-path retriever warm without blocking App startup."""

    def __init__(
        self,
        search: Callable[..., object],
        *,
        interval_seconds: float = 900.0,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("Warm-up interval must be greater than zero")
        self._search = search
        self._interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def warm_once(self) -> bool:
        """Run one harmless lookup and report whether the endpoint responded."""
        try:
            self._search("order shipping return policy", top_k=1)
        except Exception as exc:
            logger.warning("Retriever warm-up failed: %s", exc)
            return False
        logger.info("Retriever warm-up completed")
        return True

    def start(self) -> None:
        """Start one daemon worker; repeated startup hooks are idempotent."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="retriever-warmup",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout_seconds: float = 2.0) -> None:
        """Signal shutdown without extending the App's 15-second deadline."""
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=max(0.0, timeout_seconds))

    def _run(self) -> None:
        while not self._stop.is_set():
            self.warm_once()
            if self._stop.wait(self._interval_seconds):
                break

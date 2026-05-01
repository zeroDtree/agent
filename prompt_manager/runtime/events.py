from __future__ import annotations

import datetime as dt
import time
from contextlib import contextmanager
from typing import Generator

from ..types import LoreBook, RuntimeContext, RuntimeEvent, Stage


class RuntimeEventSink:
    """Emits structured runtime events when log_level is not off."""

    def __init__(self, lorebook: LoreBook):
        self._lorebook = lorebook

    def event(
        self,
        events: list[RuntimeEvent],
        context: RuntimeContext,
        entry_id: str | None,
        stage: Stage,
        action: str,
        reason: str,
        metrics: dict | None = None,
    ) -> None:
        if self._lorebook.runtime.log_level == "off":
            return
        events.append(
            RuntimeEvent(
                ts=dt.datetime.now(dt.UTC).isoformat(),
                request_id=context.request_id,
                session_id=context.session_id,
                lorebook_id=self._lorebook.id,
                entry_id=entry_id,
                stage=stage,
                action=action,
                reason=reason,
                metrics=metrics or {},
            )
        )

    def stage_started(
        self,
        events: list[RuntimeEvent],
        context: RuntimeContext,
        stage: Stage,
        reason: str,
    ) -> float:
        """Emit stage `started` and return a perf_counter value for `stage_completed`."""
        self.event(events, context, None, stage, "started", reason)
        return time.perf_counter()

    def stage_completed(
        self,
        events: list[RuntimeEvent],
        context: RuntimeContext,
        stage: Stage,
        reason: str,
        started_at: float,
        metrics: dict | None = None,
    ) -> None:
        """Emit stage `completed` with `duration_ms` plus optional counters in metrics."""
        payload = dict(metrics or {})
        payload["duration_ms"] = round((time.perf_counter() - started_at) * 1000, 3)
        self.event(events, context, None, stage, "completed", reason, payload)

    @contextmanager
    def timed_stage(
        self,
        events: list[RuntimeEvent],
        context: RuntimeContext,
        stage: Stage,
        start_reason: str,
        end_reason: str,
    ) -> Generator[dict, None, None]:
        """Context manager that wraps a pipeline stage with start/completed events and timing.

        Yields a metrics dict the caller can populate; its contents are merged into the
        completed event automatically.

            with sink.timed_stage(events, ctx, "match", "match_started", "match_completed") as m:
                matched = run_match(...)
                m["matched_entries"] = len(matched)
        """
        metrics: dict = {}
        t0 = self.stage_started(events, context, stage, start_reason)
        try:
            yield metrics
        finally:
            self.stage_completed(events, context, stage, end_reason, t0, metrics)

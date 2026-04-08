from __future__ import annotations

import datetime as dt
import time

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

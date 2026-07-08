from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..types import RuntimeEvent


class LoreBookEventLogger:
    def __init__(self, log_path: str | Path = "logs/lorebook-events.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def append_events(self, events: list[RuntimeEvent]) -> None:
        if not events:
            return
        with self.log_path.open("a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

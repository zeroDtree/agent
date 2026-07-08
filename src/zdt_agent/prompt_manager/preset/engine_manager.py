from __future__ import annotations

from pathlib import Path

from ..runtime import LoreBookRuntimeEngine
from ..utils.builder import build_lorebook
from ..utils.loader import load_lorebook


class LoreBookEngineManager:
    """Caches lorebook runtime engines per lorebook id under a root directory."""

    def __init__(self, lorebook_root: Path) -> None:
        self._lorebook_root = lorebook_root
        self._engines: dict[str, LoreBookRuntimeEngine] = {}

    def clear(self) -> None:
        self._engines.clear()

    def get_engine(self, lorebook_id: str) -> LoreBookRuntimeEngine:
        lorebook_source = self._lorebook_root / lorebook_id
        lorebook_output = lorebook_source / "lorebook.json"
        entries_dir = lorebook_source / "entries"
        has_md_sources = entries_dir.is_dir() and any(entries_dir.glob("*.md"))

        if has_md_sources:
            self._engines.pop(lorebook_id, None)
            build_lorebook(source=lorebook_source, output=lorebook_output)
            lorebook = load_lorebook(lorebook_output)
            engine = LoreBookRuntimeEngine(lorebook)
            self._engines[lorebook_id] = engine
            return engine

        if not lorebook_output.exists():
            raise FileNotFoundError(
                f"Missing lorebook.json for {lorebook_id!r} under {self._lorebook_root} "
                "(no entries/*.md sources to build from)."
            )

        cached = self._engines.get(lorebook_id)
        if cached is not None:
            return cached

        lorebook = load_lorebook(lorebook_output)
        engine = LoreBookRuntimeEngine(lorebook)
        self._engines[lorebook_id] = engine
        return engine

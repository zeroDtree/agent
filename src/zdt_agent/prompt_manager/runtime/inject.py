from __future__ import annotations

from ..types import LoreEntry, RuntimeContext, TruncateMode
from .helpers import clip_text_to_token_budget, token_count


class LoreInjector:
    """Inject stage helper: per-entry body preparation."""

    def __init__(self) -> None:
        pass

    def prepare_entry_body(self, entry: LoreEntry, context: RuntimeContext) -> tuple[str | None, int, bool]:
        """Return (body, token_count, truncated) or (None, raw_token_count, False) if dropped."""
        raw = entry.content
        raw_tokens = token_count(raw)
        max_tok = entry.resolved.budget.max_tokens
        truncate_mode = entry.resolved.budget.truncate

        if raw_tokens <= max_tok:
            return raw, raw_tokens, False
        if truncate_mode == TruncateMode.NONE:
            return None, raw_tokens, False

        clipped = clip_text_to_token_budget(raw, max_tok, truncate_mode)
        return clipped, token_count(clipped), True

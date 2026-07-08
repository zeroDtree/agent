from __future__ import annotations

import hashlib

from ..types import TruncateMode


def token_count(text: str) -> int:
    return max(1, len(text.split()))


def stable_int_seed(*parts: str) -> int:
    """Deterministic RNG seed across processes (unlike built-in hash())."""
    joined = "\0".join(parts)
    digest = hashlib.sha256(joined.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**63)


def clip_text_to_token_budget(text: str, max_tokens: int, mode: TruncateMode | str) -> str:
    """Trim whitespace tokens to at most max_tokens; mode is head|tail|none."""
    if max_tokens <= 0:
        return ""
    words = text.split()
    if len(words) <= max_tokens:
        return text
    if mode == TruncateMode.HEAD:
        return " ".join(words[:max_tokens])
    if mode == TruncateMode.TAIL:
        return " ".join(words[-max_tokens:])
    return text

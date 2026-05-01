from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .conversation import MessageType


class SourceScope(StrEnum):
    """Which context bucket an entry or lorebook participates in (multi-source merge)."""

    GLOBAL = "global"
    CHARACTER = "character"
    PERSONA = "persona"
    CHAT = "chat"


class OverflowPolicy(StrEnum):
    """What to do when total injected content exceeds the lorebook budget."""

    DROP_LOW_PRIORITY = "drop_low_priority"
    TRUNCATE_TAIL = "truncate_tail"
    TRUNCATE_HEAD = "truncate_head"


class TruncateMode(StrEnum):
    """How to trim entry content that exceeds its per-entry token budget."""

    HEAD = "head"
    TAIL = "tail"
    NONE = "none"


class LogLevel(StrEnum):
    """Verbosity of structured lorebook events."""

    OFF = "off"
    NORMAL = "normal"
    DEBUG = "debug"


class RandomSeedStrategy(StrEnum):
    """How to seed probability gates."""

    SESSION_STABLE = "session_stable"
    REQUEST_RANDOM = "request_random"


class MergeMode(StrEnum):
    """High-level merge strategy for multi-source lorebook candidates."""

    GLOBAL_SORTED_MERGE = "global_sorted_merge"
    CHARACTER_FIRST = "character_first"


class InjectionPositionType(StrEnum):
    """Canonical placement modes for matched lore content.

    Six static anchors place content immediately before or after the core,
    character, or persona preset segment.  The special value DEPTH routes
    content into the depth preset segment (emitted only when that segment is
    enabled in the host preset configuration).
    """

    BEFORE_CORE = "before_core"
    AFTER_CORE = "after_core"
    BEFORE_CHARACTER = "before_character"
    AFTER_CHARACTER = "after_character"
    BEFORE_PERSONA = "before_persona"
    AFTER_PERSONA = "after_persona"
    DEPTH = "depth"


@dataclass(slots=True)
class EntryTriggers:
    """How an entry is matched against scanned text (keywords and/or regex)."""

    keywords: list[str] = field(default_factory=list)
    regex: list[str] = field(default_factory=list)
    case_sensitive: bool = False
    whole_word: bool = False


@dataclass(slots=True)
class EntryFilters:
    """Reserved for future post-match filter fields; filter stage still applies delay, cooldown, probability."""


@dataclass(slots=True)
class EntryInjection:
    """Where and how a matched entry is materialized in prompt assembly."""

    position_type: InjectionPositionType = InjectionPositionType.AFTER_CHARACTER
    order: int = 0
    #: Message role for the injected segment; None defers to the host default (system).
    message_type: MessageType | None = None
    #: Layer offset within the depth segment (only used when position_type is DEPTH).
    #: depth=0 is closest to the most recent message; higher values are further away.
    #: Within the same depth, higher order places the entry closer to the most recent message.
    #: None for all other position types.
    depth: int | None = None


@dataclass(slots=True)
class EntryAdvanced:
    """Advanced per-entry controls: groups, probability, recursion, and timing."""

    inclusion_group: str | None = None
    group_scoring: bool = False
    probability: float = 1.0
    recursive: bool = False
    max_recursion_depth: int = 0
    sticky_turns: int = 0
    cooldown_turns: int = 0
    delay_turns: int = 0


@dataclass(slots=True)
class EntryBudget:
    """Per-entry token budget and truncation when over limit."""

    max_tokens: int = 300
    truncate: TruncateMode = TruncateMode.TAIL


@dataclass(slots=True)
class EntryResolved:
    """Normalized runtime parameters for one entry (builder fallbacks + front matter)."""

    triggers: EntryTriggers
    filters: EntryFilters
    injection: EntryInjection
    advanced: EntryAdvanced
    budget: EntryBudget


@dataclass(slots=True)
class LoreEntry:
    """One lorebook entry: identity, source path, body text, and resolved settings."""

    id: str
    path: str
    enabled: bool
    content: str
    resolved: EntryResolved


@dataclass(slots=True)
class LoreBookBudget:
    """Total token budget for the whole lorebook and overflow handling mode."""

    max_tokens: int = 2000
    overflow_policy: OverflowPolicy = OverflowPolicy.DROP_LOW_PRIORITY


@dataclass(slots=True)
class MergePolicy:
    """How multiple sources or entries are ordered when strategies conflict."""

    mode: MergeMode = MergeMode.GLOBAL_SORTED_MERGE
    priority: list[SourceScope] = field(
        default_factory=lambda: [
            SourceScope.CHARACTER,
            SourceScope.PERSONA,
            SourceScope.CHAT,
            SourceScope.GLOBAL,
        ]
    )


@dataclass(slots=True)
class RuntimeConfig:
    """Engine knobs: recursion cap, randomness for probability gates, log verbosity."""

    max_recursion_steps: int = 3
    random_seed_strategy: RandomSeedStrategy = RandomSeedStrategy.SESSION_STABLE
    log_level: LogLevel = LogLevel.NORMAL


@dataclass(slots=True)
class LoreBook:
    """Aggregated book: metadata, budgets, merge policy, and all entries."""

    id: str
    name: str
    enabled: bool
    description: str
    budget: LoreBookBudget
    entries: list[LoreEntry]
    source_scope: list[SourceScope] = field(default_factory=lambda: [SourceScope.GLOBAL])
    merge_policy: MergePolicy = field(default_factory=MergePolicy)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)

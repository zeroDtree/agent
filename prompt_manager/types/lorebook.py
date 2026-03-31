"""Lorebook schema and runtime-facing type definitions.

This module defines the normalized data shapes used across build and runtime
stages: trigger matching, filtering, sorting, and final injection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, TypeAlias

from .common import _md

if TYPE_CHECKING:
    from .conversation import MessageType

# Which context bucket an entry or lorebook participates in (multi-source merge).
SourceScope = Literal["global", "character", "persona", "chat"]
# Pipeline stage for structured logging (scan → match → filter → expand → sort → inject).
Stage = Literal["scan", "match", "filter", "expand", "sort", "inject"]


@dataclass(slots=True)
class EntryTriggers:
    """How an entry is matched against scanned text (keywords and/or regex)."""

    keywords: list[str] = field(
        default_factory=list,
        metadata=_md(
            "Substring or whole-word keyword triggers. Any match can activate the entry "
            "as a candidate, subject to `case_sensitive` and `whole_word`."
        ),
    )
    regex: list[str] = field(
        default_factory=list,
        metadata=_md(
            "Additional `re`-compatible patterns evaluated against the combined scan text. "
            "Invalid patterns should fail at build time."
        ),
    )
    case_sensitive: bool = field(
        default=False,
        metadata=_md("If True, keyword and regex matching is case-sensitive."),
    )
    whole_word: bool = field(
        default=False,
        metadata=_md(
            "If True, keywords use word-boundary matching to reduce accidental substring hits. "
            "Less reliable for languages without clear word boundaries."
        ),
    )


@dataclass(slots=True)
class EntryFilters:
    """Post-match gates: role constraints."""

    role_allowlist: list[str] = field(
        default_factory=list,
        metadata=_md(
            "If non-empty, the entry only passes when `RuntimeContext.role` is in this list. "
            "Empty means no role allowlist restriction."
        ),
    )
    role_denylist: list[str] = field(
        default_factory=list,
        metadata=_md("If the current role is in this list, the entry is dropped after match."),
    )


class InjectionPositionType(StrEnum):
    """Canonical placement modes for matched lore content."""

    BEFORE_CHAR_DEFS = "before_char_defs"
    AFTER_CHAR_DEFS = "after_char_defs"
    DEPTH = "depth"
    OUTLET = "outlet"


@dataclass(slots=True)
class EntryInjection:
    """Where and how a matched entry is materialized in prompt assembly."""

    position: InjectionPositionType = field(
        default=InjectionPositionType.AFTER_CHAR_DEFS,
        metadata=_md(
            "Placement mode for this entry. Runtime output is often merged into one string unless the host "
            "keeps structured segments by position."
        ),
    )
    order: int = field(
        default=0,
        metadata=_md(
            "Relative ordering among entries targeting the same position. Interpretation of "
            "larger vs smaller values is controlled by `runtime.injection_order` (small_first vs "
            "great_first) for sort order and inclusion-group tie-breaks."
        ),
    )
    message_type: "MessageType | None" = field(
        default=None,
        metadata=_md(
            "Message role for the injected synthetic segment when the host models lore as messages. "
            "None means host-default role handling."
        ),
    )
    outlet: str | None = field(
        default=None,
        metadata=_md(
            "If set, content is buffered under this outlet name rather than injected inline. "
            "The host must explicitly reference the outlet to materialize it; None means direct injection."
        ),
    )
    depth: int | None = field(
        default=None,
        metadata=_md(
            "Depth index for `position_type=DEPTH` (0 = prompt bottom in host-defined ordering). "
            "Should be None for non-depth positions."
        ),
    )


@dataclass(slots=True)
class EntryAdvanced:
    """Optional behavior: grouping, probability, recursion, and turn-based state."""

    inclusion_group: str | None = field(
        default=None,
        metadata=_md(
            "Mutual exclusion group name. When multiple entries in the same group match, "
            "the engine typically keeps one winner per policy."
        ),
    )
    group_scoring: bool = field(
        default=False,
        metadata=_md(
            "If True, tie-breaking within an inclusion group may use match strength (e.g. keyword hit count)."
        ),
    )
    probability: float = field(
        default=1.0,
        metadata=_md(
            "Post-filter stochastic gate in [0, 1]. Values below 1.0 may drop the entry even when matched. "
            "Should not be used for safety-critical rules."
        ),
    )
    recursive: bool = field(
        default=False,
        metadata=_md(
            "If True, matched entry content may be scanned again to activate other entries, "
            "subject to global recursion limits."
        ),
    )
    max_recursion_depth: int = field(
        default=0,
        metadata=_md(
            "Maximum depth for this entry in recursive activation chains. Zero usually means rely on the "
            "global runtime cap without an entry-specific override."
        ),
    )
    sticky_turns: int = field(
        default=0,
        metadata=_md(
            "After a successful match or injection, keep the entry eligible for this many subsequent "
            "turn indices without requiring a fresh keyword hit."
        ),
    )
    cooldown_turns: int = field(
        default=0,
        metadata=_md("After activation, block re-triggering this entry for this many future turn indices."),
    )
    delay_turns: int = field(
        default=0,
        metadata=_md("Do not allow this entry to trigger until `RuntimeContext.turn_index` reaches this threshold."),
    )


@dataclass(slots=True)
class EntryBudget:
    """Per-entry token budget and truncation when over limit."""

    max_tokens: int = field(
        default=300,
        metadata=_md(
            "Soft ceiling for this entry's body when counting tokens (engine-defined tokenizer). "
            "Used before lorebook-level budget enforcement."
        ),
    )
    truncate: Literal["head", "tail", "none"] = field(
        default="tail",
        metadata=_md(
            "If content exceeds `max_tokens`, whether to keep the start (`head`), end (`tail`), "
            "or not truncate (`none`)."
        ),
    )


@dataclass(slots=True)
class EntryResolved:
    """Normalized runtime parameters for one entry (merged defaults + front matter)."""

    triggers: EntryTriggers = field(
        metadata=_md("Resolved trigger configuration after merging book defaults and entry YAML."),
    )
    filters: EntryFilters = field(
        metadata=_md("Resolved post-match filter configuration (currently role-based constraints)."),
    )
    injection: EntryInjection = field(
        metadata=_md("Resolved injection target, ordering, and optional outlet."),
    )
    advanced: EntryAdvanced = field(
        metadata=_md("Resolved advanced controls: groups, probability, recursion, timing."),
    )
    budget: EntryBudget = field(
        metadata=_md("Resolved per-entry budget and truncation policy."),
    )


@dataclass(slots=True)
class LoreEntry:
    """One lorebook entry: identity, source path, body text, and resolved settings."""

    id: str = field(
        metadata=_md(
            "Stable kebab-case identifier, unique within the lorebook. Must match the source "
            "`entries/<id>.md` stem when using the standard layout."
        ),
    )
    path: str = field(
        metadata=_md(
            "Repository-relative path to the source Markdown file (e.g. `entries/foo.md`). "
            "Used for traceability and rebuilds."
        ),
    )
    enabled: bool = field(
        metadata=_md("Final enabled flag after merging book-level overrides. False entries are skipped entirely."),
    )
    content: str = field(
        metadata=_md(
            "Markdown body text after the closing front matter delimiter; this is what the runtime "
            "injects or routes to an outlet."
        ),
    )
    resolved: EntryResolved = field(
        metadata=_md("Fully expanded settings used by the engine without re-parsing Markdown."),
    )


@dataclass(slots=True)
class LorebookBudget:
    """Total token budget for the whole lorebook and overflow handling mode."""

    max_tokens: int = field(
        default=2000,
        metadata=_md(
            "Upper bound on total injected lorebook content for one activation, in token units defined by the engine."
        ),
    )
    overflow_policy: Literal["drop_low_priority", "truncate_tail", "truncate_head"] = field(
        default="drop_low_priority",
        metadata=_md(
            "When the sum of selected entries exceeds `max_tokens`: drop entries last in the "
            "injection sort order (see `runtime.injection_order`), or truncate merged text from the tail or head. "
            "This policy applies after candidate selection and ordering."
        ),
    )


@dataclass(slots=True)
class LorebookDefaults:
    """Book-level defaults applied when an entry omits a field."""

    position: InjectionPositionType = field(
        default=InjectionPositionType.AFTER_CHAR_DEFS,
        metadata=_md("Default injection position type for entries that omit `injection.position`."),
    )
    probability: float = field(
        default=1.0,
        metadata=_md("Default probability for entries that omit `advanced.probability`."),
    )
    case_sensitive: bool = field(
        default=False,
        metadata=_md("Default case sensitivity for triggers when not specified on the entry."),
    )


@dataclass(slots=True)
class MergePolicy:
    """How multiple sources or entries are ordered when strategies conflict."""

    mode: Literal["global_sorted_merge", "character_first"] = field(
        default="global_sorted_merge",
        metadata=_md(
            "High-level merge strategy: sort all candidates together, or prioritize character-scoped "
            "entries before others."
        ),
    )
    priority: list[SourceScope] = field(
        default_factory=lambda: ["character", "persona", "chat", "global"],
        metadata=_md(
            "When ties occur, earlier entries in this list win for source scope precedence. "
            "This precedence should align with how `source_scope` is populated by the host."
        ),
    )


@dataclass(slots=True)
class RuntimeConfig:
    """Engine knobs: recursion cap, randomness for probability gates, log verbosity."""

    max_recursion_steps: int = field(
        default=3,
        metadata=_md(
            "Global cap on recursive activation waves across one engine run, preventing unbounded expansion "
            "even when entries allow recursion."
        ),
    )
    random_seed_strategy: Literal["session_stable", "request_random"] = field(
        default="session_stable",
        metadata=_md(
            "How to seed probability gates: stable per session for reproducibility, or random per request "
            "for higher variation."
        ),
    )
    log_level: Literal["off", "normal", "debug"] = field(
        default="normal",
        metadata=_md("Verbosity of structured lorebook events written by the engine or host."),
    )
    injection_order: Literal["small_first", "great_first"] = field(
        default="small_first",
        metadata=_md(
            "How to sort by `injection.order` before inject: ascending (smaller order first) or "
            "descending (larger order first). Affects `drop_low_priority` drop order and inclusion-group "
            "ties when match scores are equal."
        ),
    )


@dataclass(slots=True)
class Lorebook:
    """Aggregated book: metadata, budgets, merge policy, and all entries."""

    id: str = field(
        metadata=_md("Unique lorebook identifier, usually matching the directory name (e.g. `coding-default`)."),
    )
    name: str = field(
        metadata=_md("Human-readable title for UIs and logs."),
    )
    enabled: bool = field(
        metadata=_md("Master switch: when False, the engine skips the entire book."),
    )
    description: str = field(
        metadata=_md("Free-text summary of the book's purpose."),
    )
    merge_strategy: Literal["global_sorted_merge", "character_first"] = field(
        metadata=_md(
            "Book-level merge strategy. It should remain semantically consistent with `merge_policy.mode` "
            "to avoid contradictory ordering expectations."
        ),
    )
    budget: LorebookBudget = field(
        metadata=_md("Aggregate token budget and overflow behavior for this book."),
    )
    defaults: LorebookDefaults = field(
        metadata=_md("Default trigger and injection values merged into each entry at build time."),
    )
    entries: list[LoreEntry] = field(
        metadata=_md("All compiled entries, typically sorted by id for deterministic builds."),
    )
    source_scope: list[SourceScope] = field(
        default_factory=lambda: ["global"],
        metadata=_md("Which logical sources this book participates in when the host merges multiple books."),
    )
    merge_policy: MergePolicy = field(
        default_factory=MergePolicy,
        metadata=_md("Detailed ordering rules when multiple sources contribute candidates."),
    )
    runtime: RuntimeConfig = field(
        default_factory=RuntimeConfig,
        metadata=_md("Engine-level limits and logging tied to this book."),
    )


# Doc parity name for World Info / LoreBook; identical to `Lorebook`.
LoreBook: TypeAlias = Lorebook

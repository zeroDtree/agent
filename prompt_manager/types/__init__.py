"""Typed data models for conversation primitives, lorebook build output, and runtime activation.

Split across ``conversation``, ``lorebook``, and ``runtime`` modules. Re-exported here for stable
``prompt_manager.types`` imports.

Conversation-layer types (`Message`, `Preset`, `Chat`, `PersonaMessages`, `CharacterCard`, `Persona`) model the
prompt organization described in project docs. Lorebook types mirror the `lorebook.json` shape
(after `builder`) and the inputs/outputs of `LorebookRuntimeEngine`, aligned with
`schemas/lorebook.schema.json`.

Field documentation is attached via ``dataclasses.field(metadata={"description": ...})`` for
introspection and tooling.
"""

from __future__ import annotations

from .conversation import CharacterCard, Chat, Message, MessageType, Persona, PersonaMessages, Preset
from .lorebook import (
    EntryAdvanced,
    EntryBudget,
    EntryFilters,
    EntryInjection,
    EntryResolved,
    EntryTriggers,
    LoreBook,
    Lorebook,
    LorebookBudget,
    LorebookDefaults,
    LoreEntry,
    MergePolicy,
    RuntimeConfig,
    SourceScope,
    Stage,
)
from .runtime import RuntimeContext, RuntimeEvent, RuntimeResult

__all__ = [
    "CharacterCard",
    "Chat",
    "EntryAdvanced",
    "EntryBudget",
    "EntryFilters",
    "EntryInjection",
    "EntryResolved",
    "EntryTriggers",
    "LoreBook",
    "LoreEntry",
    "Lorebook",
    "LorebookBudget",
    "LorebookDefaults",
    "MergePolicy",
    "Message",
    "MessageType",
    "Persona",
    "PersonaMessages",
    "Preset",
    "RuntimeConfig",
    "RuntimeContext",
    "RuntimeEvent",
    "RuntimeResult",
    "SourceScope",
    "Stage",
]

"""Prompt manager package for lorebook build and runtime injection."""

from .builder import build_lorebook
from .loader import load_lorebook
from .runtime import LorebookRuntimeEngine, RuntimeContext, RuntimeResult
from .types import CharacterCard, Chat, LoreBook, Message, MessageType, Persona, PersonaMessages, Preset

__all__ = [
    "build_lorebook",
    "load_lorebook",
    "CharacterCard",
    "Chat",
    "LorebookRuntimeEngine",
    "LoreBook",
    "Message",
    "MessageType",
    "Persona",
    "PersonaMessages",
    "Preset",
    "RuntimeContext",
    "RuntimeResult",
]

"""Prompt manager package for lorebook build and runtime injection."""

from .runtime import LoreBookRuntimeEngine, RuntimeContext, RuntimeResult
from .types import CharacterCard, Chat, LoreBook, Message, MessageType, Persona, PersonaMessages, Preset
from .utils.builder import build_lorebook
from .utils.loader import load_lorebook

__all__ = [
    "build_lorebook",
    "load_lorebook",
    "CharacterCard",
    "Chat",
    "LoreBookRuntimeEngine",
    "LoreBook",
    "Message",
    "MessageType",
    "Persona",
    "PersonaMessages",
    "Preset",
    "RuntimeContext",
    "RuntimeResult",
]

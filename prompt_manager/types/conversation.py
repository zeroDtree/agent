"""Conversation-layer types: messages, presets, character card, persona."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeAlias


class MessageType(StrEnum):
    """Role of a chat message (OpenAI-style string values)."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(slots=True)
class Message:
    """Smallest interaction unit toward the model; maps to common API roles."""

    id: str
    name: str
    role: MessageType
    content: str
    tool_call_id: str | None = None


Preset: TypeAlias = list[Message]
Chat: TypeAlias = list[Message]
PersonaMessages: TypeAlias = list[Message]


@dataclass(slots=True)
class CharacterCard:
    """Logical character (Char): identity, preset messages, and bound lorebooks by id."""

    id: str
    name: str
    preset: Preset = field(default_factory=list)
    lorebook_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Persona:
    """User mask: how the human presents in chat (messages + identity metadata)."""

    id: str
    name: str
    messages: PersonaMessages = field(default_factory=list)

"""Conversation-layer types: messages, presets, character card, persona."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeAlias

from .common import _md


class MessageType(StrEnum):
    """Role of a chat message (OpenAI-style string values)."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(slots=True)
class Message:
    """Smallest interaction unit toward the model; maps to common API roles."""

    role: MessageType = field(metadata=_md("Logical speaker: system, user, assistant, or tool."))
    content: str = field(metadata=_md("Message body text."))
    name: str | None = field(
        default=None,
        metadata=_md("Optional label (e.g. tool name); used mainly when `role` is `tool`."),
    )
    tool_call_id: str | None = field(
        default=None,
        metadata=_md("Binds a tool result to a tool call; set when `role` is `tool`."),
    )


# Final sequence assembled for the model (template + injections, ordering host-defined).
Preset: TypeAlias = list[Message]
# Message history for a single conversation turn context (semantics differ from Preset only by usage).
Chat: TypeAlias = list[Message]
# User-mask framing: voice, style, and constraints for the human side (distinct from a Char Preset).
PersonaMessages: TypeAlias = list[Message]


@dataclass(slots=True)
class CharacterCard:
    """Logical character (Char): identity, preset messages, and bound lorebooks by id."""

    id: str = field(metadata=_md("Stable character identifier (e.g. kebab-case slug)."))
    name: str = field(metadata=_md("Display name."))
    preset: Preset = field(
        default_factory=list,
        metadata=_md("Messages forming this character's contribution to the outgoing prompt."),
    )
    description: str | None = field(
        default=None,
        metadata=_md("Optional free-text summary for UIs or tooling."),
    )
    lorebook_ids: list[str] = field(
        default_factory=list,
        metadata=_md("Identifiers of `Lorebook` resources to attach; resolved by the host."),
    )


@dataclass(slots=True)
class Persona:
    """User mask: how the human presents in chat (messages + identity metadata)."""

    id: str = field(metadata=_md("Stable persona identifier."))
    name: str = field(metadata=_md("Display name for the persona."))
    messages: PersonaMessages = field(
        default_factory=list,
        metadata=_md("Messages describing the user's voice, style, or constraints for this mask."),
    )

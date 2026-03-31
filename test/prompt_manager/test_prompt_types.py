"""Tests for conversation-layer types in prompt_manager.types."""

from prompt_manager.types import (
    CharacterCard,
    Chat,
    LoreBook,
    Lorebook,
    Message,
    MessageType,
    Persona,
    PersonaMessages,
    Preset,
)


def test_message_type_str_enum_values() -> None:
    assert MessageType.SYSTEM == "system"
    assert MessageType.USER == "user"
    assert MessageType.ASSISTANT == "assistant"
    assert MessageType.TOOL == "tool"
    assert list(MessageType) == [
        MessageType.SYSTEM,
        MessageType.USER,
        MessageType.ASSISTANT,
        MessageType.TOOL,
    ]


def test_message_constructors() -> None:
    assert Message(MessageType.SYSTEM, "sys") == Message(role=MessageType.SYSTEM, content="sys")
    tool_msg = Message(
        MessageType.TOOL,
        '{"ok": true}',
        name="lookup",
        tool_call_id="call-1",
    )
    assert tool_msg.name == "lookup"
    assert tool_msg.tool_call_id == "call-1"


def test_preset_and_chat_type_aliases() -> None:
    preset: Preset = [
        Message(MessageType.SYSTEM, "You are helpful."),
        Message(MessageType.USER, "Hello."),
    ]
    history: Chat = preset.copy()
    assert len(history) == 2
    assert isinstance(history, list)


def test_character_card_and_persona() -> None:
    char = CharacterCard(
        id="coding-agent",
        name="Coder",
        preset=[Message(MessageType.SYSTEM, "Act as a coder.")],
        lorebook_ids=["coding-default"],
    )
    assert char.description is None
    assert char.lorebook_ids == ["coding-default"]

    framing: PersonaMessages = [Message(MessageType.SYSTEM, "You are a careful student.")]
    persona = Persona(id="student", name="Student", messages=framing)
    assert len(persona.messages) == 1


def test_lorebook_type_alias() -> None:
    assert LoreBook is Lorebook

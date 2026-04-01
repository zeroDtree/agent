from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from prompt_manager.builder import build_lorebook
from prompt_manager.loader import load_lorebook
from prompt_manager.logger import LorebookEventLogger
from prompt_manager.runtime import LorebookRuntimeEngine, MultiLorebookRuntimeEngine
from prompt_manager.types import RuntimeContext

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_text(path: str) -> str:
    return (_PROJECT_ROOT / path).read_text(encoding="utf-8")


def _read_first_existing(paths: list[str]) -> str:
    for path in paths:
        candidate = _PROJECT_ROOT / path
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    raise FileNotFoundError(f"None of the prompt files exist: {paths}")


_DEFAULT_CHARACTER_PROMPT_PATHS = ["prompts/chars/main.md", "prompts/default/main.md"]


def _read_character_prompt(character_prompt_path: str | None = None) -> str:
    if character_prompt_path:
        candidate = _PROJECT_ROOT / character_prompt_path
        if not candidate.exists():
            raise FileNotFoundError(f"Character prompt file not found: {character_prompt_path}")
        return candidate.read_text(encoding="utf-8")
    return _read_first_existing(_DEFAULT_CHARACTER_PROMPT_PATHS)


def _build_base_preset_messages(character_prompt_path: str | None = None) -> list:
    return [
        SystemMessage(content=_read_text("prompts/core/system.md")),
        AIMessage(content=_read_first_existing(["prompts/core/ai-ok1.md", "prompts/core/ai-ok.md"])),
        HumanMessage(content=_read_text("prompts/core/role_play.md") + "\n\n" + _read_character_prompt(character_prompt_path)),
        AIMessage(content=_read_text("prompts/core/ai-ok2.md")),
    ]


BASE_PRESET_MESSAGES = _build_base_preset_messages()

_DEFAULT_LOREBOOK_ID = "coding-default"
_LOREBOOK_ROOT = _PROJECT_ROOT / "prompts/lorebooks"
_ENGINES: dict[str, LorebookRuntimeEngine] = {}
_EVENT_LOGGER = LorebookEventLogger()


def _normalize_lorebook_ids(lorebook_ids: list[str] | None) -> list[str]:
    if not lorebook_ids:
        return [_DEFAULT_LOREBOOK_ID]
    unique_ids: list[str] = []
    seen: set[str] = set()
    for lorebook_id in lorebook_ids:
        if lorebook_id not in seen:
            unique_ids.append(lorebook_id)
            seen.add(lorebook_id)
    return unique_ids


def _get_engine(lorebook_id: str) -> LorebookRuntimeEngine:
    cached = _ENGINES.get(lorebook_id)
    if cached is not None:
        return cached

    lorebook_source = _LOREBOOK_ROOT / lorebook_id
    lorebook_output = lorebook_source / "lorebook.json"
    if not lorebook_output.exists():
        build_lorebook(source=lorebook_source, output=lorebook_output)
    lorebook = load_lorebook(lorebook_output)
    engine = LorebookRuntimeEngine(lorebook)
    _ENGINES[lorebook_id] = engine
    return engine


def build_preset_messages(
    user_input: str,
    thread_id: str,
    turn_index: int,
    lorebook_ids: list[str] | None = None,
    tags: set[str] | None = None,
    include_base_messages: bool = True,
    character_prompt_path: str | None = None,
) -> list:
    runtime_context = RuntimeContext(
        request_id=str(uuid4()),
        session_id=thread_id,
        role="assistant",
        text=user_input,
        tags=tags or {"coding", "python"},
        active_sources={"global"},
        turn_index=turn_index,
    )
    selected_lorebook_ids = _normalize_lorebook_ids(lorebook_ids)
    engines = [_get_engine(lorebook_id) for lorebook_id in selected_lorebook_ids]
    runtime_result = MultiLorebookRuntimeEngine(engines).run(runtime_context)
    _EVENT_LOGGER.append_events(runtime_result.events)
    messages: list = []
    if runtime_result.injected_prompt:
        messages.append(SystemMessage(content=runtime_result.injected_prompt))
    if include_base_messages:
        messages.extend(_build_base_preset_messages(character_prompt_path))
    return messages

from __future__ import annotations

from pathlib import Path

_DEFAULT_CHARACTER_PROMPT_PATHS = ["prompts/chars/main.md"]


class PresetPromptReader:
    """Loads preset markdown from the project tree."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def read_text(self, relative_path: str) -> str:
        candidate = self._root / relative_path
        if not candidate.exists():
            raise FileNotFoundError(f"Prompt file not found: {relative_path}")
        return candidate.read_text(encoding="utf-8")

    def read_first_existing(self, relative_paths: list[str]) -> str:
        for path in relative_paths:
            candidate = self._root / path
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")
        raise FileNotFoundError(f"None of the prompt files exist: {relative_paths}")

    def read_character_prompt(self, character_prompt_path: str | None) -> str:
        if character_prompt_path:
            candidate = self._root / character_prompt_path
            if not candidate.exists():
                raise FileNotFoundError(f"Character prompt file not found: {character_prompt_path}")
            return candidate.read_text(encoding="utf-8")
        return self.read_first_existing(list(_DEFAULT_CHARACTER_PROMPT_PATHS))

    def read_persona_prompt(self, persona_prompt_path: str | None) -> str | None:
        if not persona_prompt_path:
            return None
        candidate = self._root / persona_prompt_path
        if not candidate.exists():
            raise FileNotFoundError(f"Persona prompt file not found: {persona_prompt_path}")
        return candidate.read_text(encoding="utf-8")

from __future__ import annotations

from pathlib import Path

import omegaconf
from omegaconf import DictConfig

from config.config_class import WorkConfig

from .state import ChatSessionState

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_shell_working_directory(working_directory: str) -> str:
    resolved = Path(working_directory).expanduser()
    if not resolved.is_absolute():
        resolved = (PROJECT_ROOT / resolved).resolve()
    return str(resolved)


def resolve_prompt_dir(prompt_dir: str) -> Path:
    return (PROJECT_ROOT / prompt_dir).resolve()


def list_available_roles(prompt_dir: Path) -> list[str]:
    if not prompt_dir.exists() or not prompt_dir.is_dir():
        return []
    return sorted(path.stem for path in prompt_dir.glob("*.md"))


def resolve_role_prompt_path(prompt_dir: Path, role_name: str) -> str:
    return str((prompt_dir / f"{role_name}.md").relative_to(PROJECT_ROOT))


def resolve_conversation_dir(cfg: DictConfig) -> Path:
    chat_cfg = cfg.get("chat")
    configured = str(chat_cfg.get("conversation_dir", "data/conversations")) if chat_cfg else "data/conversations"
    conversation_dir = Path(configured).expanduser()
    if not conversation_dir.is_absolute():
        conversation_dir = (PROJECT_ROOT / conversation_dir).resolve()
    return conversation_dir


def resolve_conversation_path(raw_path: str, default_dir: Path) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate
    if candidate.parent != Path("."):
        return candidate
    return default_dir / candidate


def build_chat_session_state(
    cfg: DictConfig,
    work_config: WorkConfig,
) -> ChatSessionState:
    char_cfg = cfg.get("char")
    default_conversation_dir = resolve_conversation_dir(cfg)
    lorebook_ids = list(char_cfg.get("lorebook_ids", [])) if char_cfg else []
    prompt_dir = resolve_prompt_dir(str(char_cfg.get("prompt_dir", "prompts/chars")) if char_cfg else "prompts/chars")
    current_role = str(char_cfg.get("active", "main")) if char_cfg else "main"

    def notify_warning(message: str) -> None:
        print(f"Warning: {message}")

    available_roles = list_available_roles(prompt_dir)
    if current_role not in available_roles and available_roles:
        notify_warning(
            f"Configured role '{current_role}' not found. Falling back to '{available_roles[0]}'.",
        )
        current_role = available_roles[0]
    elif not available_roles:
        notify_warning(f"No role prompts found in {prompt_dir}. Falling back to default prompt behavior.")

    current_prompt_path = resolve_role_prompt_path(prompt_dir, current_role) if available_roles else None
    shell_working_directory = resolve_shell_working_directory(work_config.working_directory)

    preset_segments_enabled = None
    preset_segment_order = None
    persona_prompt_path = None
    if char_cfg:
        persona_raw = char_cfg.get("persona_prompt_path")
        persona_prompt_path = str(persona_raw) if persona_raw else None
        preset_cfg = char_cfg.get("preset")
        if preset_cfg is not None:
            preset_plain = omegaconf.OmegaConf.to_container(preset_cfg, resolve=True)
            if isinstance(preset_plain, dict):
                segments_raw = preset_plain.get("segments")
                if isinstance(segments_raw, dict):
                    preset_segments_enabled = {
                        str(key): bool(value["enabled"])
                        for key, value in segments_raw.items()
                        if isinstance(value, dict) and "enabled" in value
                    }
                order_raw = preset_plain.get("segment_order")
                if isinstance(order_raw, list) and order_raw:
                    preset_segment_order = [str(item) for item in order_raw]

    return ChatSessionState(
        prompt_dir=prompt_dir,
        default_conversation_dir=default_conversation_dir,
        current_role=current_role,
        current_prompt_path=current_prompt_path,
        shell_working_directory=shell_working_directory,
        lorebook_ids=lorebook_ids,
        persona_prompt_path=persona_prompt_path,
        preset_segments_enabled=preset_segments_enabled,
        preset_segment_order=preset_segment_order,
    )

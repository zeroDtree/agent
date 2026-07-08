from __future__ import annotations

import json
from pathlib import Path

from langchain_core.messages import messages_from_dict, messages_to_dict


def save_conversation(path: Path, conversation_history: list) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = messages_to_dict(conversation_history)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
    return len(payload)


def load_conversation(path: Path) -> list:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return messages_from_dict(payload)

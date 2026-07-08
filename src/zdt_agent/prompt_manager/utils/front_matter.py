from __future__ import annotations

from pathlib import Path

import yaml


def parse_markdown_entry(path: Path) -> tuple[dict, str]:
    """Parse Markdown entry with YAML front matter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text.strip()

    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text.strip()

    front_matter_raw = parts[0].removeprefix("---\n")
    content = parts[1].strip()
    metadata = yaml.safe_load(front_matter_raw) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata, content

---
id: python-env-rule
title: Python command execution policy
enabled: true
triggers:
  keywords: ["python", "pytest", "script", "uv run"]
  regex: []
  case_sensitive: false
  whole_word: false
injection:
  position_type: after_character
  order: 100
advanced:
  inclusion_group: null
  group_scoring: false
  probability: 1.0
  recursive: false
  max_recursion_depth: 0
  sticky_turns: 0
  cooldown_turns: 0
  delay_turns: 0
budget:
  max_tokens: 300
  truncate: tail
---

Always use one of the following when running Python commands or scripts:

- Prefix commands with `uv run`: `uv run python script.py`, `uv run pytest`.
- Or activate the virtual environment first: `source .venv/bin/activate`.

Prefer `uv run` for one-off commands and activate the environment for interactive sessions.

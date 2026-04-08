---
id: python-linter
title: Python Linter
enabled: false
triggers:
  keywords: ["python", "linter", "ruff", "pylint"]
  regex: []
  case_sensitive: false
  whole_word: false
filters:
  role_allowlist: ["assistant"]
  role_denylist: []
injection:
  position: after_character
  order: 90
  outlet: null
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
  max_tokens: 5000
  truncate: tail
---

Use the following command to check the Python code:

```bash
ruff check <file_path>
```

Use the following command to check and fix the code style of the Python code:

```bash
ruff check --fix <file_path>
```
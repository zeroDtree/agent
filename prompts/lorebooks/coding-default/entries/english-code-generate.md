---
id: english-code-generate
title: English code generation policy
enabled: true
triggers:
  keywords: ["code", "function", "class", "script", "refactor", "implement"]
  regex: []
  case_sensitive: false
  whole_word: false
injection:
  position_type: after_character
  order: 90
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
  max_tokens: 1000
  truncate: tail
---

Write generated source code, identifiers, comments, docstrings, and developer-facing output in English.
Prefer clear and simple wording, keep naming consistent, and preserve semantic intent from non-English input.

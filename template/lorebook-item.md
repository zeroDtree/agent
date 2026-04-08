---
id: new-entry-id
title: New entry title
enabled: true
triggers:
  keywords: ["keyword1", "keyword2"]
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

Entry content...
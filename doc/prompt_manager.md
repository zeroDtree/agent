## 1. Prompt Organization (inspired by [SillyTavern](https://docs.sillytavern.app/usage/core-concepts/worldinfo/))

- **Message**: The smallest interaction unit. Common types include `System`, `User`, `Assistant`, and `Tool`.
- **Preset**: The final Message sequence sent to the model.
- **Chat**: A Message sequence representing one conversation context (chat history).
- **LoreBook / World Info / World Book**: A collection of Messages that are triggered by rules and dynamically injected into the Preset.
- **Character Card**: A Message collection representing a logical entity that interacts with the user or other chars (shortened as Char). It can bind one Preset and multiple LoreBooks.
- **Persona**: A Message collection representing the user's persona (identity mask), i.e., the role from which the user talks to a Char.

Prompt directory structure example:

```text
prompts/
  core/
    system.md
    safety.md
    output_contract.md
  chars/
    coding_agent.md
    reviewer_agent.md
  lorebooks/
    lorebook_id/
      lorebook.json
      entries/
        <entry_id>.md
  personas/
    student.md
```

- `<lorebook_id>`: Unique lorebook identifier. Use kebab-case, for example `coding-default`.
- `<entry_id>`: Unique entry identifier. Use kebab-case and keep it unique within one lorebook, for example `python-env-rule`.


## 2. Lorebook Role in the Architecture

A Lorebook is essentially a dynamic context injector:

- It activates entries by conditions such as keywords, regex, and vector similarity.
- It injects selected entries into target prompt positions within budget constraints.
- It only loads knowledge relevant to the current turn, preventing permanent prompt bloat.

Note: A Lorebook only increases the probability that the model sees specific information. It does not guarantee that the output will always reflect that information.

Context-specific source scopes:

- **Global**: Global LoreBook.
- **Character Lore**: Character-specific LoreBook.
- **Persona Lorebook**: LoreBook bound to the current Persona.
- **Chat Lorebook**: LoreBook bound to a single conversation session.


## 3. Lorebook Entry Model (Entry Schema)

- **`LoreEntry` (`prompt_manager/types/lorebook.py`)**
  - `id: str`
    - Unique entry identifier (kebab-case).
  - `path: str`
    - Source file path of the entry (typically `entries/<id>.md`).
  - `enabled: bool`
    - Whether this entry is enabled.
  - `content: str`
    - Final body text to inject (or write to an outlet).
  - `resolved: EntryResolved`
    - Normalized parameters after build, used directly at runtime.

- **`EntryResolved` (runtime parameter aggregation)**
  - `triggers: EntryTriggers`
    - **`keywords: list[str]`**: Keyword trigger (matching any one keyword makes it a candidate).
    - **`regex: list[str]`**: Regex trigger (evaluated in parallel with keywords).
    - **`case_sensitive: bool`**: Case sensitivity for both keywords and regex.
    - **`whole_word: bool`**: Whether keyword matching uses word boundaries (use carefully for CJK and similar scripts).
  - `filters: EntryFilters`
    - **`role_allowlist: list[str]`**: If non-empty, only these roles are allowed.
    - **`role_denylist: list[str]`**: Any match is rejected.
  - `injection: EntryInjection`
    - **`position: InjectionPositionType`**: Injection position type.
      - Current enum values in code: `before_char_defs` / `after_char_defs` / `depth` / `outlet`.
    - **`order: int`**: Ordering weight among candidates in the same batch (combined with `runtime.injection_order`).
    - **`message_type: MessageType | None`**: Message role field. The current injector does not branch by this field and only preserves it in the model.
    - **`outlet: str | None`**: Writes to a named outlet. If the host does not reference that outlet, it is dropped during injection.
    - **`depth: int | None`**: Depth parameter when `position=depth`.
  - `advanced: EntryAdvanced`
    - **`inclusion_group: str | None`**: Mutual exclusion group (only one entry is kept per group).
    - **`group_scoring: bool`**: Whether to prioritize by match score within the group.
    - **`probability: float`**: Probability gate (0~1).
    - **`recursive: bool`**: Whether recursive expansion is enabled.
    - **`max_recursion_depth: int`**: Entry-level recursion depth limit (0 means only the global limit applies).
    - **`sticky_turns: int`**: Number of turns an entry can stay active after trigger.
    - **`cooldown_turns: int`**: Cooldown turns after trigger.
    - **`delay_turns: int`**: Earliest turn index at which the entry can trigger.
  - `budget: EntryBudget`
    - **`max_tokens: int`**: Entry-level token budget upper bound.
    - **`truncate: "head" | "tail" | "none"`**: Truncation policy when over budget.

- **`RuntimeContext` (`prompt_manager/types/runtime.py`, strongly related to entry activation)**
  - `text: str`
    - Primary scan text (usually current turn input).
  - `source_texts: dict[SourceScope, str]` + `active_sources: set[SourceScope]`
    - Additional scan sources (such as character/persona/chat).
  - `role: str`
    - Used by `EntryFilters` for role-based filtering.
  - `outlet_references: set[str]`
    - Outlet names referenced by the template. Entries targeting unreferenced outlets are dropped.
  - `turn_index: int`
    - Used for timing effects (`delay/sticky/cooldown`).
  - `seed: int | None`
    - Random seed for probability gating (can override default strategy).

## 4. Activation Pipeline (Engine View)

- **`LorebookRuntimeEngine` actual stages (6 steps)**
  - **1) Scan (`ActiveEntryScanner.collect_enabled_entries`)**
    - Collect only entries with `entry.enabled == true`.
  - **2) Match (`LoreMatcher`)**
    - Match based on `EntryTriggers.keywords/regex`.
    - Supports `whole_word` and `case_sensitive`.
    - Supports direct sticky hits (no need to match keywords again this turn).
    - Scan text comes from `RuntimeContext.text + source_texts(active_sources)`.
  - **3) Filter (`LoreFilterStage`)**
    - Applies `delay_turns` and `cooldown_turns`.
    - Applies `filters.role_allowlist/role_denylist`.
    - Applies `advanced.probability` gating.
  - **4) Expand (`LoreExpander`)**
    - Performs recursive expansion matching for entries with `advanced.recursive=true`.
    - Constrained jointly by `runtime.max_recursion_steps` and `advanced.max_recursion_depth`.
  - **5) Sort (`LoreSorter`)**
    - Resolves `inclusion_group` mutual exclusion first.
    - If `group_scoring=true`, prioritize by match score.
    - Then sort by `injection.order` (direction controlled by `runtime.injection_order`).
  - **6) Inject (`LoreInjector`)**
    - Applies `EntryBudget` first (entry-level budget and truncation).
    - Then applies `LorebookBudget` (lorebook-level budget and `overflow_policy`).
    - Drops entries with `injection.outlet` not referenced by `outlet_references`.
    - Updates session state after injection (`sticky/cooldown`).

## 5. Budget and Stability Strategy

- Set a fixed budget upper bound for each Lorebook (absolute token count or a ratio of context size).
- Keep always-on entries as few as possible; within budget, prioritize higher-priority entries.
- When budget is insufficient, prioritize safety, protocol, and task-critical entries.

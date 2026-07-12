# How the prompt system works

**Static preset bones + conditional lorebook meat**, selected by triggers and session rules, merged under a token budget, and laid out into one ordered conversation for the model.

The system has two ideas: 
- **lorebooks** (dynamic snippets that may attach when the conversation matches rules)
- **preset skeleton** (fixed blocks such as system core, character, and persona). 

At request time, matching lorebook text is merged into that skeleton and becomes the model’s context.

---

## Architecture

### 1. Build & Load

Markdown entries and preset files on disk → parsed and assembled into in-memory objects.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#f0f7ee', 'primaryBorderColor': '#6aa84f', 'lineColor': '#8fbc8f'}}}%%
flowchart TB
  subgraph disk["📁 On disk"]
    BookDir["Book folder"]
    EntryMD["entries/*.md\nYAML front matter + body"]
    PresetMD["Preset files\ncore / character / persona / depth"]
    BookDir --> EntryMD
  end

  subgraph build["🔨 Build"]
    Parse["Parse front matter\n→ triggers, injection rules, budget"]
    Resolve["Merge with defaults\n→ resolved entry config"]
    LoreBookOut["LoreBook\nentries + budget + merge policy"]
    EntryMD --> Parse --> Resolve --> LoreBookOut
  end

  subgraph load["📦 In memory"]
    PresetSegments["Preset skeleton\nordered message blocks"]
  end

  PresetMD --> PresetSegments

  style disk fill:#e8f5e9,stroke:#6aa84f
  style build fill:#fff3e0,stroke:#f9a825
  style load fill:#e3f2fd,stroke:#1e88e5
```

- **Book id** = folder name; **entry id** = front-matter `id` or filename stem.
- Markdown sources trigger **rebuild on load**; front matter is merged with per-field defaults.
- Preset files load once and produce the fixed skeleton reused across all requests.

---

### 2. Per-Book Pipeline

One pipeline per active lorebook. Six stages scan entries against the current conversation and produce matched + filtered + sorted candidates.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#f0f7ee', 'primaryBorderColor': '#6aa84f', 'lineColor': '#8fbc8f'}}}%%
flowchart TB
  Input["Conversation context\nuser text, session, turn, tags"]
  State[("Session state\nsticky & cooldown\nper-entry, across turns")]

  subgraph pipeline["⚙️ Pipeline"]
    direction TB

    S0["① Scan\npick enabled entries"]
    S1["② Match\nkeyword / regex triggers\n+ sticky entries from state"]
    S2["③ Filter\ndelay, cooldown, probability"]
    S3["④ Expand\nrecursive: matched content\nbecomes context for new matches"]
    S4["⑤ Sort\nresolve competing groups\nsort by injection priority"]
    S5["⑥ Budget\nper-entry token limit\ntruncate or drop"]

    S0 --> S1 --> S2 --> S3 --> S4 --> S5
  end

  Output["Matched entries\nwith scores and reject reasons"]

  Input --> S0
  State -.->|"read state"| S1
  State -.->|"read state"| S2
  S5 --> Output

  style pipeline fill:#f3e5f5,stroke:#8e24aa
  style State fill:#fce4ec,stroke:#e91e63
```

- **Match**: scans user text against keywords and regex; sticky entries re-trigger automatically.
- **Filter**: gates entries by delay turns, cooldown, and random probability.
- **Expand**: matched entries marked recursive have their own body scanned for further matches (breadth-first, depth-limited).
- **Sort**: entries in the same inclusion group compete (by match score or priority); survivors are ordered.
- Session state persists sticky and cooldown counters **across turns**.

---

### 3. Merge & Assembly

Results from all active books are merged under a global token budget, then spliced into the preset skeleton at annotated anchor points.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#f0f7ee', 'primaryBorderColor': '#6aa84f', 'lineColor': '#8fbc8f'}}}%%
flowchart TB
  subgraph merge["🔀 Merge"]
    direction TB
    BookResults["Per-book results × N"]
    Union["Union all candidates"]
    GlobalSort["Global sort\nby priority, book, entry"]
    Budget["Budgeted inject\nΣ book budgets\noverflow → drop"]
    MergedOut["Selected entries\nwith placement instructions"]

    BookResults --> Union --> GlobalSort --> Budget --> MergedOut
  end

  subgraph assembly["🧩 Assembly"]
    direction TB
    Bucket["Bucket by placement\nbefore/after core, char, persona\n+ depth layer"]
    Walk["Walk skeleton in order\nCore → Character → Persona → Depth"]
    Splice["Splice at each segment\n  inject before-anchor entries\n  embed preset messages\n  inject after-anchor entries\nDepth: layer by distance from tail"]
    MapRole["Assign message roles\nsystem / user / assistant / tool"]
    FinalOut["Ordered message list\nready for the model"]

    Bucket --> Walk --> Splice --> MapRole --> FinalOut
  end

  MergedOut --> Bucket
  PresetInput["Preset skeleton\nsegment order + messages"] --> Walk

  style merge fill:#e8eaf6,stroke:#3949ab
  style assembly fill:#e0f7fa,stroke:#00acc1
```

- **Placement anchors**: `before_core`, `after_core`, `before_character`, `after_character`, `before_persona`, `after_persona`, `depth`, or overflow (appended at end).
- Within each anchor, entries sort by priority; depth entries sort by distance from the newest message.
- Each entry maps to a message role; `system` is the default.
- Injected keys are `book_id:entry_id`; global budget is the sum of per-book budgets.

# How the prompt system works

**Static preset bones + conditional lorebook meat**, selected by triggers and session rules, merged under a token budget, and laid out into one ordered conversation for the model.

The system has two ideas: 
- **lorebooks** (dynamic snippets that may attach when the conversation matches rules)
- **preset skeleton** (fixed blocks such as system core, character, and persona). 

At request time, matching lorebook text is merged into that skeleton and becomes the model’s context.

---

## Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#f0f7ee', 'primaryBorderColor': '#6aa84f', 'lineColor': '#8fbc8f'}}}%%
flowchart LR
  subgraph disk["On disk"]
    BookDir["Book folder\nid = folder name"]
    Entries["entries/*.md\nYAML front matter + body"]
    BookJson["lorebook.json"]
    PresetFiles["Preset skeleton files\ncore / character / persona / depth"]
    BookDir --> Entries
    Entries -->|"build on load"| BookJson
  end

  subgraph runtime["Per request"]
    Ctx["User text\nsession + turn + tags"]
    subgraph books["Each active book"]
      PipeA["Match → filter → expand"]
      PipeB["Match → filter → expand"]
    end
    Union["Union candidates"]
    GSort["Global sort\norder, book id, entry id"]
    Budget["Single budgeted inject\nbook_id:entry_id"]
    BookJson --> PipeA
    BookJson --> PipeB
    Ctx --> PipeA
    Ctx --> PipeB
    PipeA --> Union
    PipeB --> Union
    Union --> GSort --> Budget
  end

  subgraph out["Assembly and output"]
    SkWalk["Skeleton walk\nCore → Character → Persona → Depth"]
    Splice["Splice injected bodies\nbefore / after / depth / tail"]
    Roles["Map to message roles\nsystem / user / …"]
    Msg["Ordered messages for the model"]
    PresetFiles --> SkWalk
    SkWalk --> Splice
    Budget --> Splice
    Splice --> Roles --> Msg
  end
```

- **Book id** = folder name; **entry id** = front-matter `id` or filename stem.
- Markdown sources trigger **rebuild on load**; JSON-only books load as-is.
- Runtime inputs: user text, session identity, turn index, optional tags.
- Filter stage covers probability, cooldowns, stickiness, etc.; expand handles recursive pulls.
- Global budget is conceptually the **sum of per-book budgets**; injected keys are **`book_id:entry_id`**.

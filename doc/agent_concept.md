- **LLM (Large Language Model)**: The Agent's "control center (Controller)", responsible for reasoning, intent recognition, and text generation.
- **Function Call / Tool Use**: A connection mechanism. The LLM outputs structured instructions (such as JSON), which are translated by the host environment into concrete function execution, enabling the LLM to operate on the external world.
- **MCP (Model Context Protocol)**: A standardized protocol for tool calling and data interaction initiated by Anthropic, designed to remove integration barriers across different tools.

---

- **State (state machine)**: Persistently stores the Agent's short-term/long-term memory, execution context, and variable states.
- **Graph (topology graph)**:
  - **Node**: Execution unit. It can be an **LLM node** (decision/generation) or a **Tool node** (execution/computation).
  - **Edge / Route**:
    - **Hard Route (static routing)**: Deterministic transitions based on predefined conditions (such as `if/else` or status codes).
    - **Soft Route (dynamic routing)**: The LLM acts as a "router" and semantically decides the next target node based on the current State.
- **Subgraph**: A logical encapsulation unit. It abstracts complex local workflows into an independent node, enabling modular architecture and reuse.

---

- **Skill**: A closed-loop logic package designed for a specific business objective.
  - **Soft Skill (Declarative)**
    - **Representation**: Detailed SOP documentation, System Prompts, or metadata-rich README files.
    - **Core logic**: Prompt engineering. Use natural language to provide execution steps, constraints, and target strategies to the LLM.
    - **Runtime behavior**: The LLM dynamically builds the execution path at runtime using in-context learning capabilities.
  - **Hard Skill (Procedural)**
    - **Representation**: A packaged **Subgraph** with explicit code logic, node definitions, and topology links.
    - **Core logic**: Workflow engineering. Break down complex tasks into deterministic and highly reliable steps.
    - **Runtime behavior**: The Agent enters the subgraph like calling a subroutine and executes strictly following the defined topology.
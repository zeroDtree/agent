from typing import Annotated, Optional, TypedDict

from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]
    session_id: Optional[str]

import logging

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph

# Re-export config types so existing callers (main.py) keep working
from config.config_class import AutoMode, GraphConfig, LLMConfig, LoggerConfig, ToolConfig, WorkConfig
from graphs.nodes import get_auto_reject_node, get_chatbot_node, get_custom_tool_node, get_human_confirm_node
from graphs.routing import make_chatbot_router
from graphs.state import State
from utils.logger import get_and_create_new_log_dir, get_logger

__all__ = [
    "Graph",
    "State",
    "AutoMode",
    "GraphConfig",
    "LLMConfig",
    "LoggerConfig",
    "ToolConfig",
    "WorkConfig",
]


class Graph:
    def __init__(
        self,
        config: GraphConfig,
        logger_config: LoggerConfig = None,
        logger: logging.Logger = None,
        llm_config: LLMConfig = None,
        work_config: WorkConfig = None,
        tool_config: ToolConfig = None,
    ):
        assert logger_config is not None or logger is not None, "Either logger_config or logger must be provided"
        if logger_config is not None:
            log_dir = get_and_create_new_log_dir(
                root=logger_config.log_dir, prefix="", suffix="", strftime_format="%Y%m%d"
            )
            self.logger = get_logger(name=__name__, log_dir=log_dir)
        else:
            self.logger = logger

        self.config = config
        self.llm_config = llm_config
        self.work_config = work_config
        self.tool_config = tool_config

    def create_graph(self, tools=None, checkpointer=None, need_memory=False):
        if checkpointer is None:
            checkpointer = InMemorySaver() if need_memory else None

        tool_node = get_custom_tool_node(tools=tools, logger=self.logger)
        chatbot_node = get_chatbot_node(
            config=self.llm_config,
            tools=tools,
            max_history=self.config.n_max_history,
        )
        human_confirm_node = get_human_confirm_node(
            next_node_for_yes="my_tools",
            next_node_for_no="chatbot",
        )
        auto_reject_node = get_auto_reject_node(next_node="chatbot")
        router = make_chatbot_router(
            work_config=self.work_config,
            tool_config=self.tool_config,
            logger=self.logger,
        )

        builder = StateGraph(State)
        builder.add_node("my_tools", tool_node)
        builder.add_node("chatbot", chatbot_node)
        builder.add_node("human_confirm", human_confirm_node)
        builder.add_node("auto_reject", auto_reject_node)

        builder.add_edge(START, "chatbot")
        builder.add_edge("my_tools", "chatbot")
        builder.add_edge("auto_reject", "chatbot")
        builder.add_conditional_edges("chatbot", router)

        return builder.compile(checkpointer=checkpointer)

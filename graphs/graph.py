from typing import Annotated, Optional

from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from typing_extensions import TypedDict

from config.config_class import AutoMode, GraphConfig, LLMConfig, LoggerConfig, ToolConfig, WorkConfig
from utils.logger import get_and_create_new_log_dir, get_logger


class State(TypedDict):
    messages: Annotated[list, add_messages]
    session_id: Optional[str]


class Graph:
    def __init__(
        self,
        config: GraphConfig,
        logger_config: LoggerConfig = None,
        logger=None,
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
        self.work_config = work_config
        self.llm_config = llm_config
        self.config = config
        self.tool_config = tool_config

    def create_graph(self, tools=None, checkpointer=None, need_memory=False):
        """Create graph structure with dependency injection support"""

        if checkpointer is None:
            checkpointer = InMemorySaver() if need_memory else None

        tool_node = ToolNode(tools=tools)
        graph_builder = StateGraph(State)

        graph_builder.add_node("my_tools", tool_node)
        graph_builder.add_node("chatbot", self.get_chatbot_node(config=self.llm_config, tools=tools))
        graph_builder.add_node(
            "human_confirm",
            self.get_human_confirm_node(next_node_for_yes="my_tools", next_node_for_no="chatbot"),
        )
        graph_builder.add_node("auto_reject", self.get_auto_reject_node(next_node="chatbot"))
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_edge("my_tools", "chatbot")
        graph_builder.add_edge("auto_reject", "chatbot")

        graph_builder.add_conditional_edges(
            "chatbot",
            self.chatbot_route,
        )

        return graph_builder.compile(checkpointer=checkpointer)

    def get_human_confirm_node(self, next_node_for_yes: str, next_node_for_no: str):

        def human_confirm(state: State):
            tool_call_message = state["messages"][-1]
            nonlocal next_node_for_yes
            nonlocal next_node_for_no

            return self.console_confirm(state, tool_call_message, next_node_for_yes, next_node_for_no)

        return human_confirm

    def console_confirm(self, state: State, tool_call_message, next_node_for_yes: str, next_node_for_no: str):
        """Console mode confirmation"""
        human_str = input(f"About to execute {tool_call_message.content},\nDo you want to proceed? (yes/no): ")
        if human_str in ["y", "Y", "yes", "Yes", "YES"]:
            return Command(goto=next_node_for_yes)
        else:

            tool_messages = []
            for tool_call in tool_call_message.tool_calls:
                tool_message = ToolMessage(
                    content="User rejected execution of this tool call",
                    tool_call_id=tool_call["id"],
                )
                tool_messages.append(tool_message)

            return Command(goto=next_node_for_no, update={"messages": tool_messages})

    def get_auto_reject_node(self, next_node: str):
        def auto_reject_node(state: State):
            return self.reject_node(state, next_node)

        return auto_reject_node

    def reject_node(self, state: State, next_node: str, rejection_reason: str):
        tool_messages = []
        for tool_call in state["messages"][-1].get("tool_calls", []):
            tool_message = ToolMessage(content=rejection_reason, tool_call_id=tool_call["id"])
            tool_messages.append(tool_message)
        return Command(goto=next_node, update={"messages": tool_messages})

    def chatbot_route(self, state: State):
        try:
            if messages := state.get("messages", []):
                ai_message = messages[-1]
            else:
                raise ValueError(f"No messages found in input state to tool_edge: {state}")

            if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
                tool_names = [tool_call.get("name", "unknown") for tool_call in ai_message.tool_calls]
                self.logger.info(f"Tool calls detected: {', '.join(tool_names)}")
                self.logger.info(f"with args: {ai_message.tool_calls}")
                self.logger.info(f"{self.work_config.auto_mode}")

                if self.work_config.auto_mode == AutoMode.MANUAL:
                    return "human_confirm"
                elif self.work_config.auto_mode == AutoMode.UNIVERSAL_REJECT:
                    return "auto_reject"
                elif self.work_config.auto_mode == AutoMode.UNIVERSAL_ACCEPT:
                    return "my_tools"
                elif self.work_config.auto_mode == AutoMode.BLACKLIST_REJECT:
                    # Check all tool calls - if any is unsafe, reject
                    for tool_call in ai_message.tool_calls:
                        tool_name = tool_call.get("name", "")
                        args = tool_call.get("args", {})
                        if not self.is_safe(tool_name, args):
                            return "auto_reject"
                    return "human_confirm"  # All tools are safe
                elif self.work_config.auto_mode == AutoMode.WHITELIST_ACCEPT:
                    # Check all tool calls - only accept if all are safe
                    for tool_call in ai_message.tool_calls:
                        tool_name = tool_call.get("name", "")
                        args = tool_call.get("args", {})
                        if not self.is_safe(tool_name, args):
                            return "human_confirm"
                    return "my_tools"  # All tools are safe
            return END
        except Exception as e:
            self.logger.error(f"Routing function execution error: {e}")
            return END

    def is_safe(self, tool_name: str, args: dict) -> bool:
        if tool_name in ["run_shell_command_popen_tool"]:
            command = args.get("command", "")
            return command.split(" ")[0] in self.tool_config.safe_shell_commands
        else:
            return tool_name in self.tool_config.safe_tools

    def get_llm_model(self, config: LLMConfig):
        return ChatOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model_name,
            max_tokens=config.max_tokens,
            streaming=config.streaming,
            temperature=config.temperature,
            presence_penalty=config.presence_penalty,
            frequency_penalty=config.frequency_penalty,
        )

    def get_llm_with_tools(self, config: LLMConfig, tools: list[Tool]):
        llm = self.get_llm_model(config=config)
        return llm.bind_tools(tools) if tools else llm

    def get_chatbot_node(self, config: LLMConfig, tools: list[Tool] = None):

        def chatbot(state: State):
            """Main chatbot function with performance monitoring"""
            state["messages"] = self.cleanup_old_messages(state["messages"], max_history=self.config.n_max_history)
            messages = state["messages"]
            llm_with_tools = self.get_llm_with_tools(config=config, tools=tools)

            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}

        return chatbot

    def cleanup_old_messages(self, messages: list[BaseMessage], max_history: int) -> list[BaseMessage]:
        """Clean up old conversation history"""

        if len(messages) > max_history:
            # Keep the most recent max_history messages
            return messages[-max_history:]
        return messages

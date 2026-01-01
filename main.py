# offical package

import hydra
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from omegaconf import DictConfig
import omegaconf
from graphs.graph import AutoMode, Graph, GraphConfig, LLMConfig, LoggerConfig, ToolConfig, WorkConfig
from tools import get_run_shell_command_popen_tool

# from tools.embedding_knowledge_base import search_knowledge_base
# from tools.todo_list import todo_list_tool
from utils.logger import LoggerConfig, get_and_create_new_log_dir, get_logger
from utils.preset import preset_messages
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient


async def get_mcp_tools(mcp_config) -> list:
    try:
        client = MultiServerMCPClient(dict(mcp_config))
        tools = await client.get_tools()
    except Exception as e:
        return []
    return tools


async def async_main(cfg: DictConfig):
    """
    Main function to run the chatbot
    """
    print(omegaconf.OmegaConf.to_yaml(cfg=cfg))
    # log
    log_config = LoggerConfig(log_dir=cfg.log.log_dir, log_level=cfg.log.log_level)
    log_dir = get_and_create_new_log_dir(root=log_config.log_dir, prefix="", suffix="", strftime_format="%Y%m%d")
    logger = get_logger(name=__name__, log_dir=log_dir)
    # logger.info(OmegaConf.to_yaml(cfg))

    # llm
    llm_config = LLMConfig(
        model_name=cfg.llm.model_name,
        base_url=cfg.llm.base_url,
        api_key=cfg.llm.api_key,
        max_tokens=cfg.llm.max_tokens,
        streaming=cfg.llm.streaming,
        temperature=cfg.llm.temperature,
        presence_penalty=cfg.llm.presence_penalty,
        frequency_penalty=cfg.llm.frequency_penalty,
    )

    work_config = WorkConfig(
        working_directory=cfg.work.working_directory,
        command_timeout=cfg.work.command_timeout,
        auto_mode=AutoMode(cfg.work.auto_mode),
    )

    graph_config = GraphConfig(
        n_max_history=cfg.system.n_max_history,
        thread_id=cfg.system.thread_id,
        recursion_limit=cfg.system.recursion_limit,
        stream_mode=cfg.system.stream_mode,
    )

    tool_config = ToolConfig(
        safe_tools=cfg.tool.get("safe_tools", []),
        dangerous_tools=cfg.tool.get("dangerous_tools", []),
        safe_shell_commands=cfg.tool.get("safe_shell_commands", []),
        dangerous_shell_commands=cfg.tool.get("dangerous_shell_commands", []),
    )

    try:
        # Initialize graph
        mcp_tools = await get_mcp_tools(cfg.mcp)
        tools = [get_run_shell_command_popen_tool(work_config=work_config)] + mcp_tools
        graph = Graph(
            logger=logger,
            llm_config=llm_config,
            work_config=work_config,
            config=graph_config,
            tool_config=tool_config,
        ).create_graph(need_memory=True, tools=tools)

        is_first = True
        while True:
            try:
                input_str = input("You: ")

                input_state = {
                    "messages": (
                        preset_messages + [HumanMessage(content=input_str)]
                        if is_first
                        else [HumanMessage(content=input_str)]
                    ),
                }

                is_first = False

                events = graph.astream(
                    input=input_state,
                    config={
                        "configurable": {"thread_id": cfg.system.thread_id},
                        "recursion_limit": cfg.system.recursion_limit,
                    },
                    stream_mode=cfg.system.stream_mode,
                )

                printed_message_ids = set()  # Track printed messages to avoid duplicates

                async for event in events:
                    if event.get("messages") and len(event["messages"]) > 0:
                        # Collect recent AI and tool messages in order until we hit a non-AI message
                        recent_ai_and_tool_messages = []
                        for message in event["messages"][::-1]:  # Start from most recent
                            if isinstance(message, (AIMessage, ToolMessage)):
                                recent_ai_and_tool_messages.append(message)
                            else:
                                # Stop when we encounter a non-AI message
                                break

                        # Print AI and tool messages in chronological order (oldest first)
                        for ai_and_tool_message in reversed(recent_ai_and_tool_messages):
                            # Use message ID or content hash to avoid duplicates
                            message_id = getattr(ai_and_tool_message, "id", None) or hash(
                                str(ai_and_tool_message.content)
                            )
                            if message_id not in printed_message_ids:
                                ai_and_tool_message.pretty_print()
                                printed_message_ids.add(message_id)

            except KeyboardInterrupt:
                print("\n\nExiting program")
                break
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                print(f"Error occurred, please try again: {e}")

    except Exception as e:
        logger.error(f"System startup failed: {e}")
        print(f"System startup failed: {e}")


@hydra.main(config_path="config", config_name="config", version_base="1.3")
def main(cfg):
    asyncio.run(async_main(cfg))


if __name__ == "__main__":
    main()

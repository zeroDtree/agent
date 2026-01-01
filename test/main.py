import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
import os

async def main():
    client = MultiServerMCPClient(
        {
            "math": {"transport": "http", "url": "http://127.0.0.1:8000/mcp"},
        }
    )

    tools = await client.get_tools()

    print(tools)

    llm = ChatOpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        max_tokens=8192,
    )
    # Bind tools to LLM - need to assign the result back
    llm_with_tools = llm.bind_tools(tools)

    # Create a tool dictionary for easy lookup
    tool_dict = {tool.name: tool for tool in tools}

    # Initialize conversation with user message
    messages = [HumanMessage(content="what's (3 + 5) x 12?，use tools to solve the problem")]

    # Tool call loop - continue until LLM returns final answer
    max_iterations = 10
    for iteration in range(max_iterations):
        print(f"\n--- Iteration {iteration + 1} ---")

        # Get LLM response
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        print("Response:", response.content)
        print("\nTool calls in response:")

        # Check if there are tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "unknown")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "unknown")

                print(f"  - Tool: {tool_name}")
                print(f"    Args: {tool_args}")

                # Execute tool call using the tool object
                if tool_name in tool_dict:
                    tool = tool_dict[tool_name]
                    try:
                        # Call the tool using LangChain's invoke/ainvoke method
                        if hasattr(tool, "ainvoke"):
                            tool_result = await tool.ainvoke(tool_args)
                        elif hasattr(tool, "invoke"):
                            tool_result = tool.invoke(tool_args)
                        else:
                            # Fallback: try to call directly if it's callable
                            tool_result = tool(**tool_args) if callable(tool) else None
                        print(f"    Result: {tool_result}")

                        # Add tool result to messages
                        messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_id))
                    except Exception as e:
                        error_msg = f"Error executing tool: {str(e)}"
                        print(f"    Error: {error_msg}")
                        messages.append(ToolMessage(content=error_msg, tool_call_id=tool_id))
                else:
                    error_msg = f"Tool '{tool_name}' not found"
                    print(f"    Error: {error_msg}")
                    messages.append(ToolMessage(content=error_msg, tool_call_id=tool_id))
        else:
            print("  No tool calls found - final answer received")
            break

    print(f"\n--- Final Answer ---")
    print(f"Final response: {messages[-1].content}")


if __name__ == "__main__":
    asyncio.run(main())

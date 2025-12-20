from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

role_definition = open("prompts/main.md").read()


system_message = SystemMessage(content=open("prompts/core/system.md").read())
ai_ok_message = AIMessage(content=open("prompts/core/ai-ok.md").read())
role_play_message = HumanMessage(content=open("prompts/core/role_play.md").read() + "\n\n" + role_definition)
ai_ok2_message = AIMessage(content=open("prompts/core/ai-ok2.md").read())


preset_messages = [system_message, ai_ok_message, role_play_message, ai_ok2_message]

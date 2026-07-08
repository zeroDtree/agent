from typing import Any


def extract_text_from_content_blocks(content: Any) -> str:
    """
    Extract text content from MCP tool response content blocks.

    MCP tools may return content as a list of content blocks like:
    [{'type': 'text', 'text': '15', 'id': '...'}]
    This function converts such formats to a plain string.
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and "text" in block:
                    texts.append(str(block["text"]))
                elif "content" in block:
                    texts.append(str(block["content"]))
                elif "text" in block:
                    texts.append(str(block["text"]))
            elif isinstance(block, str):
                texts.append(block)
        return "\n".join(texts) if texts else str(content)
    else:
        return str(content)

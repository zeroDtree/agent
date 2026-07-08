"""
CLI rendering for chat turns using plain stdout (no Rich).

Streaming uses direct writes per LangChain chunk so tokens appear as they arrive.
Tool calls are rendered only from values events (complete state after each node).
"""

from __future__ import annotations

import json
import sys
from typing import TextIO

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from ..graphs.tool_call_format import format_tool_call_line, tool_calls_payload


def message_text(msg: AIMessage | AIMessageChunk | ToolMessage) -> str:
    """Visible assistant answer text (excludes reasoning-only blocks when typed in content)."""
    content = getattr(msg, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type")
                if btype in ("reasoning", "thinking"):
                    continue
                if block.get("type") == "text" or "text" in block:
                    parts.append(str(block.get("text", "")))
                elif "content" in block:
                    parts.append(str(block["content"]))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return ""


def reasoning_text(msg: AIMessage | AIMessageChunk) -> str:
    raw = getattr(msg, "additional_kwargs", None)
    if not isinstance(raw, dict):
        return ""
    reasoning_content = raw.get("reasoning_content")
    return reasoning_content if isinstance(reasoning_content, str) else ""


def tail_ai_tool_messages(messages: list) -> list:
    recent: list = []
    for msg in reversed(messages):
        if isinstance(msg, (AIMessage, ToolMessage)):
            recent.append(msg)
        else:
            break
    return list(reversed(recent))


class CLIStreamRenderer:
    def __init__(
        self,
        show_reasoning: bool,
        *,
        model_name: str = "Assistant",
        out: TextIO | None = None,
    ) -> None:
        self._out = out if out is not None else sys.stdout
        self.show_reasoning = show_reasoning
        self.model_name = model_name
        self.reset_for_turn()

    def reset_for_turn(self) -> None:
        self.streaming_printed_tool_keys: set = set()
        self.streaming_appended_history_keys: set = set()
        self.nonstreaming_emitted_message_keys: set = set()
        self.emitted_tool_call_ids: set[str] = set()
        self._reset_ai_segment()

    def _reset_ai_segment(self) -> None:
        self.stream_reasoning_started = False
        self.stream_answer_started = False
        self.streamed_ai = False

    def _write(self, s: str = "", *, end: str = "\n") -> None:
        print(s, end=end, file=self._out, flush=True)

    def consume_stream_part(self, part: dict, turn_tail_messages: list) -> None:
        if part["type"] == "messages":
            msg, _meta = part["data"]
            if isinstance(msg, AIMessageChunk):
                self._print_chunk(msg)
            elif isinstance(msg, AIMessage):
                if not self.streamed_ai:
                    self._print_full_ai_message(msg, tty_char_stream=True)
                else:
                    body = message_text(msg)
                    if body and not self.stream_answer_started:
                        if self.show_reasoning:
                            self._write()
                            self._write("[Answer]")
                        self.stream_answer_started = True
                        self.streamed_ai = True
                        print(body, end="", file=self._out, flush=True)
            elif isinstance(msg, ToolMessage):
                tid = getattr(msg, "id", None) or hash(str(msg.content))
                if tid not in self.streaming_printed_tool_keys:
                    self._reset_ai_segment()
                    self._print_tool_message(msg)
                    self.streaming_printed_tool_keys.add(tid)
            return

        if part["type"] == "values":
            state = part["data"]
            msgs = state.get("messages") or []
            for msg in tail_ai_tool_messages(msgs):
                mid = getattr(msg, "id", None) or hash(str(msg.content))
                if mid in self.streaming_appended_history_keys:
                    continue
                if isinstance(msg, AIMessage):
                    self._emit_tool_calls(msg)
                turn_tail_messages.append(msg)
                self.streaming_appended_history_keys.add(mid)

    def finish_stream_turn(self) -> None:
        if self.streamed_ai:
            self._write()

    def consume_nonstream_event(self, event: dict, turn_tail_messages: list) -> None:
        msgs = event.get("messages") or []
        if not msgs:
            return
        for msg in tail_ai_tool_messages(msgs):
            msg_id = getattr(msg, "id", None) or hash(str(msg.content))
            if msg_id in self.nonstreaming_emitted_message_keys:
                continue
            if isinstance(msg, AIMessage):
                self._emit_tool_calls(msg)
                self._print_full_ai_message(msg, tty_char_stream=False)
            elif isinstance(msg, ToolMessage):
                self._print_tool_message(msg)
            self.nonstreaming_emitted_message_keys.add(msg_id)
            turn_tail_messages.append(msg)

    def _emit_tool_calls(self, msg: AIMessage) -> None:
        tool_calls = tool_calls_payload(msg)
        if not tool_calls:
            return
        if self.streamed_ai:
            self._write()
        for tc in tool_calls:
            raw_name = tc.get("name")
            if raw_name is None or not str(raw_name).strip():
                continue
            call_id = tc.get("id")
            dedupe_key = str(call_id) if call_id else f"{raw_name}:{format_tool_call_line(str(raw_name), tc.get('args'))}"
            if dedupe_key in self.emitted_tool_call_ids:
                continue
            self.emitted_tool_call_ids.add(dedupe_key)
            self._write(format_tool_call_line(str(raw_name), tc.get("args")))

    def _print_chunk(self, msg: AIMessageChunk) -> None:
        reasoning = reasoning_text(msg) if self.show_reasoning else ""
        text = message_text(msg)
        if reasoning:
            if not self.stream_reasoning_started:
                self._write()
                self._write("[Reasoning]")
                self.stream_reasoning_started = True
            self.streamed_ai = True
            print(reasoning, end="", file=self._out, flush=True)
        if text:
            if not self.stream_answer_started:
                if self.show_reasoning:
                    self._write()
                    self._write("[Answer]")
                self.stream_answer_started = True
            self.streamed_ai = True
            print(text, end="", file=self._out, flush=True)

    def _print_tool_message(self, msg: ToolMessage) -> None:
        title = f"Tool: {msg.name}"
        content_raw = msg.content
        if isinstance(content_raw, str):
            try:
                parsed = json.loads(content_raw)
                body = json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                body = content_raw
        else:
            body = str(content_raw)
        width = max(len(title) + 4, 44)
        bar = "=" * width
        self._write(bar)
        self._write(f" {title}")
        self._write(bar)
        self._write(body)
        self._write(bar)

    def _stream_plain_chars(self, text: str) -> None:
        for ch in text:
            print(ch, end="", file=self._out, flush=True)

    def _print_full_ai_message(self, msg: AIMessage, *, tty_char_stream: bool) -> None:
        reasoning = reasoning_text(msg) if self.show_reasoning else ""
        body = message_text(msg)
        if tty_char_stream:
            if reasoning:
                self._write()
                self._write("[Reasoning]")
                self._stream_plain_chars(reasoning)
                self._write()
            if body:
                self._write("[Answer]")
                self._stream_plain_chars(body)
                self._write()
            return
        if reasoning:
            self._write()
            self._write("--- Thinking ---")
            self._write(reasoning)
        if body:
            self._write()
            self._write(f"--- {self.model_name} ---")
            self._write(body)

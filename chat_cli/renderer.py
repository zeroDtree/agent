"""
CLI rendering for chat turns using plain stdout (no Rich).

Streaming uses direct writes per LangChain chunk so tokens appear as they arrive.
When the graph emits a full ``AIMessage`` without chunks, reasoning/body can be
printed character-by-character so the UI still feels like a stream.
"""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage


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


def _tool_calls_payload(msg: AIMessage | AIMessageChunk) -> list[dict[str, Any]]:
    raw = getattr(msg, "tool_calls", None)
    if not raw:
        return []
    out: list[dict[str, Any]] = []
    for tc in raw:
        if isinstance(tc, dict):
            out.append(tc)
        else:
            name = getattr(tc, "name", None)
            args = getattr(tc, "args", None)
            tid = getattr(tc, "id", None)
            out.append({"name": name, "args": args, "id": tid})
    return out


def _format_tool_call_args(args: Any) -> str:
    if args is None:
        return "{}"
    if isinstance(args, str):
        return args
    try:
        return json.dumps(args, ensure_ascii=False)
    except TypeError:
        return str(args)


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
        self.streaming_emitted_tool_call_keys: set = set()
        self.streamed_ai = False
        self.stream_reasoning_started = False
        self.stream_answer_started = False

    def _write(self, s: str = "", *, end: str = "\n") -> None:
        print(s, end=end, file=self._out, flush=True)

    def consume_stream_part(self, part: dict, turn_tail_messages: list) -> None:
        if part["type"] == "messages":
            msg, _meta = part["data"]
            if isinstance(msg, AIMessageChunk):
                self._emit_tool_calls_stream(msg)
                self._print_chunk(msg)
            elif isinstance(msg, AIMessage):
                self._emit_tool_calls_stream(msg)
                if not self.streamed_ai:
                    self._print_full_ai_message(msg, tty_char_stream=True)
                else:
                    # Thinking/reasoning often streams in chunks with empty `content`; the
                    # final AIMessage carries the visible answer. Do not skip it when
                    # stream_answer_started is still False.
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
                self._emit_tool_calls_nonstream(msg)
                self._print_full_ai_message(msg, tty_char_stream=False)
            elif isinstance(msg, ToolMessage):
                self._print_tool_message(msg)
            self.nonstreaming_emitted_message_keys.add(msg_id)
            turn_tail_messages.append(msg)

    def _tool_call_key(self, tc: dict[str, Any]) -> int:
        tid = tc.get("id")
        name = tc.get("name", "")
        args = tc.get("args")
        return hash((tid, name, _format_tool_call_args(args)))

    def _emit_tool_calls_stream(self, msg: AIMessage | AIMessageChunk) -> None:
        for tc in _tool_calls_payload(msg):
            raw_name = tc.get("name")
            if raw_name is None or not str(raw_name).strip():
                continue
            key = self._tool_call_key(tc)
            if key in self.streaming_emitted_tool_call_keys:
                continue
            self.streaming_emitted_tool_call_keys.add(key)
            name = raw_name or "?"
            args_s = _format_tool_call_args(tc.get("args"))
            self._write(f"→ tool {name} {args_s}")

    def _emit_tool_calls_nonstream(self, msg: AIMessage) -> None:
        self._emit_tool_calls_stream(msg)

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

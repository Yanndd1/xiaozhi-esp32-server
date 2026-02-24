import json
import uuid
from types import SimpleNamespace

import anthropic

from config.logger import setup_logging
from core.utils.util import check_model_key
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name", "claude-sonnet-4-20250514")
        self.api_key = config.get("api_key")
        self.max_tokens = int(config.get("max_tokens", 1024))
        self.temperature = float(config.get("temperature", 0.7)) if config.get("temperature") is not None else None

        model_key_msg = check_model_key("LLM", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

        self.client = anthropic.Anthropic(api_key=self.api_key)

    @staticmethod
    def _extract_system_message(dialogue):
        """Extract system message and convert dialogue to Anthropic format.

        Handles:
        - Extracting system message (Anthropic uses separate parameter)
        - Converting OpenAI tool_calls in assistant messages to Anthropic tool_use blocks
        - Converting OpenAI role="tool" messages to Anthropic tool_result user messages
        """
        system_content = ""
        filtered_messages = []

        for msg in dialogue:
            role = msg.get("role", "user")

            if role == "system":
                system_content = msg.get("content", "")
                continue

            # Assistant message with tool_calls (OpenAI format -> Anthropic format)
            if role == "assistant" and msg.get("tool_calls"):
                content_blocks = []
                text_content = msg.get("content", "")
                if text_content:
                    content_blocks.append({"type": "text", "text": text_content})
                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    try:
                        args = json.loads(func.get("arguments", "{}") or "{}")
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", uuid.uuid4().hex),
                        "name": func.get("name", ""),
                        "input": args,
                    })
                if content_blocks:
                    filtered_messages.append({"role": "assistant", "content": content_blocks})
                continue

            # Tool result message (OpenAI format -> Anthropic format)
            if role == "tool":
                filtered_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": msg.get("content", ""),
                    }],
                })
                continue

            # Regular user/assistant messages
            content = msg.get("content", "") or ""
            if role == "assistant" and not content:
                continue
            filtered_messages.append({"role": role, "content": content})

        # Ensure messages start with a user message
        if filtered_messages and filtered_messages[0].get("role") != "user":
            filtered_messages.insert(0, {"role": "user", "content": "Hello"})

        # Ensure no consecutive same-role messages (merge or insert synthetic)
        merged = []
        for msg in filtered_messages:
            if merged and merged[-1]["role"] == msg["role"]:
                if msg["role"] == "user":
                    # Merge consecutive user messages
                    prev_content = merged[-1]["content"]
                    new_content = msg["content"]
                    if isinstance(prev_content, str) and isinstance(new_content, str):
                        merged[-1]["content"] = prev_content + "\n" + new_content
                    elif isinstance(prev_content, list) and isinstance(new_content, list):
                        merged[-1]["content"] = prev_content + new_content
                    elif isinstance(prev_content, str) and isinstance(new_content, list):
                        merged[-1]["content"] = [{"type": "text", "text": prev_content}] + new_content
                    elif isinstance(prev_content, list) and isinstance(new_content, str):
                        merged[-1]["content"] = prev_content + [{"type": "text", "text": new_content}]
                else:
                    # Insert synthetic user message between consecutive assistant messages
                    merged.append({"role": "user", "content": "Continue."})
                    merged.append(msg)
            else:
                merged.append(msg)

        return system_content, merged

    @staticmethod
    def _convert_tools(openai_tools):
        """Convert OpenAI tool format to Anthropic tool format.

        OpenAI:  [{"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}]
        Anthropic: [{"name": ..., "description": ..., "input_schema": {...}}]
        """
        if not openai_tools:
            return None
        anthropic_tools = []
        for tool in openai_tools:
            func = tool.get("function", tool)
            anthropic_tools.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
            })
        return anthropic_tools

    def response(self, session_id, dialogue, **kwargs):
        """Streaming text response (no function calling)."""
        system_content, messages = self._extract_system_message(dialogue)

        request_params = {
            "model": self.model_name,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "messages": messages,
        }
        if system_content:
            request_params["system"] = system_content
        if self.temperature is not None:
            request_params["temperature"] = self.temperature

        with self.client.messages.stream(**request_params) as stream:
            for text in stream.text_stream:
                if text:
                    yield text

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        """Streaming response with function calling support.

        Yields (content, tool_calls) tuples matching the contract in
        connection.py _merge_tool_calls:
          tool_calls is a list of SimpleNamespace with .id, .function.name, .function.arguments
        """
        if not functions:
            for token in self.response(session_id, dialogue, **kwargs):
                yield token, None
            return

        system_content, messages = self._extract_system_message(dialogue)

        request_params = {
            "model": self.model_name,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "messages": messages,
        }
        if system_content:
            request_params["system"] = system_content
        if self.temperature is not None:
            request_params["temperature"] = self.temperature

        anthropic_tools = self._convert_tools(functions)
        if anthropic_tools:
            request_params["tools"] = anthropic_tools

        # Track current tool_use block being built (buffered approach like Gemini)
        current_tool_id = None
        current_tool_name = None
        current_tool_args = ""

        try:
            with self.client.messages.stream(**request_params) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        if hasattr(event, "content_block"):
                            if getattr(event.content_block, "type", None) == "tool_use":
                                current_tool_id = event.content_block.id
                                current_tool_name = event.content_block.name
                                current_tool_args = ""

                    elif event.type == "content_block_delta":
                        # Use .type discriminator for reliable delta detection
                        if event.delta.type == "text_delta":
                            yield event.delta.text, None
                        elif event.delta.type == "input_json_delta":
                            current_tool_args += event.delta.partial_json

                    elif event.type == "content_block_stop":
                        # If we were building a tool call, yield it complete
                        if current_tool_name:
                            tool_call = SimpleNamespace(
                                id=current_tool_id or uuid.uuid4().hex,
                                index=None,
                                function=SimpleNamespace(
                                    name=current_tool_name,
                                    arguments=current_tool_args,
                                ),
                            )
                            yield None, [tool_call]
                            current_tool_id = None
                            current_tool_name = None
                            current_tool_args = ""

        except anthropic.APIError as e:
            logger.bind(tag=TAG).error(f"Claude API error: {e}")
            raise

        # End marker (like Gemini provider)
        yield None, None

"""Bush League Co-Pilot agent loop with SSE streaming."""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

import anthropic

from backend.config import ANTHROPIC_API_KEY, LLM_MODEL, LLM_MAX_TOKENS
from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.tools import TOOLS, execute_tool

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 4


def _build_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def stream_copilot_response(
    user_message: str,
    conversation_history: list[dict] | None = None,
) -> AsyncGenerator[dict, None]:
    """Async generator yielding SSE-formatted events.

    Events:
        {"event": "text_delta", "data": "<chunk>"}
        {"event": "tool_use",   "data": "<tool_name>"}
        {"event": "done",       "data": ""}
        {"event": "error",      "data": "<message>"}
    """
    client = _build_client()

    messages: list[dict] = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    tool_rounds = 0

    try:
        while True:
            response = client.messages.create(
                model=LLM_MODEL,
                max_tokens=LLM_MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=TOOLS,
            )

            tool_use_blocks = [
                b for b in response.content if b.type == "tool_use"
            ]
            text_blocks = [
                b for b in response.content if b.type == "text"
            ]

            if not tool_use_blocks:
                for block in text_blocks:
                    yield {"event": "text_delta", "data": block.text}
                break

            if tool_rounds >= MAX_TOOL_ROUNDS:
                yield {
                    "event": "text_delta",
                    "data": "I've gathered enough information. Let me summarize what I found.",
                }
                break

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in tool_use_blocks:
                yield {"event": "tool_use", "data": block.name}
                logger.info("Tool call: %s(%s)", block.name, block.input)

                try:
                    result = await execute_tool(block.name, block.input)
                except Exception as exc:
                    logger.exception("Tool %s failed", block.name)
                    result = json.dumps({"error": str(exc)})

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})
            tool_rounds += 1

    except anthropic.APIError as exc:
        logger.exception("Anthropic API error")
        yield {"event": "error", "data": f"API error: {exc.message}"}
    except Exception as exc:
        logger.exception("Copilot error")
        yield {"event": "error", "data": str(exc)}

    yield {"event": "done", "data": ""}

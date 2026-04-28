"""
Monkey-patch langchain_openai to preserve reasoning_content for DeepSeek
thinking mode.  Patches three functions:

1. ``_convert_delta_to_message_chunk`` — captures reasoning_content from
   streaming delta into AIMessageChunk.additional_kwargs (INPUT direction).
2. ``_convert_dict_to_message`` — captures reasoning_content from non-streaming
   response dict into AIMessage.additional_kwargs (INPUT direction).
3. ``_convert_message_to_dict`` — injects reasoning_content from AIMessage
   back into the API request dict (OUTPUT direction).

DeepSeek's API requires that reasoning_content from previous assistant
messages be passed back in subsequent requests.  ChatOpenAI (and
ChatDeepSeek which inherits from it) drops this field, causing
a 400 error on multi-turn conversations.

This patch is idempotent — calling apply() multiple times is safe.
"""

from __future__ import annotations

from typing import Any, Literal, Mapping, cast

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.messages.ai import AIMessageChunk
from loguru import logger

_original_convert_to_dict = None
_original_convert_delta = None
_original_convert_dict = None


def apply() -> None:
    """Install all monkey-patches.  Safe to call multiple times."""
    global _original_convert_to_dict, _original_convert_delta, _original_convert_dict

    import langchain_openai.chat_models.base as base_mod

    # ── 1. _convert_delta_to_message_chunk (streaming INPUT) ──────
    if _original_convert_delta is None:
        _original_convert_delta = base_mod._convert_delta_to_message_chunk

        def _patched_convert_delta_to_message_chunk(
            _dict: Mapping[str, Any],
            default_class: type,
        ):
            # Capture reasoning_content from delta BEFORE the original builds the chunk
            reasoning = _dict.get("reasoning_content")
            chunk = _original_convert_delta(_dict, default_class)
            if reasoning and isinstance(chunk, AIMessageChunk):
                chunk.additional_kwargs["reasoning_content"] = reasoning
                logger.debug(
                    f"[deepseek_patch] Captured reasoning_content "
                    f"({len(reasoning)} chars) in streaming delta"
                )
            return chunk

        base_mod._convert_delta_to_message_chunk = _patched_convert_delta_to_message_chunk
        logger.info("Monkey-patched _convert_delta_to_message_chunk for reasoning_content capture")

    # ── 2. _convert_dict_to_message (non-streaming INPUT) ─────────
    if _original_convert_dict is None:
        _original_convert_dict = base_mod._convert_dict_to_message

        def _patched_convert_dict_to_message(_dict: Mapping[str, Any]):
            # Capture reasoning_content BEFORE the original builds the message
            reasoning = _dict.get("reasoning_content")
            msg = _original_convert_dict(_dict)
            if reasoning and isinstance(msg, AIMessage):
                msg.additional_kwargs["reasoning_content"] = reasoning
                logger.debug(
                    f"[deepseek_patch] Captured reasoning_content "
                    f"({len(reasoning)} chars) in non-streaming response"
                )
            return msg

        base_mod._convert_dict_to_message = _patched_convert_dict_to_message
        logger.info("Monkey-patched _convert_dict_to_message for reasoning_content capture")

    # ── 3. _convert_message_to_dict (OUTPUT) ──────────────────────
    if _original_convert_to_dict is None:
        _original_convert_to_dict = base_mod._convert_message_to_dict

        def _patched_convert_message_to_dict(
            message: BaseMessage,
            api: Literal["chat/completions", "responses"] = "chat/completions",
        ) -> dict[str, Any]:
            message_dict = _original_convert_to_dict(message, api)

            if isinstance(message, AIMessage):
                reasoning = message.additional_kwargs.get("reasoning_content")
                if reasoning:
                    message_dict["reasoning_content"] = reasoning
                    logger.debug(
                        f"[deepseek_patch] Injected reasoning_content "
                        f"({len(reasoning)} chars) into API request"
                    )

            return message_dict

        base_mod._convert_message_to_dict = _patched_convert_message_to_dict
        logger.info("Monkey-patched _convert_message_to_dict for reasoning_content passthrough")

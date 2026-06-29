"""In-memory fake SDK clients used by tests.

Mirrors the minimal surface of the real Anthropic / OpenAI client
objects that the backends touch (``messages.create`` for Anthropic,
``chat.completions.create`` for OpenAI), including the ``stop_reason`` /
``finish_reason`` and token-``usage`` fields the backends map onto
``BackendResult``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AnthropicBlock:
    text: str


@dataclass
class AnthropicUsage:
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cache_read_input_tokens: Optional[int] = None
    cache_creation_input_tokens: Optional[int] = None


@dataclass
class AnthropicResponse:
    content: List[AnthropicBlock]
    stop_reason: Optional[str] = None
    usage: Optional[AnthropicUsage] = None


@dataclass
class AnthropicMessages:
    calls: List[dict] = field(default_factory=list)
    response_text: str = "hello"
    stop_reason: str = "end_turn"
    raise_exc: Optional[BaseException] = None

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc is not None:
            exc = self.raise_exc
            self.raise_exc = None
            raise exc
        return AnthropicResponse(
            content=[AnthropicBlock(text=self.response_text)],
            stop_reason=self.stop_reason,
            usage=AnthropicUsage(input_tokens=11, output_tokens=7),
        )


class FakeAnthropicClient:
    def __init__(self, *_, **__):
        self.messages = AnthropicMessages()


@dataclass
class OpenAIPromptTokensDetails:
    cached_tokens: Optional[int] = None


@dataclass
class OpenAIUsage:
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    prompt_tokens_details: Optional[OpenAIPromptTokensDetails] = None


@dataclass
class OpenAIMessage:
    content: str


@dataclass
class OpenAIChoice:
    message: OpenAIMessage
    finish_reason: Optional[str] = None


@dataclass
class OpenAIResponse:
    choices: List[OpenAIChoice]
    usage: Optional[OpenAIUsage] = None


@dataclass
class OpenAIChatCompletions:
    calls: List[dict] = field(default_factory=list)
    response_text: str = "hello"
    finish_reason: str = "stop"
    raise_exc: Optional[BaseException] = None

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc is not None:
            exc = self.raise_exc
            self.raise_exc = None
            raise exc
        return OpenAIResponse(
            choices=[
                OpenAIChoice(
                    message=OpenAIMessage(content=self.response_text),
                    finish_reason=self.finish_reason,
                )
            ],
            usage=OpenAIUsage(
                prompt_tokens=13,
                completion_tokens=9,
                prompt_tokens_details=OpenAIPromptTokensDetails(cached_tokens=4),
            ),
        )


class FakeOpenAIChat:
    def __init__(self):
        self.completions = OpenAIChatCompletions()


class FakeOpenAIClient:
    def __init__(self, *_, **__):
        self.chat = FakeOpenAIChat()

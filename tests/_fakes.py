"""In-memory fake SDK clients used by tests.

Mirrors the minimal surface of the real Anthropic / OpenAI client
objects that the backends touch (``messages.create`` for Anthropic,
``chat.completions.create`` for OpenAI).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AnthropicBlock:
    text: str


@dataclass
class AnthropicResponse:
    content: List[AnthropicBlock]


@dataclass
class AnthropicMessages:
    calls: List[dict] = field(default_factory=list)
    response_text: str = "hello"
    raise_exc: Optional[BaseException] = None

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc is not None:
            exc = self.raise_exc
            self.raise_exc = None
            raise exc
        return AnthropicResponse(content=[AnthropicBlock(text=self.response_text)])


class FakeAnthropicClient:
    def __init__(self, *_, **__):
        self.messages = AnthropicMessages()


@dataclass
class OpenAIMessage:
    content: str


@dataclass
class OpenAIChoice:
    message: OpenAIMessage


@dataclass
class OpenAIResponse:
    choices: List[OpenAIChoice]


@dataclass
class OpenAIChatCompletions:
    calls: List[dict] = field(default_factory=list)
    response_text: str = "hello"
    raise_exc: Optional[BaseException] = None

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc is not None:
            exc = self.raise_exc
            self.raise_exc = None
            raise exc
        return OpenAIResponse(choices=[OpenAIChoice(message=OpenAIMessage(content=self.response_text))])


class FakeOpenAIChat:
    def __init__(self):
        self.completions = OpenAIChatCompletions()


class FakeOpenAIClient:
    def __init__(self, *_, **__):
        self.chat = FakeOpenAIChat()

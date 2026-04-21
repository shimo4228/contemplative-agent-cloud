"""Concrete LLMBackend implementations for managed providers."""

from contemplative_agent_cloud.backends.anthropic import AnthropicBackend
from contemplative_agent_cloud.backends.openai import OpenAIBackend

__all__ = ["AnthropicBackend", "OpenAIBackend"]

"""Optional managed-LLM backends for contemplative-agent.

Installing this package and configuring an API key routes every
generation call in contemplative-agent (distill, insight,
amend-constitution, post, comment, reply, dialogue)
through the selected provider's API. Embeddings continue to use the
local Ollama ``nomic-embed-text`` model.

The main repository's default stack (Ollama + gemma4:e4b, ADR-0069) is unchanged
and never reaches the network on its own — activating a cloud backend
requires this package plus an explicit opt-in via environment variables
or programmatic ``configure(backend=...)`` call.
"""

from contemplative_agent_cloud.backends.anthropic import AnthropicBackend
from contemplative_agent_cloud.backends.openai import OpenAIBackend

__all__ = ["AnthropicBackend", "OpenAIBackend"]
__version__ = "0.1.0"

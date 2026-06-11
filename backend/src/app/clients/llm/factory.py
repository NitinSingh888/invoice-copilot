from __future__ import annotations

from typing import TYPE_CHECKING

from .base import LLMClient
from .failover import FailoverClient
from .mock_client import MockClient

if TYPE_CHECKING:
    from app.core.config import Settings


def build_llm_client(settings: "Settings") -> LLMClient:
    """Build an LLMClient based on the configured provider.

    Always ends any FailoverClient chain with a MockClient so that the
    system remains functional even when all real providers are unavailable.
    """
    provider = settings.llm_provider.lower()

    if provider == "mock":
        return MockClient()

    if provider == "anthropic":
        if settings.anthropic_api_key:
            from .anthropic_client import AnthropicClient

            return FailoverClient(
                [
                    AnthropicClient(
                        api_key=settings.anthropic_api_key,
                        model=settings.anthropic_model,
                    ),
                    MockClient(),
                ]
            )
        return MockClient()

    if provider == "openai":
        if settings.openai_api_key:
            from .openai_client import OpenAIClient

            return FailoverClient(
                [
                    OpenAIClient(
                        api_key=settings.openai_api_key,
                        model=settings.openai_model,
                    ),
                    MockClient(),
                ]
            )
        return MockClient()

    if provider == "auto":
        from .anthropic_client import AnthropicClient
        from .openai_client import OpenAIClient

        real_clients: list[LLMClient] = []
        if settings.anthropic_api_key:
            real_clients.append(
                AnthropicClient(
                    api_key=settings.anthropic_api_key,
                    model=settings.anthropic_model,
                )
            )
        if settings.openai_api_key:
            real_clients.append(
                OpenAIClient(
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                )
            )
        real_clients.append(MockClient())
        return FailoverClient(real_clients)

    # Unknown provider — fall back to mock
    return MockClient()

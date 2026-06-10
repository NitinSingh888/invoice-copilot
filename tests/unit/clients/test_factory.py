"""Tests for build_llm_client factory."""
from __future__ import annotations

from app.clients.llm.factory import build_llm_client
from app.clients.llm.failover import FailoverClient
from app.clients.llm.mock_client import MockClient
from app.core.config import Settings


def test_factory_mock_provider_returns_mock_client() -> None:
    settings = Settings(llm_provider="mock")
    client = build_llm_client(settings)
    assert isinstance(client, MockClient)


def test_factory_auto_no_keys_returns_failover_ending_in_mock() -> None:
    settings = Settings(llm_provider="auto", anthropic_api_key=None, openai_api_key=None)
    client = build_llm_client(settings)
    assert isinstance(client, FailoverClient)
    # The last client in the chain must be a MockClient
    assert isinstance(client._clients[-1], MockClient)


def test_factory_auto_no_keys_last_is_mock() -> None:
    settings = Settings(llm_provider="auto")
    client = build_llm_client(settings)
    assert isinstance(client, FailoverClient)
    assert client._clients[-1].name == "mock"


def test_factory_anthropic_no_key_returns_mock() -> None:
    settings = Settings(llm_provider="anthropic", anthropic_api_key=None)
    client = build_llm_client(settings)
    # No key → falls back to mock
    assert client.name in ("mock", "failover")
    if isinstance(client, FailoverClient):
        assert isinstance(client._clients[-1], MockClient)
    else:
        assert isinstance(client, MockClient)


def test_factory_anthropic_with_key_returns_failover() -> None:
    settings = Settings(llm_provider="anthropic", anthropic_api_key="sk-test-key")
    client = build_llm_client(settings)
    assert isinstance(client, FailoverClient)
    assert client._clients[-1].name == "mock"
    assert client._clients[0].name == "anthropic"


def test_factory_openai_no_key_returns_mock() -> None:
    settings = Settings(llm_provider="openai", openai_api_key=None)
    client = build_llm_client(settings)
    assert client.name in ("mock", "failover")
    if isinstance(client, FailoverClient):
        assert isinstance(client._clients[-1], MockClient)
    else:
        assert isinstance(client, MockClient)


def test_factory_openai_with_key_returns_failover() -> None:
    settings = Settings(llm_provider="openai", openai_api_key="sk-test-openai")
    client = build_llm_client(settings)
    assert isinstance(client, FailoverClient)
    assert client._clients[-1].name == "mock"
    assert client._clients[0].name == "openai"


def test_factory_unknown_provider_returns_mock() -> None:
    settings = Settings(llm_provider="unknown_provider")
    client = build_llm_client(settings)
    assert isinstance(client, MockClient)


def test_factory_auto_with_anthropic_key_includes_anthropic() -> None:
    settings = Settings(llm_provider="auto", anthropic_api_key="sk-ant-test")
    client = build_llm_client(settings)
    assert isinstance(client, FailoverClient)
    names = [c.name for c in client._clients]
    assert "anthropic" in names
    assert names[-1] == "mock"

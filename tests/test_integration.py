from __future__ import annotations

import time

import pytest

from hermes_dcma import DCMAMemoryProvider, register


class TestIntegration:
    def test_plugin_lifecycle(self, mock_server: str) -> None:
        provider = register()
        provider._client.base_url = mock_server  # type: ignore[attr-defined]

        assert provider.is_available() is True

        provider.initialize("integration-test-session")

        prefetch_result = provider.prefetch("anything")
        assert prefetch_result == "No relevant memories found."

        provider.handle_tool_call(
            "dcma_remember",
            {"name": "test_concept", "type": "concept", "content": "integration test data"},
        )

        search_result = provider.handle_tool_call("dcma_search", {"query": "integration"})
        assert isinstance(search_result, str)
        assert "test_concept" in search_result

        provider.sync_turn(
            user="What is DCMA?",
            assistant="DCMA is a graph cognition engine.",
        )
        time.sleep(0.1)

        provider.shutdown()

    def test_tool_dispatch_all(self, mock_server: str) -> None:
        provider = register()
        provider._client.base_url = mock_server  # type: ignore[attr-defined]

        provider.initialize("test")

        r1 = provider.handle_tool_call("dcma_search", {"query": "x"})
        assert isinstance(r1, str)

        r2 = provider.handle_tool_call(
            "dcma_remember", {"name": "x", "type": "t"}
        )
        assert isinstance(r2, str)
        assert "x" in r2

        r3 = provider.handle_tool_call("dcma_ingest", {"text": "hello"})
        assert isinstance(r3, str)
        assert "text" in r3

        r4 = provider.handle_tool_call("dcma_graph", {"query": "x"})
        assert isinstance(r4, str)
        assert "atoms" in r4

        r5 = provider.handle_tool_call(
            "dcma_relate", {"source": "a", "target": "b", "type": "link"}
        )
        assert isinstance(r5, str)
        assert "source" in r5

        provider.shutdown()

    def test_register_function(self) -> None:
        provider = register()
        assert isinstance(provider, DCMAMemoryProvider)
        assert provider.name == "dcma"

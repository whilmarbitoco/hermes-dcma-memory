from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from hermes_dcma.provider import DCMAMemoryProvider


@pytest.fixture
def provider(mock_server: str) -> DCMAMemoryProvider:
    p = DCMAMemoryProvider()
    p._client.base_url = mock_server  # type: ignore[attr-defined]
    return p


class TestDCMAMemoryProvider:
    def test_name(self) -> None:
        assert DCMAMemoryProvider.name == "dcma"

    def test_is_available_true(self, provider: DCMAMemoryProvider) -> None:
        assert provider.is_available() is True

    def test_is_available_false(self) -> None:
        provider = DCMAMemoryProvider()
        provider._client.base_url = "http://127.0.0.1:19872"  # type: ignore[attr-defined]
        assert provider.is_available() is False

    def test_initialize(self, provider: DCMAMemoryProvider) -> None:
        provider.initialize("test-session")
        assert provider._session_id == "test-session"

    def test_system_prompt_block_available(self, provider: DCMAMemoryProvider) -> None:
        provider._available = True
        block = provider.system_prompt_block()
        assert "connected" in block

    def test_system_prompt_block_unavailable(self, provider: DCMAMemoryProvider) -> None:
        provider._available = False
        block = provider.system_prompt_block()
        assert "unavailable" in block

    def test_prefetch_with_results(self, provider: DCMAMemoryProvider) -> None:
        provider._client.remember("memory1", "note", content="important info")
        result = provider.prefetch("memory")
        assert "memory1" in result
        assert "important info" in result

    def test_prefetch_no_results(self, provider: DCMAMemoryProvider) -> None:
        result = provider.prefetch("zzzzzznonexistent")
        assert "No relevant memories found" in result

    def test_tool_schemas(self, provider: DCMAMemoryProvider) -> None:
        schemas = provider.get_tool_schemas()
        names = {s["name"] for s in schemas}
        expected = {
            "dcma_search",
            "dcma_remember",
            "dcma_ingest",
            "dcma_graph",
            "dcma_relate",
        }
        assert names == expected

    def test_handle_tool_call_search(self, provider: DCMAMemoryProvider) -> None:
        provider._client.remember("found_item", "test")
        result = provider.handle_tool_call("dcma_search", {"query": "found"})
        assert isinstance(result, str)
        assert "found_item" in result

    def test_handle_tool_call_remember(self, provider: DCMAMemoryProvider) -> None:
        result = provider.handle_tool_call(
            "dcma_remember",
            {"name": "new_atom", "type": "concept", "content": "test content"},
        )
        assert isinstance(result, str)
        assert "new_atom" in result

    def test_handle_tool_call_ingest(self, provider: DCMAMemoryProvider) -> None:
        result = provider.handle_tool_call("dcma_ingest", {"text": "hello world"})
        assert isinstance(result, str)
        assert "text" in result

    def test_handle_tool_call_graph(self, provider: DCMAMemoryProvider) -> None:
        result = provider.handle_tool_call("dcma_graph", {"query": "test"})
        assert isinstance(result, str)
        assert "atoms" in result

    def test_handle_tool_call_relate(self, provider: DCMAMemoryProvider) -> None:
        result = provider.handle_tool_call(
            "dcma_relate", {"source": "a", "target": "b", "type": "link"}
        )
        assert isinstance(result, str)
        assert "source" in result

    def test_handle_tool_call_unknown(self, provider: DCMAMemoryProvider) -> None:
        result = provider.handle_tool_call("dcma_unknown", {})
        assert "error" in result

    def test_handle_tool_call_error(self, provider: DCMAMemoryProvider) -> None:
        provider._client.base_url = "http://127.0.0.1:19873"  # type: ignore[attr-defined]
        result = provider.handle_tool_call("dcma_search", {"query": "x"})
        assert isinstance(result, str)
        assert "error" in result

    def test_sync_turn_passive_learning(self, provider: DCMAMemoryProvider) -> None:
        provider.initialize("session-passive")
        provider.sync_turn(
            user="I prefer dark backgrounds.",
            assistant="Noted.",
            session_id="session-passive",
        )
        time.sleep(0.1)

        atoms = provider._client.list_atoms()  # type: ignore[attr-defined]
        assert any(
            atom["name"].startswith("passive-preference")
            and "dark backgrounds" in atom.get("content", "")
            for atom in atoms
        )

    def test_shutdown(self, provider: DCMAMemoryProvider) -> None:
        provider.shutdown()

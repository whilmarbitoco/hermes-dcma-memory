from __future__ import annotations

import pytest

from hermes_dcma.client import DCMAClient, DCMAError


class TestDCMAClient:
    def test_health(self, mock_server: str) -> None:
        client = DCMAClient(base_url=mock_server)
        result = client.health()
        assert result == {"status": "ok"}

    def test_search(self, mock_server: str) -> None:
        client = DCMAClient(base_url=mock_server)
        client.remember("test_atom", "test", content="hello world")
        results = client.search("hello")
        assert len(results) == 1
        assert results[0]["name"] == "test_atom"

    def test_search_empty(self, mock_server: str) -> None:
        client = DCMAClient(base_url=mock_server)
        results = client.search("nonexistent")
        assert results == []

    def test_search_handles_structured_payload(self, mock_server: str) -> None:
        client = DCMAClient(base_url=mock_server)
        client.remember("structured_atom", "test", content="structured payload")
        results = client.search("structured")
        assert isinstance(results, list)
        assert results[0]["name"] == "structured_atom"

    def test_remember(self, mock_server: str) -> None:
        client = DCMAClient(base_url=mock_server)
        result = client.remember(
            "my_atom",
            "concept",
            content="some content",
            tags=["ai", "memory"],
            attributes={"key": "val"},
        )
        assert result["name"] == "my_atom"
        assert result["type"] == "concept"
        assert result["content"] == "some content"
        assert result["tags"] == ["ai", "memory"]
        assert result["attributes"] == {"key": "val"}

    def test_remember_minimal(self, mock_server: str) -> None:
        client = DCMAClient(base_url=mock_server)
        result = client.remember("minimal", "note")
        assert result["name"] == "minimal"
        assert result["type"] == "note"

    def test_graph(self, mock_server: str) -> None:
        client = DCMAClient(base_url=mock_server)
        client.remember("node_a", "entity")
        client.remember("node_b", "entity")
        client.relate("node_a", "node_b", "connects_to")
        result = client.graph("node")
        assert "atoms" in result
        assert "relations" in result

    def test_relate(self, mock_server: str) -> None:
        client = DCMAClient(base_url=mock_server)
        result = client.relate("src", "dst", "related_to")
        assert result["source"] == "src"
        assert result["target"] == "dst"
        assert result["type"] == "related_to"

    def test_ingest(self, mock_server: str) -> None:
        client = DCMAClient(base_url=mock_server)
        result = client.ingest("Alice knows Bob")
        assert "entities" in result
        assert "relations" in result

    def test_tick(self, mock_server: str) -> None:
        client = DCMAClient(base_url=mock_server)
        result = client.tick()
        assert result["status"] == "ok"

    def test_list_atoms(self, mock_server: str) -> None:
        client = DCMAClient(base_url=mock_server)
        client.remember("a1", "type1")
        client.remember("a2", "type2")
        atoms = client.list_atoms(limit=10)
        assert len(atoms) == 2
        names = [a["name"] for a in atoms]
        assert "a1" in names
        assert "a2" in names

    def test_get_contradictions(self, mock_server: str) -> None:
        client = DCMAClient(base_url=mock_server)
        result = client.get_contradictions()
        assert result == []

    def test_connection_error(self) -> None:
        client = DCMAClient(base_url="http://127.0.0.1:19871")
        with pytest.raises(DCMAError):
            client.health()

    def test_timeout(self) -> None:
        client = DCMAClient(base_url="http://203.0.113.1:3030")
        with pytest.raises(DCMAError):
            client.health()

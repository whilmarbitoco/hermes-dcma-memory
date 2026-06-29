from __future__ import annotations

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Generator
from urllib.parse import urlparse, parse_qs

import pytest


class MockDCMAHandler(BaseHTTPRequestHandler):
    atoms: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []

    def _json_response(self, data: Any, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        if not raw:
            return {}
        return json.loads(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/health":
            self._json_response({"status": "ok"})

        elif path == "/search":
            q = params.get("q", [""])[0]
            limit = int(params.get("limit", ["10"])[0])
            results = [
                a for a in self.atoms
                if q.lower() in a.get("name", "").lower()
                or q.lower() in a.get("content", "").lower()
            ]
            self._json_response(results[:limit])

        elif path == "/graph":
            q = params.get("q", [""])[0]
            self._json_response({
                "atoms": [a for a in self.atoms if q.lower() in a.get("name", "").lower()],
                "relations": self.relations,
            })

        elif path == "/atoms":
            limit = int(params.get("limit", ["100"])[0])
            self._json_response(self.atoms[:limit])

        elif path == "/contradictions":
            self._json_response([])

        else:
            self._json_response({"error": "not found"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        if path == "/remember":
            atom = {
                "id": len(self.atoms) + 1,
                "name": body.get("name", ""),
                "type": body.get("type", ""),
                "content": body.get("content"),
                "tags": body.get("tags", []),
                "attributes": body.get("attributes", {}),
            }
            self.atoms.append(atom)
            self._json_response(atom, 201)

        elif path == "/relations":
            rel = {
                "source": body.get("source"),
                "target": body.get("target"),
                "type": body.get("type"),
            }
            self.relations.append(rel)
            self._json_response(rel, 201)

        elif path == "/ingest":
            self._json_response({
                "entities": [],
                "relations": [],
                "text": body.get("text", ""),
            })

        elif path == "/tick":
            self._json_response({"status": "ok", "contradictions": []})

        else:
            self._json_response({"error": "not found"}, 404)

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture
def mock_server() -> Generator[str, None, None]:
    MockDCMAHandler.atoms = []
    MockDCMAHandler.relations = []

    server = HTTPServer(("127.0.0.1", 0), MockDCMAHandler)
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield base_url

    server.shutdown()
    server.server_close()

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:3030"
REQUEST_TIMEOUT = 5


class DCMAError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class DCMAClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, url: str) -> None:
        self._base_url = url.rstrip("/")

    def _request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {}
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            status = e.code
            try:
                detail = json.loads(e.read().decode("utf-8"))
            except Exception:
                detail = {}
            msg = detail.get("error", detail.get("message", str(e)))
            raise DCMAError(str(msg), status_code=status) from e
        except urllib.error.URLError as e:
            raise DCMAError(f"Connection failed: {e.reason}") from e

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def search(
        self, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        result = self._request("GET", "/search", params={"q": query, "limit": limit})
        if isinstance(result, dict):
            atoms = result.get("atoms", [])
            return atoms if isinstance(atoms, list) else []
        if isinstance(result, list):
            return result
        return []

    def graph(self, query: str) -> dict[str, Any]:
        return self._request("GET", "/graph", params={"q": query})

    def remember(
        self,
        name: str,
        type: str,
        content: str | None = None,
        tags: list[str] | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "type": type}
        if content is not None:
            payload["content"] = content
        if tags is not None:
            payload["tags"] = tags
        if attributes is not None:
            payload["attributes"] = attributes
        return self._request("POST", "/remember", data=payload)

    def relate(
        self, source: str, target: str, type: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/relations",
            data={"src": source, "dst": target, "type": type},
        )

    def ingest(self, text: str) -> dict[str, Any]:
        return self._request("POST", "/ingest", data={"text": text})

    def tick(self) -> dict[str, Any]:
        return self._request("POST", "/tick")

    def list_atoms(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._request("GET", "/atoms", params={"limit": limit})

    def get_contradictions(self) -> list[dict[str, Any]]:
        try:
            result = self._request("GET", "/contradictions")
        except DCMAError as e:
            if e.status_code == 404:
                return []
            raise
        if isinstance(result, list):
            return result
        return []

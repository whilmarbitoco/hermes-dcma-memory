import logging
import threading
from typing import Any, ClassVar

from .client import DCMAClient

try:
    from hermes.memory import MemoryProvider
except ImportError:
    class MemoryProvider:  # type: ignore[no-redef]
        name: ClassVar[str] = "dcma"

        def is_available(self) -> bool:
            return False

        def initialize(self, session_id: str, **kwargs: Any) -> None:
            pass

        def system_prompt_block(self) -> str:
            return ""

        def prefetch(self, query: str, session_id: str = "") -> str:
            return ""

        def sync_turn(self, user: str, assistant: str, session_id: str = "") -> None:
            pass

        def get_tool_schemas(self) -> list[dict[str, Any]]:
            return []

        def handle_tool_call(self, tool_name: str, args: dict[str, Any]) -> Any:
            return {"error": "not implemented"}

        def shutdown(self) -> None:
            pass


logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

AVAILABILITY_CACHE_SECONDS = 30


class DCMAMemoryProvider(MemoryProvider):
    name: ClassVar[str] = "dcma"

    def __init__(self) -> None:
        self._client = DCMAClient()
        self._session_id: str | None = None
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is None:
            try:
                self._client.health()
                self._available = True
            except Exception:
                self._available = False
        return self._available

    def initialize(self, session_id: str, **kwargs: Any) -> None:
        self._session_id = session_id
        logger.info("DCMA provider initialized for session %s", session_id)

    def system_prompt_block(self) -> str:
        if self._available:
            return "Memory: DCMA graph cognition engine connected."
        return "Memory: DCMA unavailable (graph cognition disabled)."

    def prefetch(self, query: str, session_id: str = "") -> str:
        try:
            results = self._client.search(query, limit=5)
            atoms = results.get("atoms", []) if isinstance(results, dict) else results
            if not atoms:
                return "No relevant memories found."
            lines = []
            for r in atoms[:5]:
                name = r.get("name", "unknown")
                content = r.get("content", "")
                lines.append(f"- {name}: {content}" if content else f"- {name}")
            return "Relevant memories:\n" + "\n".join(lines)
        except Exception as e:
            logger.warning("Prefetch failed: %s", e)
            return ""

    def sync_turn(self, user: str, assistant: str, session_id: str = "") -> None:
        def _ingest() -> None:
            try:
                text = f"User: {user}\nAssistant: {assistant}"
                self._client.ingest(text)
            except Exception as e:
                logger.debug("Ingest on sync_turn failed: %s", e)

        thread = threading.Thread(target=_ingest, daemon=True)
        thread.start()

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "dcma_search",
                "description": "Search DCMA memory by text query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "dcma_remember",
                "description": "Store a memory atom in DCMA",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "content": {"type": "string"},
                        "tags": {"type": "string"},
                        "attributes": {"type": "object"},
                    },
                    "required": ["name", "type"],
                },
            },
            {
                "name": "dcma_ingest",
                "description": "Extract entities and relations from natural language text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                    },
                    "required": ["text"],
                },
            },
            {
                "name": "dcma_graph",
                "description": "Relational graph search across DCMA memory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "dcma_relate",
                "description": "Create a relationship between two memory atoms",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "target": {"type": "string"},
                        "type": {"type": "string"},
                    },
                    "required": ["source", "target", "type"],
                },
            },
            {
                "name": "dcma_contradictions",
                "description": "List detected contradictions in DCMA memory",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def handle_tool_call(self, tool_name: str, args: dict[str, Any]) -> Any:
        try:
            if tool_name == "dcma_search":
                return self._client.search(args["query"], limit=args.get("limit", 10))
            elif tool_name == "dcma_remember":
                tags = None
                if isinstance(args.get("tags"), str):
                    tags = [t.strip() for t in args["tags"].split(",") if t.strip()]
                return self._client.remember(
                    name=args["name"],
                    type=args["type"],
                    content=args.get("content"),
                    tags=tags,
                    attributes=args.get("attributes"),
                )
            elif tool_name == "dcma_ingest":
                return self._client.ingest(args["text"])
            elif tool_name == "dcma_graph":
                return self._client.graph(args["query"])
            elif tool_name == "dcma_relate":
                return self._client.relate(
                    source=args["source"],
                    target=args["target"],
                    type=args["type"],
                )
            elif tool_name == "dcma_contradictions":
                return self._client.get_contradictions()
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error("Tool call '%s' failed: %s", tool_name, e)
            return {"error": str(e)}

    def shutdown(self) -> None:
        logger.info("DCMA provider shut down")

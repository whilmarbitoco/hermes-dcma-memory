import json
import logging
import re
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

_TURN_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "preference",
        "positive",
        re.compile(
            r"\bI\s+(?:really\s+)?(?:like|love|prefer|enjoy|use)\s+(?P<object>[^.!?\n]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "preference",
        "negative",
        re.compile(
            r"\bI\s+(?:do\s+not|don't|dont|dislike|hate|avoid)\s+(?:like\s+)?(?P<object>[^.!?\n]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "identity",
        "name",
        re.compile(r"\bmy\s+name\s+is\s+(?P<object>[^.!?\n]+)", re.IGNORECASE),
    ),
    (
        "identity",
        "location",
        re.compile(r"\bI\s+live\s+in\s+(?P<object>[^.!?\n]+)", re.IGNORECASE),
    ),
    (
        "commitment",
        "assistant",
        re.compile(r"\bI\s+(?:will|'ll|can|should)\s+(?P<object>[^.!?\n]+)", re.IGNORECASE),
    ),
]


def _slugify(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value or "item"


def _clean_phrase(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" ,;:.!?\"'")


def _candidate_name(kind: str, subject: str, value: str) -> str:
    return f"passive-{kind}-{_slugify(subject)}-{_slugify(value)[:48]}"


def _extract_candidates(user: str, assistant: str, session_id: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    def _scan(text: str, source: str) -> None:
        for kind, subject, pattern in _TURN_PATTERNS:
            for match in pattern.finditer(text):
                value = _clean_phrase(match.group("object"))
                if not value:
                    continue
                if kind == "commitment" and source != "assistant":
                    continue
                if kind in {"preference", "identity"} and source != "user":
                    continue
                name = _candidate_name(kind, subject, value)
                content = f"{source} {kind}: {value}"
                confidence = 0.9 if kind in {"identity", "preference"} else 0.75
                candidates.append(
                    {
                        "name": name,
                        "type": kind.title(),
                        "content": content,
                        "tags": ["passive", kind, source],
                        "attributes": {
                            "source": source,
                            "session_id": session_id,
                            "confidence": confidence,
                            "evidence": value,
                        },
                    }
                )

    _scan(user, "user")
    _scan(assistant, "assistant")

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate["name"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


class DCMAMemoryProvider(MemoryProvider):
    name: ClassVar[str] = "dcma"

    def __init__(self) -> None:
        self._client = DCMAClient()
        self._session_id: str | None = None
        self._available: bool | None = None
        self._learned_memory_keys: set[str] = set()

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
                if not isinstance(content, str):
                    content = json.dumps(content, ensure_ascii=False)
                content = " ".join(content.split())
                lines.append(f"- {name}: {content}" if content else f"- {name}")
            return "Relevant memories:\n" + "\n".join(lines)
        except Exception as e:
            logger.warning("Prefetch failed: %s", e)
            return ""

    def sync_turn(self, user: str, assistant: str, session_id: str = "") -> None:
        session_key = session_id or self._session_id or "session"

        def _ingest() -> None:
            try:
                for candidate in _extract_candidates(user, assistant, session_key):
                    key = candidate["name"]
                    if key in self._learned_memory_keys:
                        continue
                    self._client.remember(
                        name=candidate["name"],
                        type=candidate["type"],
                        content=candidate["content"],
                        tags=candidate["tags"],
                        attributes=candidate["attributes"],
                    )
                    self._learned_memory_keys.add(key)
            except Exception as e:
                logger.debug("Passive learning on sync_turn failed: %s", e)

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
        ]

    def handle_tool_call(self, tool_name: str, args: dict[str, Any]) -> Any:
        try:
            def _textify(value: Any) -> str:
                if isinstance(value, str):
                    return " ".join(value.split())
                if isinstance(value, list):
                    lines: list[str] = []
                    for item in value[:10]:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("id") or "item"
                            content = item.get("content", "")
                            if not isinstance(content, str):
                                content = str(content)
                            content = " ".join(content.split())
                            lines.append(f"- {name}: {content}" if content else f"- {name}")
                        else:
                            lines.append(f"- {str(item)}")
                    return "\n".join(lines) if lines else "No results."
                if isinstance(value, dict):
                    parts: list[str] = []
                    for key in ("name", "type", "id", "source", "target", "status", "message", "error", "query", "method", "total", "text"):
                        if key in value and value[key] is not None:
                            parts.append(f"{key}: {value[key]}")
                    if "atoms" in value and isinstance(value["atoms"], list):
                        atoms = value["atoms"][:5]
                        parts.append(f"atoms: {len(value['atoms'])}")
                        for atom in atoms:
                            if isinstance(atom, dict):
                                name = atom.get("name", "item")
                                content = atom.get("content", "")
                                if not isinstance(content, str):
                                    content = str(content)
                                content = " ".join(content.split())
                                parts.append(f"- {name}: {content}" if content else f"- {name}")
                    if "relations" in value and isinstance(value["relations"], list):
                        parts.append(f"relations: {len(value['relations'])}")
                    for key in ("content", "tags", "attributes"):
                        if key in value and value[key] not in (None, "", [], {}):
                            parts.append(f"{key}: {value[key]}")
                    return "\n".join(parts) if parts else "OK"
                return str(value)

            if tool_name == "dcma_search":
                return _textify(self._client.search(args["query"], limit=args.get("limit", 10)))
            elif tool_name == "dcma_remember":
                tags = None
                if isinstance(args.get("tags"), str):
                    tags = [t.strip() for t in args["tags"].split(",") if t.strip()]
                return _textify(self._client.remember(
                    name=args["name"],
                    type=args["type"],
                    content=args.get("content"),
                    tags=tags,
                    attributes=args.get("attributes"),
                ))
            elif tool_name == "dcma_ingest":
                return _textify(self._client.ingest(args["text"]))
            elif tool_name == "dcma_graph":
                return _textify(self._client.graph(args["query"]))
            elif tool_name == "dcma_relate":
                return _textify(self._client.relate(
                    source=args["source"],
                    target=args["target"],
                    type=args["type"],
                ))
            elif tool_name == "dcma_contradictions":
                return "contradictions: unsupported"
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error("Tool call '%s' failed: %s", tool_name, e)
            return f"error: {e}"

    def shutdown(self) -> None:
        logger.info("DCMA provider shut down")

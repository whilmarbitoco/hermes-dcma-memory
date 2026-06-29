# hermes-dcma-memory

A [Hermes](https://github.com/NousResearch/hermes-agent) memory provider plugin that connects to a DCMA graph cognition engine backend.

DCMA processes knowledge through a graph cognition pipeline:
- **Extracts entities and relationships** from text, building a living knowledge graph
- **Detects contradictions** — when new information conflicts with prior knowledge
- **Surfaces forgotten connections** relevant to the current context
- **Enables natural-language ingestion** with automatic entity/relation extraction

This plugin connects Hermes to a DCMA backend, giving agents structured recall with relational reasoning.

- Graph-based memory with entities and typed relationships
- Full-text search across memory atoms
- Natural language ingestion (extract entities and relations from text)
- Contradiction detection via cognitive tick cycles
- Activation spreading for relevance-ranked recall
- Zero external dependencies — uses Python stdlib only

## Installation

```bash
pip install hermes-dcma-memory
```

For development:

```bash
pip install -e '.[dev]'
```

## Configuration

Add to your Hermes `config.yaml`:

```yaml
memory:
  provider: dcma
```

## Prerequisites

A DCMA server must be running at `http://localhost:3030`. DCMA is private and not publicly available.

## API Reference

Tools exposed to Hermes agents:

| Tool | Description |
|------|-------------|
| `dcma_search` | Search DCMA memory by text query |
| `dcma_remember` | Store a memory atom with type, content, tags, attributes |
| `dcma_ingest` | Extract entities and relations from natural language |
| `dcma_graph` | Relational graph search returning atoms + relations |
| `dcma_relate` | Create a typed relationship between two atoms |
| `dcma_contradictions` | List detected contradictions in memory |

## License

MIT

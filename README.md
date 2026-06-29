# hermes-dcma-memory

A [Hermes](https://github.com/NousResearch/hermes-agent) memory provider plugin backed by DCMA.

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

A DCMA server running at `http://localhost:3030`. DCMA is private and not publicly available.

## Tools

| Tool | Description |
|------|-------------|
| `dcma_search` | Search stored memory |
| `dcma_remember` | Store a memory entry |
| `dcma_ingest` | Process natural language into memory |
| `dcma_graph` | Relational memory lookup |
| `dcma_relate` | Connect two memory entries |
| `dcma_contradictions` | Surface conflicting memory entries |

## License

MIT

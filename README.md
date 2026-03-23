# 🕸️ a2a-trace

**A2A-native Distributed Tracing & Agent Topology Visualization**

A lightweight tracing library designed specifically for the Agent-to-Agent (A2A) protocol. Track messages as they flow through your agent network, visualize agent topology in real-time, and debug multi-agent workflows with ease.

## ✨ Features

- **Trace Context Propagation** — Inject `trace_id` + `span_id` into A2A messages, auto-propagated across agent boundaries
- **A2A Semantic Attributes** — OTel-compatible span attributes for agent-specific data (`task_state`, `model_provider`, `routing_reason`)
- **Real-time Topology** — Web dashboard showing agent call relationships as they happen
- **Task Correlation** — All spans linked by `task_id` for end-to-end traceability
- **Zero External Dependencies** — SQLite storage, pure Python, no Kafka/Jaeger required for basic use

## 🚀 Quick Start

```bash
pip install a2a-trace
```

### Basic Usage

```python
from a2a_trace import A2ATraceMiddleware, A2ASpan, get_collector
from a2a_trace.server.web import run_server_background

# Start the dashboard
run_server_background(port=8081)

# Add tracing to your A2A agent
middleware = A2ATraceMiddleware(service_name="my-agent")

# On incoming request
ctx = middleware.on_request(request_message, task_id="task_001")

# Record a span
collector = get_collector()
collector.record_span(A2ASpan(
    trace_id=ctx.trace_id,
    span_id=ctx.span_id,
    parent_span_id=ctx.parent_span_id,
    task_id="task_001",
    service_name="my-agent",
    span_type="request",
    timestamp=time.time(),
    duration_ms=50,
    task_state="working",
))
```

### Trace Context Propagation

```python
from a2a_trace import A2ATracePropagator

propagator = A2ATracePropagator()

# Agent A: Inject context before sending to Agent B
propagator.inject(ctx, outgoing_message)

# Agent B: Extract context from incoming message
parent_ctx = propagator.extract(incoming_message)
child_ctx = parent_ctx.child_span(service_name="agent-b")
```

## 🖥️ Dashboard

Start the dashboard and open `http://localhost:8081`:

```python
from a2a_trace.server.web import run_server
run_server(port=8081)
```

The dashboard shows:
- **Agent Topology** — Nodes = agents, Edges = call relationships
- **Recent Traces** — Browse recent trace IDs
- **Span Timeline** — Detailed timeline for each trace

## 📊 Span Attributes (A2A Extension)

| Attribute | Type | Description |
|-----------|------|-------------|
| `a2a.task.id` | string | Task identifier for correlation |
| `a2a.task.state` | enum | `submitted` / `working` / `completed` / `failed` |
| `a2a.agent.name` | string | Agent/service name |
| `a2a.agent.card_url` | string | A2A Agent Card URL |
| `a2a.model.provider` | string | LLM provider (`openai` / `anthropic` / `google`) |
| `a2a.model.name` | string | Model name (`gpt-4` / `claude-3-sonnet`) |
| `a2a.routing.reason` | string | AI routing decision explanation |

## 🔌 Integration with python-a2a

### TracedAgentMixin

Add tracing to your agent class with a single mixin:

```python
from a2a_trace import TracedAgentMixin, traced

class MyAgent(TracedAgentMixin):
    def __init__(self):
        self.init_tracing(service_name="my-agent")
    
    @traced(operation="handle_query")
    def handle_query(self, query: str, trace_ctx=None, task_id=None):
        # This method is now automatically traced
        return result
```

### Standalone Functions

Trace any function with the `@traced_function` decorator:

```python
from a2a_trace import traced_function

@traced_function(service_name="web-search", operation="search")
def web_search(query: str) -> str:
    # Automatically traced
    return results
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                  A2A Message                     │
│  {                                               │
│    "params": {                                   │
│      "metadata": {                               │
│        "a2a_trace": { ◄── Trace context here     │
│          "trace_id": "0af7...",                   │
│          "span_id": "b7ad...",                    │
│          "task_id": "task_001"                    │
│        }                                         │
│      }                                           │
│    }                                             │
│  }                                               │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
          ┌──────────────┐
          │   Collector  │
          └──────┬───────┘
                 │
                 ▼
          ┌──────────────┐
          │   SQLite DB  │
          └──────┬───────┘
                 │
                 ▼
          ┌──────────────┐
          │   Dashboard  │ (http://localhost:8081)
          │   Topology   │
          │   Traces     │
          └──────────────┘
```

## 📄 License

MIT

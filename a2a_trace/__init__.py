"""
a2a-trace — A2A-native Distributed Tracing for Agent Networks.

This package provides distributed tracing capabilities specifically designed
for the Agent-to-Agent (A2A) protocol. It enables:

- Trace context propagation across agent boundaries
- A2A-specific semantic attributes for spans
- Real-time agent topology visualization
- Task-level trace correlation

Basic Usage:
    from a2a_trace import A2ATraceContext, A2ATracePropagator, A2ATraceMiddleware
    
    # Create middleware for an agent
    middleware = A2ATraceMiddleware(service_name="research-agent")
    
    # On incoming request
    ctx = middleware.on_request(request_message)
    
    # ... process request ...
    
    # On outgoing response
    middleware.on_response(response_message, ctx)

Visualization:
    from a2a_trace.server import run_server
    run_server(port=8080)  # Open http://localhost:8080
"""

__version__ = "0.1.0"

from .context import A2ATraceContext
from .propagator import A2ATracePropagator, A2ATraceMiddleware
from .collector import A2ATraceCollector, A2ASpan, get_collector
from .integration import (
    TracedAgentMixin,
    TraceSpan,
    traced,
    traced_function,
)

__all__ = [
    "A2ATraceContext",
    "A2ATracePropagator",
    "A2ATraceMiddleware",
    "A2ATraceCollector",
    "A2ASpan",
    "get_collector",
    "TracedAgentMixin",
    "TraceSpan",
    "traced",
    "traced_function",
]

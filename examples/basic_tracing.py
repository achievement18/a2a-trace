#!/usr/bin/env python3
"""
Example: Basic A2A tracing with two agents.

This example demonstrates how to use a2a-trace to track
messages flowing between two A2A agents.

Run:
    python examples/basic_tracing.py

Then open http://localhost:8081 to see the topology.
"""

import time
import json
from a2a_trace import (
    A2ATraceContext,
    A2ATracePropagator,
    A2ATraceMiddleware,
    A2ASpan,
    get_collector,
)
from a2a_trace.server.web import run_server_background


def simulate_agent_call():
    """Simulate a multi-agent workflow with tracing."""
    
    # Start the trace dashboard in background
    run_server_background(port=8081)
    
    collector = get_collector()
    propagator = A2ATracePropagator()
    
    # ── Step 1: User sends message to Router Agent ──
    print("📨 User → Router Agent")
    
    router_middleware = A2ATraceMiddleware(service_name="router-agent")
    
    incoming_msg = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Research the A2A protocol"}],
            }
        },
    }
    
    router_ctx = router_middleware.on_request(incoming_msg, task_id="task_001")
    
    # Record span
    collector.record_span(A2ASpan(
        trace_id=router_ctx.trace_id,
        span_id=router_ctx.span_id,
        parent_span_id=router_ctx.parent_span_id,
        task_id="task_001",
        service_name="router-agent",
        span_type="request",
        timestamp=time.time(),
        duration_ms=50,
        task_state="working",
        routing_reason="Query requires research capability",
    ))
    
    print(f"   Trace ID: {router_ctx.trace_id}")
    print(f"   Span ID:  {router_ctx.span_id}")
    
    time.sleep(0.1)
    
    # ── Step 2: Router forwards to Research Agent ──
    print("📨 Router Agent → Research Agent")
    
    research_middleware = A2ATraceMiddleware(service_name="research-agent")
    
    # Router creates message with trace context
    research_msg = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Research the A2A protocol"}],
            }
        },
    }
    propagator.inject(router_ctx, research_msg)
    
    research_ctx = research_middleware.on_request(research_msg, task_id="task_001")
    
    collector.record_span(A2ASpan(
        trace_id=research_ctx.trace_id,
        span_id=research_ctx.span_id,
        parent_span_id=research_ctx.parent_span_id,
        task_id="task_001",
        service_name="research-agent",
        span_type="request",
        timestamp=time.time(),
        duration_ms=200,
        task_state="working",
        model_provider="anthropic",
        model_name="claude-3-sonnet",
    ))
    
    time.sleep(0.2)
    
    # ── Step 3: Research Agent calls external API (via MCP) ──
    print("📨 Research Agent → Web Search Tool")
    
    search_ctx = research_ctx.child_span(service_name="web-search-tool")
    
    collector.record_span(A2ASpan(
        trace_id=search_ctx.trace_id,
        span_id=search_ctx.span_id,
        parent_span_id=search_ctx.parent_span_id,
        task_id="task_001",
        service_name="web-search-tool",
        span_type="internal",
        timestamp=time.time(),
        duration_ms=150,
        task_state="completed",
        attributes={"query": "A2A protocol google agents"},
    ))
    
    time.sleep(0.15)
    
    # ── Step 4: Research Agent responds ──
    print("📨 Research Agent → Router Agent (response)")
    
    collector.record_span(A2ASpan(
        trace_id=research_ctx.trace_id,
        span_id=_generate_span_id(),
        parent_span_id=research_ctx.span_id,
        task_id="task_001",
        service_name="research-agent",
        span_type="response",
        timestamp=time.time(),
        duration_ms=5,
        task_state="completed",
    ))
    
    # ── Step 5: Router forwards to Output Agent ──
    print("📨 Router Agent → Output Agent")
    
    output_middleware = A2ATraceMiddleware(service_name="output-agent")
    output_msg = {"jsonrpc": "2.0", "method": "message/send", "params": {"message": {"role": "user", "parts": [{"type": "text", "text": "Summary: ..."}]}}}
    propagator.inject(router_ctx, output_msg)
    
    output_ctx = output_middleware.on_request(output_msg, task_id="task_001")
    
    collector.record_span(A2ASpan(
        trace_id=output_ctx.trace_id,
        span_id=output_ctx.span_id,
        parent_span_id=output_ctx.parent_span_id,
        task_id="task_001",
        service_name="output-agent",
        span_type="response",
        timestamp=time.time(),
        duration_ms=30,
        task_state="completed",
    ))
    
    time.sleep(0.05)
    
    # ── Done ──
    print("\n✅ Workflow complete!")
    print(f"🔗 View trace: http://localhost:8081")
    print(f"   Trace ID: {router_ctx.trace_id}")
    print("\nKeeping dashboard alive for 60 seconds...")
    print("Press Ctrl+C to exit.")
    
    # Keep server running
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass


def _generate_span_id():
    import uuid
    return uuid.uuid4().hex[:16]


if __name__ == "__main__":
    simulate_agent_call()

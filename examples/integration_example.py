#!/usr/bin/env python3
"""
Example: Integrating a2a-trace with python-a2a agents.

Shows how to add tracing to A2AServer using TracedAgentMixin
and the @traced decorator.

Run:
    python examples/integration_example.py

Then open http://localhost:8081 to see the topology.
"""

import time
import json
from a2a_trace import (
    TracedAgentMixin,
    traced,
    traced_function,
    A2ATraceContext,
    A2ATracePropagator,
    get_collector,
    A2ASpan,
)
from a2a_trace.server.web import run_server_background


# ─── Example Agent (simplified python-a2a style) ───

class ResearchAgent(TracedAgentMixin):
    """
    A research agent with automatic tracing.
    
    In a real scenario, this would extend python-a2a's A2AServer.
    """
    
    def __init__(self, name: str = "research-agent"):
        self.name = name
        self.init_tracing(service_name=name)
    
    @traced(operation="research_query")
    def handle_query(self, query: str, trace_ctx=None, task_id=None):
        """Handle a research query with automatic span tracing."""
        print(f"  🔍 [{self.name}] Researching: {query}")
        
        # Simulate calling a tool
        result = self._search_web(query, trace_ctx=trace_ctx)
        
        # Simulate processing
        time.sleep(0.1)
        
        return {"result": result, "agent": self.name}
    
    @traced(operation="web_search")
    def _search_web(self, query: str, trace_ctx=None, task_id=None):
        """Internal method also traced."""
        time.sleep(0.05)
        return f"Search results for: {query}"


class SummarizerAgent(TracedAgentMixin):
    """Summarization agent."""
    
    def __init__(self, name: str = "summarizer-agent"):
        self.name = name
        self.init_tracing(service_name=name)
    
    @traced(operation="summarize")
    def summarize(self, text: str, trace_ctx=None, task_id=None):
        """Summarize text with tracing."""
        print(f"  📝 [{self.name}] Summarizing...")
        time.sleep(0.08)
        return f"Summary of: {text[:50]}..."


# ─── Example standalone traced function ───

@traced_function(service_name="web-search-tool", operation="google_search")
def google_search(query: str) -> str:
    """A standalone function with automatic tracing."""
    time.sleep(0.03)
    return f"Google results for: {query}"


# ─── Simulate a multi-agent workflow ───

def run_workflow():
    """Run a traced multi-agent workflow."""
    
    # Start dashboard
    run_server_background(port=8081)
    
    # Create agents
    research = ResearchAgent("research-agent")
    summarizer = SummarizerAgent("summarizer-agent")
    
    # Shared trace context for the workflow
    propagator = A2ATracePropagator()
    workflow_ctx = A2ATraceContext.create(
        task_id="workflow_001",
        service_name="orchestrator",
    )
    
    # Record orchestrator span
    collector = get_collector()
    collector.record_span(A2ASpan(
        trace_id=workflow_ctx.trace_id,
        span_id=workflow_ctx.span_id,
        parent_span_id=None,
        task_id="workflow_001",
        service_name="orchestrator",
        span_type="request",
        timestamp=time.time(),
        task_state="working",
    ))
    
    print("🚀 Starting traced workflow...")
    print(f"   Trace ID: {workflow_ctx.trace_id}")
    print()
    
    # Step 1: Research
    print("Step 1: Research")
    research_result = research.handle_query(
        "A2A protocol agent collaboration",
        trace_ctx=workflow_ctx,
        task_id="workflow_001",
    )
    
    # Step 2: Use standalone traced function
    print("\nStep 2: Web Search (standalone function)")
    search_result = google_search("A2A protocol examples")
    
    # Step 3: Summarize
    print("\nStep 3: Summarize")
    summary = summarizer.summarize(
        research_result["result"],
        trace_ctx=workflow_ctx,
        task_id="workflow_001",
    )
    
    # Complete orchestrator span
    collector.record_span(A2ASpan(
        trace_id=workflow_ctx.trace_id,
        span_id=workflow_ctx.span_id,
        parent_span_id=None,
        task_id="workflow_001",
        service_name="orchestrator",
        span_type="response",
        timestamp=time.time(),
        duration_ms=500,
        task_state="completed",
    ))
    
    print("\n✅ Workflow complete!")
    print(f"   Summary: {summary}")
    print(f"\n🔗 Dashboard: http://localhost:8081")
    print("   Press Ctrl+C to exit.")
    
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run_workflow()

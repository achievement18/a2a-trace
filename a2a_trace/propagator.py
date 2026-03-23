"""
A2A Trace Propagator — Inject and extract trace context from A2A messages.

The propagator handles the mechanics of embedding trace context into
A2A JSON-RPC message metadata and reading it back out.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .context import A2ATraceContext


class A2ATracePropagator:
    """
    Propagates trace context through A2A messages.
    
    The propagator works with the A2A JSON-RPC protocol's metadata field
    to inject and extract trace context without modifying the protocol itself.
    
    Usage:
        propagator = A2ATracePropagator()
        
        # Inject into outgoing message
        message = {"jsonrpc": "2.0", "method": "message/send", ...}
        propagator.inject(ctx, message)
        
        # Extract from incoming message
        ctx = propagator.extract(message)
    """
    
    METADATA_KEY = "a2a_trace"
    
    def inject(self, context: A2ATraceContext, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject trace context into an A2A message.
        
        Modifies the message in-place by adding trace context to metadata.
        """
        if "params" not in message:
            message["params"] = {}
        
        if "metadata" not in message["params"]:
            message["params"]["metadata"] = {}
        
        message["params"]["metadata"][self.METADATA_KEY] = context.to_metadata()
        return message
    
    def extract(self, message: Dict[str, Any]) -> Optional[A2ATraceContext]:
        """
        Extract trace context from an A2A message.
        
        Returns None if no trace context is found.
        """
        try:
            metadata = message.get("params", {}).get("metadata", {})
            return A2ATraceContext.from_metadata(metadata)
        except (KeyError, TypeError):
            return None
    
    def is_traced(self, message: Dict[str, Any]) -> bool:
        """Check if a message contains trace context."""
        metadata = message.get("params", {}).get("metadata", {})
        return self.METADATA_KEY in metadata


class A2ATraceMiddleware:
    """
    Middleware that auto-injects trace context into all A2A messages.
    
    Can be used with any A2A server or client implementation.
    
    Usage:
        middleware = A2ATraceMiddleware(service_name="research-agent")
        
        # On incoming request
        ctx = middleware.on_request(request_message)
        
        # On outgoing response
        middleware.on_response(response_message, ctx)
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.propagator = A2ATracePropagator()
    
    def on_request(self, message: Dict[str, Any], task_id: Optional[str] = None) -> A2ATraceContext:
        """
        Process incoming request.
        
        Extracts existing trace context or creates a new one.
        Returns the active context for this request.
        """
        existing_ctx = self.propagator.extract(message)
        
        if existing_ctx:
            # Continue existing trace
            ctx = existing_ctx.child_span(
                service_name=self.service_name,
                task_id=task_id,
            )
        else:
            # Start new trace
            ctx = A2ATraceContext.create(
                task_id=task_id,
                service_name=self.service_name,
            )
        
        return ctx
    
    def on_response(self, response: Dict[str, Any], ctx: A2ATraceContext) -> Dict[str, Any]:
        """Inject trace context into outgoing response."""
        return self.propagator.inject(ctx, response)
    
    def on_error(self, error: Exception, ctx: A2ATraceContext) -> dict:
        """Create a trace-aware error response."""
        return self.propagator.inject(
            ctx,
            {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": str(error),
                    "data": {"trace_id": ctx.trace_id, "span_id": ctx.span_id},
                },
            },
        )

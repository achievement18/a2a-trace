"""
Integration layer — Drop-in tracing for python-a2a Agent classes.

This module provides mixin classes and decorators that make it trivial
to add tracing to existing A2A agents.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, Dict, Optional

from .context import A2ATraceContext
from .propagator import A2ATraceMiddleware
from .collector import A2ASpan, get_collector


class TracedAgentMixin:
    """
    Mixin that adds automatic tracing to any A2A agent class.
    
    Usage:
        class MyAgent(TracedAgentMixin, A2AServer):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.init_tracing(service_name="my-agent")
            
            def handle_message(self, message):
                with self.trace_span("handle_message") as ctx:
                    # Your logic here
                    pass
    """
    
    def init_tracing(
        self,
        service_name: Optional[str] = None,
        enable_collector: bool = True,
    ):
        """Initialize tracing for this agent."""
        self._trace_service_name = service_name or self.__class__.__name__
        self._trace_middleware = A2ATraceMiddleware(
            service_name=self._trace_service_name
        )
        self._trace_enabled = enable_collector
    
    def trace_on_request(
        self,
        message: Dict[str, Any],
        task_id: Optional[str] = None,
    ) -> A2ATraceContext:
        """Process incoming message and create/continue trace context."""
        if not hasattr(self, "_trace_middleware"):
            self.init_tracing()
        return self._trace_middleware.on_request(message, task_id)
    
    def trace_on_response(
        self,
        response: Dict[str, Any],
        ctx: A2ATraceContext,
    ) -> Dict[str, Any]:
        """Inject trace context into outgoing response."""
        return self._trace_middleware.on_response(response, ctx)
    
    def trace_span(
        self,
        operation: str,
        task_id: Optional[str] = None,
        ctx: Optional[A2ATraceContext] = None,
    ):
        """Context manager for tracing a span."""
        return TraceSpan(
            service_name=self._trace_service_name,
            operation=operation,
            task_id=task_id,
            parent_ctx=ctx,
        )


class TraceSpan:
    """Context manager for a single traced span."""
    
    def __init__(
        self,
        service_name: str,
        operation: str,
        task_id: Optional[str] = None,
        parent_ctx: Optional[A2ATraceContext] = None,
    ):
        self.service_name = service_name
        self.operation = operation
        self.task_id = task_id
        self.parent_ctx = parent_ctx
        self.ctx: Optional[A2ATraceContext] = None
        self.start_time: float = 0
        self.error: Optional[Exception] = None
    
    def __enter__(self) -> A2ATraceContext:
        self.start_time = time.time()
        
        if self.parent_ctx:
            self.ctx = self.parent_ctx.child_span(
                service_name=self.service_name,
                task_id=self.task_id,
            )
        else:
            self.ctx = A2ATraceContext.create(
                task_id=self.task_id,
                service_name=self.service_name,
            )
        
        # Record span start
        collector = get_collector()
        collector.record_span(A2ASpan(
            trace_id=self.ctx.trace_id,
            span_id=self.ctx.span_id,
            parent_span_id=self.ctx.parent_span_id,
            task_id=self.ctx.task_id,
            service_name=self.service_name,
            span_type="internal",
            timestamp=self.start_time,
            attributes={"operation": self.operation},
            task_state="working",
        ))
        
        return self.ctx
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        
        collector = get_collector()
        collector.record_span(A2ASpan(
            trace_id=self.ctx.trace_id,
            span_id=self.ctx.span_id,
            parent_span_id=self.ctx.parent_span_id,
            task_id=self.ctx.task_id,
            service_name=self.service_name,
            span_type="error" if exc_type else "internal",
            timestamp=self.start_time,
            duration_ms=duration_ms,
            attributes={"operation": self.operation},
            task_state="failed" if exc_type else "completed",
            error_message=str(exc_val) if exc_val else None,
        ))
        
        return False  # Don't suppress exceptions


def traced(
    service_name: Optional[str] = None,
    operation: Optional[str] = None,
):
    """
    Decorator for automatic tracing of agent methods.
    
    Usage:
        class MyAgent(TracedAgentMixin, A2AServer):
            @traced(operation="research")
            def research(self, query: str) -> str:
                # This method is now automatically traced
                return result
    """
    def decorator(func: Callable) -> Callable:
        op_name = operation or func.__name__
        
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, "_trace_middleware"):
                self.init_tracing(service_name=service_name or self.__class__.__name__)
            
            # Try to extract trace context from kwargs or args
            trace_ctx = kwargs.get("trace_ctx")
            task_id = kwargs.get("task_id")
            
            with self.trace_span(
                operation=op_name,
                task_id=task_id,
                ctx=trace_ctx,
            ) as ctx:
                kwargs["trace_ctx"] = ctx
                return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


def traced_function(
    func: Optional[Callable] = None,
    *,
    service_name: str = "standalone",
    operation: Optional[str] = None,
):
    """
    Decorator for tracing standalone functions (not agent methods).
    
    Usage:
        @traced_function(service_name="tool", operation="web_search")
        def web_search(query: str) -> str:
            ...
    """
    def decorator(fn: Callable) -> Callable:
        op_name = operation or fn.__name__
        
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            ctx = A2ATraceContext.create(service_name=service_name)
            
            start = time.time()
            collector = get_collector()
            collector.record_span(A2ASpan(
                trace_id=ctx.trace_id,
                span_id=ctx.span_id,
                parent_span_id=None,
                task_id=ctx.task_id,
                service_name=service_name,
                span_type="internal",
                timestamp=start,
                attributes={"operation": op_name},
                task_state="working",
            ))
            
            try:
                result = fn(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                collector.record_span(A2ASpan(
                    trace_id=ctx.trace_id,
                    span_id=ctx.span_id,
                    parent_span_id=None,
                    task_id=ctx.task_id,
                    service_name=service_name,
                    span_type="internal",
                    timestamp=start,
                    duration_ms=duration_ms,
                    attributes={"operation": op_name},
                    task_state="completed",
                ))
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                collector.record_span(A2ASpan(
                    trace_id=ctx.trace_id,
                    span_id=ctx.span_id,
                    parent_span_id=None,
                    task_id=ctx.task_id,
                    service_name=service_name,
                    span_type="error",
                    timestamp=start,
                    duration_ms=duration_ms,
                    attributes={"operation": op_name},
                    task_state="failed",
                    error_message=str(e),
                ))
                raise
        
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator

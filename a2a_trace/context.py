"""
A2A Trace Context — Distributed tracing context for Agent-to-Agent protocol.

This module defines the trace context that flows between A2A agents,
enabling distributed tracing across agent networks.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class A2ATraceContext:
    """
    Trace context that travels with A2A messages.
    
    This context is embedded in the A2A JSON-RPC message metadata,
    enabling distributed tracing across agent boundaries.
    
    Attributes:
        trace_id: Global trace identifier (128-bit hex, 32 chars)
        span_id: Current span identifier (64-bit hex, 16 chars)
        parent_span_id: Parent span identifier (optional, 16 chars)
        task_id: A2A task identifier for correlation
        service_name: Name of the agent/service generating this span
        timestamp: Unix timestamp when this context was created
    """
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    task_id: Optional[str] = None
    service_name: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    @classmethod
    def create(
        cls,
        task_id: Optional[str] = None,
        service_name: Optional[str] = None,
        parent_context: Optional["A2ATraceContext"] = None,
    ) -> "A2ATraceContext":
        """Create a new trace context, inheriting trace_id from parent if available."""
        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        else:
            trace_id = _generate_trace_id()
            parent_span_id = None
        
        # Resolve task_id: explicit > parent > None
        resolved_task_id = task_id
        if resolved_task_id is None and parent_context:
            resolved_task_id = parent_context.task_id
        
        return cls(
            trace_id=trace_id,
            span_id=_generate_span_id(),
            parent_span_id=parent_span_id,
            task_id=resolved_task_id,
            service_name=service_name,
        )
    
    def child_span(self, service_name: str, task_id: Optional[str] = None) -> "A2ATraceContext":
        """Create a child span context for downstream agent calls."""
        return self.create(
            task_id=task_id or self.task_id,
            service_name=service_name,
            parent_context=self,
        )
    
    def to_metadata(self) -> dict:
        """Serialize to A2A message metadata format."""
        data = asdict(self)
        # Remove None values for cleaner JSON
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_metadata(cls, metadata: dict) -> Optional["A2ATraceContext"]:
        """Extract trace context from A2A message metadata."""
        trace_data = metadata.get("a2a_trace")
        if not trace_data:
            return None
        return cls(**trace_data)
    
    def is_valid(self) -> bool:
        """Validate that this context has required fields."""
        return (
            len(self.trace_id) == 32
            and len(self.span_id) == 16
            and all(c in "0123456789abcdef" for c in self.trace_id)
            and all(c in "0123456789abcdef" for c in self.span_id)
        )


def _generate_trace_id() -> str:
    """Generate a 128-bit trace ID (32 hex chars)."""
    return uuid.uuid4().hex


def _generate_span_id() -> str:
    """Generate a 64-bit span ID (16 hex chars)."""
    return uuid.uuid4().hex[:16]

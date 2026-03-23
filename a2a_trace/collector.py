"""
A2A Trace Collector — Gathers and stores trace data from agent networks.

The collector receives span data from all agents in the network,
persists it, and provides query APIs for the visualization layer.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class A2ASpan:
    """A single span in the A2A trace."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    task_id: Optional[str]
    service_name: str
    span_type: str  # "request" | "response" | "error" | "internal"
    timestamp: float
    duration_ms: Optional[float] = None
    attributes: Optional[Dict[str, Any]] = None
    task_state: Optional[str] = None  # submitted/working/completed/failed
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    routing_reason: Optional[str] = None
    error_message: Optional[str] = None


class A2ATraceCollector:
    """
    Collects and stores A2A trace data.
    
    Thread-safe collector that persists span data to SQLite
    and provides real-time query capabilities.
    """
    
    def __init__(self, db_path: str = "~/.a2a-trace/traces.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS spans (
                span_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                parent_span_id TEXT,
                task_id TEXT,
                service_name TEXT NOT NULL,
                span_type TEXT NOT NULL,
                timestamp REAL NOT NULL,
                duration_ms REAL,
                attributes TEXT,
                task_state TEXT,
                model_provider TEXT,
                model_name TEXT,
                routing_reason TEXT,
                error_message TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_id ON spans(trace_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_task_id ON spans(task_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON spans(timestamp)")
        conn.commit()
    
    def record_span(self, span: A2ASpan):
        """Record a single span."""
        conn = self._get_conn()
        attrs_json = json.dumps(span.attributes) if span.attributes else None
        
        conn.execute("""
            INSERT OR REPLACE INTO spans 
            (span_id, trace_id, parent_span_id, task_id, service_name, 
             span_type, timestamp, duration_ms, attributes, task_state,
             model_provider, model_name, routing_reason, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            span.span_id, span.trace_id, span.parent_span_id, span.task_id,
            span.service_name, span.span_type, span.timestamp, span.duration_ms,
            attrs_json, span.task_state, span.model_provider, span.model_name,
            span.routing_reason, span.error_message,
        ))
        conn.commit()
    
    def get_trace(self, trace_id: str) -> List[A2ASpan]:
        """Get all spans for a given trace ID."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM spans WHERE trace_id = ? ORDER BY timestamp",
            (trace_id,),
        ).fetchall()
        return [self._row_to_span(r) for r in rows]
    
    def get_task_trace(self, task_id: str) -> List[A2ASpan]:
        """Get all spans for a given task ID."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM spans WHERE task_id = ? ORDER BY timestamp",
            (task_id,),
        ).fetchall()
        return [self._row_to_span(r) for r in rows]
    
    def get_topology(self, since_minutes: int = 5) -> Dict[str, Any]:
        """
        Get agent topology for visualization.
        
        Returns nodes (agents) and edges (call relationships).
        """
        conn = self._get_conn()
        since_ts = time.time() - (since_minutes * 60)
        
        # Get all spans in time window
        rows = conn.execute(
            "SELECT * FROM spans WHERE timestamp > ? ORDER BY timestamp",
            (since_ts,),
        ).fetchall()
        spans = [self._row_to_span(r) for r in rows]
        
        # Build topology
        nodes = {}
        edges = []
        
        for span in spans:
            # Nodes: unique services
            if span.service_name not in nodes:
                nodes[span.service_name] = {
                    "id": span.service_name,
                    "name": span.service_name,
                    "span_count": 0,
                    "error_count": 0,
                    "last_seen": span.timestamp,
                }
            nodes[span.service_name]["span_count"] += 1
            if span.span_type == "error":
                nodes[span.service_name]["error_count"] += 1
            
            # Edges: parent-child relationships
            if span.parent_span_id:
                parent = conn.execute(
                    "SELECT service_name FROM spans WHERE span_id = ?",
                    (span.parent_span_id,),
                ).fetchone()
                if parent and parent["service_name"] != span.service_name:
                    edges.append({
                        "source": parent["service_name"],
                        "target": span.service_name,
                        "task_id": span.task_id,
                        "timestamp": span.timestamp,
                    })
        
        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "span_count": len(spans),
            "time_range": {
                "start": since_ts,
                "end": time.time(),
            },
        }
    
    def get_recent_traces(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent traces summary."""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT trace_id, COUNT(*) as span_count, MIN(timestamp) as start_time,
                   GROUP_CONCAT(DISTINCT service_name) as services
            FROM spans
            GROUP BY trace_id
            ORDER BY start_time DESC
            LIMIT ?
        """, (limit,)).fetchall()
        
        return [
            {
                "trace_id": r["trace_id"],
                "span_count": r["span_count"],
                "start_time": r["start_time"],
                "services": r["services"].split(",") if r["services"] else [],
            }
            for r in rows
        ]
    
    def _row_to_span(self, row: sqlite3.Row) -> A2ASpan:
        """Convert database row to A2ASpan."""
        attrs = json.loads(row["attributes"]) if row["attributes"] else None
        return A2ASpan(
            trace_id=row["trace_id"],
            span_id=row["span_id"],
            parent_span_id=row["parent_span_id"],
            task_id=row["task_id"],
            service_name=row["service_name"],
            span_type=row["span_type"],
            timestamp=row["timestamp"],
            duration_ms=row["duration_ms"],
            attributes=attrs,
            task_state=row["task_state"],
            model_provider=row["model_provider"],
            model_name=row["model_name"],
            routing_reason=row["routing_reason"],
            error_message=row["error_message"],
        )


# Global collector instance
_collector: Optional[A2ATraceCollector] = None


def get_collector() -> A2ATraceCollector:
    """Get or create the global collector instance."""
    global _collector
    if _collector is None:
        _collector = A2ATraceCollector()
    return _collector

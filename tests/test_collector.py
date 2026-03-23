"""Tests for A2ATraceCollector."""

import os
import tempfile
import time
import pytest
from a2a_trace import A2ATraceCollector, A2ASpan


@pytest.fixture
def collector():
    """Create a collector with a temp database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        c = A2ATraceCollector(db_path=db_path)
        yield c


class TestA2ATraceCollector:
    def test_record_span(self, collector):
        span = A2ASpan(
            trace_id="a" * 32,
            span_id="b" * 16,
            parent_span_id=None,
            task_id="t1",
            service_name="test-svc",
            span_type="request",
            timestamp=time.time(),
        )
        collector.record_span(span)
        
        traces = collector.get_trace("a" * 32)
        assert len(traces) == 1
        assert traces[0].service_name == "test-svc"

    def test_get_task_trace(self, collector):
        ts = time.time()
        for i in range(3):
            collector.record_span(A2ASpan(
                trace_id="a" * 32,
                span_id=f"{i}" * 16,
                parent_span_id=None,
                task_id="t1",
                service_name=f"svc-{i}",
                span_type="internal",
                timestamp=ts + i,
            ))
        
        spans = collector.get_task_trace("t1")
        assert len(spans) == 3

    def test_get_topology(self, collector):
        ts = time.time()
        collector.record_span(A2ASpan(
            trace_id="a" * 32,
            span_id="1" * 16,
            parent_span_id=None,
            task_id="t1",
            service_name="agent-a",
            span_type="request",
            timestamp=ts,
        ))
        collector.record_span(A2ASpan(
            trace_id="a" * 32,
            span_id="2" * 16,
            parent_span_id="1" * 16,
            task_id="t1",
            service_name="agent-b",
            span_type="request",
            timestamp=ts + 0.1,
        ))
        
        topo = collector.get_topology(since_minutes=5)
        assert len(topo["nodes"]) == 2
        assert len(topo["edges"]) == 1
        assert topo["edges"][0]["source"] == "agent-a"
        assert topo["edges"][0]["target"] == "agent-b"

    def test_get_recent_traces(self, collector):
        for i in range(3):
            collector.record_span(A2ASpan(
                trace_id=f"{i}" * 32,
                span_id=f"{i}" * 16,
                parent_span_id=None,
                task_id=f"t{i}",
                service_name="svc",
                span_type="request",
                timestamp=time.time(),
            ))
        
        traces = collector.get_recent_traces(limit=10)
        assert len(traces) == 3

    def test_record_span_with_attributes(self, collector):
        collector.record_span(A2ASpan(
            trace_id="a" * 32,
            span_id="b" * 16,
            parent_span_id=None,
            task_id="t1",
            service_name="test",
            span_type="internal",
            timestamp=time.time(),
            attributes={"key": "value", "num": 123},
            model_provider="anthropic",
            model_name="claude-3",
            task_state="completed",
        ))
        
        spans = collector.get_trace("a" * 32)
        assert len(spans) == 1
        assert spans[0].attributes == {"key": "value", "num": 123}
        assert spans[0].model_provider == "anthropic"
        assert spans[0].task_state == "completed"

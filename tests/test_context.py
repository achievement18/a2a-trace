"""Tests for A2ATraceContext."""

import pytest
from a2a_trace import A2ATraceContext


class TestA2ATraceContext:
    def test_create_generates_ids(self):
        ctx = A2ATraceContext.create(task_id="t1", service_name="svc")
        assert len(ctx.trace_id) == 32
        assert len(ctx.span_id) == 16
        assert ctx.task_id == "t1"
        assert ctx.service_name == "svc"

    def test_create_inherits_trace_from_parent(self):
        parent = A2ATraceContext.create(task_id="t1", service_name="parent")
        child = parent.child_span(service_name="child")
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert child.span_id != parent.span_id

    def test_to_metadata_roundtrip(self):
        ctx = A2ATraceContext.create(task_id="t1", service_name="svc")
        metadata = ctx.to_metadata()
        restored = A2ATraceContext.from_metadata({"a2a_trace": metadata})
        assert restored.trace_id == ctx.trace_id
        assert restored.span_id == ctx.span_id
        assert restored.task_id == ctx.task_id

    def test_from_metadata_returns_none_if_missing(self):
        result = A2ATraceContext.from_metadata({"other": "data"})
        assert result is None

    def test_is_valid(self):
        ctx = A2ATraceContext.create()
        assert ctx.is_valid()

    def test_child_span_inherits_task_id(self):
        parent = A2ATraceContext.create(task_id="t1", service_name="svc")
        child = parent.child_span(service_name="child")
        assert child.task_id == "t1"

    def test_child_span_override_task_id(self):
        parent = A2ATraceContext.create(task_id="t1", service_name="svc")
        child = parent.child_span(service_name="child", task_id="t2")
        assert child.task_id == "t2"

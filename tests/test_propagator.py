"""Tests for A2ATracePropagator and A2ATraceMiddleware."""

import pytest
from a2a_trace import A2ATraceContext, A2ATracePropagator, A2ATraceMiddleware


class TestA2ATracePropagator:
    def setup_method(self):
        self.propagator = A2ATracePropagator()
        self.ctx = A2ATraceContext.create(task_id="t1", service_name="svc")

    def test_inject_adds_metadata(self):
        msg = {"jsonrpc": "2.0", "method": "test", "params": {}}
        self.propagator.inject(self.ctx, msg)
        assert "a2a_trace" in msg["params"]["metadata"]
        assert msg["params"]["metadata"]["a2a_trace"]["trace_id"] == self.ctx.trace_id

    def test_extract_retrieves_context(self):
        msg = {"params": {"metadata": {"a2a_trace": self.ctx.to_metadata()}}}
        extracted = self.propagator.extract(msg)
        assert extracted is not None
        assert extracted.trace_id == self.ctx.trace_id

    def test_extract_returns_none_if_missing(self):
        msg = {"params": {}}
        assert self.propagator.extract(msg) is None

    def test_is_traced(self):
        msg = {"params": {}}
        assert not self.propagator.is_traced(msg)
        self.propagator.inject(self.ctx, msg)
        assert self.propagator.is_traced(msg)

    def test_inject_creates_params_if_missing(self):
        msg = {"jsonrpc": "2.0", "method": "test"}
        self.propagator.inject(self.ctx, msg)
        assert "params" in msg
        assert "metadata" in msg["params"]


class TestA2ATraceMiddleware:
    def setup_method(self):
        self.middleware = A2ATraceMiddleware(service_name="test-agent")

    def test_on_request_creates_new_context(self):
        msg = {"params": {"message": {"role": "user"}}}
        ctx = self.middleware.on_request(msg, task_id="t1")
        assert ctx is not None
        assert ctx.service_name == "test-agent"
        assert ctx.task_id == "t1"

    def test_on_request_continues_existing_trace(self):
        parent_ctx = A2ATraceContext.create(task_id="t1", service_name="parent")
        propagator = A2ATracePropagator()
        msg = {"params": {"message": {"role": "user"}}}
        propagator.inject(parent_ctx, msg)
        
        ctx = self.middleware.on_request(msg)
        assert ctx.trace_id == parent_ctx.trace_id
        assert ctx.parent_span_id == parent_ctx.span_id

    def test_on_response_injects_context(self):
        msg = {"params": {"message": {"role": "user"}}}
        ctx = self.middleware.on_request(msg)
        response = {"result": "ok"}
        self.middleware.on_response(response, ctx)
        assert "a2a_trace" in response.get("params", {}).get("metadata", {})

    def test_on_error_creates_error_response(self):
        ctx = A2ATraceContext.create(task_id="t1", service_name="test")
        error_response = self.middleware.on_error(ValueError("test error"), ctx)
        assert "error" in error_response
        assert "test error" in error_response["error"]["message"]

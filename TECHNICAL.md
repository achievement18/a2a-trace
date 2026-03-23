# 技术方案文档

## 项目背景

A2A（Agent-to-Agent）协议中，当一个 Task 跨越多个 Agent 时，
现有链路追踪工具（OpenTelemetry）无法理解 Agent 语义。

## 核心创新

### 1. Trace Context 语义层传播

现有方案：OTel 传播 HTTP headers（traceparent）
我们的方案：在 A2A JSON-RPC 的 metadata 中传播 `task_id + trace_id + span_id`

```json
{
  "params": {
    "metadata": {
      "a2a_trace": {
        "trace_id": "...",
        "span_id": "...",
        "task_id": "...",
        "service_name": "research-agent"
      }
    }
  }
}
```

### 2. A2A 专属 Span 属性

定义 A2A 语义的 OTel 属性，让标准工具能理解 Agent 行为：
- `a2a.task.state` — Task 状态机
- `a2a.model.provider` — 使用的 LLM
- `a2a.routing.reason` — AI 路由决策原因

### 3. Agent 拓扑实时可视化

基于 trace 数据构建 Agent 调用关系图：
- 节点 = Agent（带状态颜色）
- 边 = 调用关系（带方向箭头）
- 实时 WebSocket 推送

## 与其他方案的差异

| 特性 | OpenTelemetry | a2a-trace |
|------|--------------|-----------|
| Agent 语义 | ❌ | ✅ |
| Task 关联 | ❌ | ✅ |
| 拓扑可视化 | 需要 Jaeger | 内置 |
| 部署复杂度 | 高 | 低（SQLite） |

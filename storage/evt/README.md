# EVT — Event Store / Audit (recommended)

## Description
事件/审计库。用于事件溯源、跨系统对账、风险追踪。可使用 Postgres 不同 schema 或专用存储。

## MVP deliverables
- event schema（trace_id、entity、action、payload_hash）
- 不可变写入策略
- 分区/归档策略（建议）

## Notes
- 本目录放“设计与管理资产”；部署与容器参数在 `infra/`。

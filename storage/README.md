# Storage (数据与存储)

> Updated: 2025-12-17

对应框架图中的 **“数据与存储”** 区域。本目录主要存放：
- 选型与部署说明（与 `infra/` 的 compose 对齐）
- Schema/索引/保留策略（尤其是 EVT/TS）
- 与 BFF/AI/Edge 的读写契约说明

> 注意：真正的容器与参数在 `infra/`；这里是“数据层设计与管理资产”。

## Components
- `obj/` — 对象存储（MinIO/OSS/S3）：照片/视频片段/报告PDF
- `ts/` — 时序库（Timescale/Influx 可选）：传感器曲线/运行指标
- `vec/` — 向量库（可选）：手册/FAQ/案例检索（RAG）
- `evt/` — 事件/审计库：事件溯源、操作审计、业务事件（可与 PG 不同 schema）

## Non-negotiables
- 媒体文件不入 Postgres，只存元数据 + URL。
- 支付/库存等交易真相以 Odoo/不可变 payment 为准；EVT/TS/Vec 不得反向修改交易真相。

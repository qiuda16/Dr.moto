# Diagram-to-Repo Mapping

> Updated: 2025-12-17

本文件用于回答“仓库结构如何满足你这张框架图”。

## 1. 框架图模块 -> 仓库目录
### 客户端/交互端
- WMP（微信小程序） -> `clients/mp_customer/`
- STAFF（技师/门店工作台） -> `clients/web_staff/`
- ADMIN（运营后台，主要为 Odoo UI） -> `odoo/`（Odoo UI 本体）；如有自研管理页则在 `clients/web_staff/`

### 边缘侧（你的笔记本：编排与采集）
- GW（Integration Gateway） -> `bff/`
- VID（Video Service） -> `edge/vid/`
- JARVIS（Orchestrator） -> `edge/jarvis/`
- RULES（Rule Engine） -> `edge/rules/`

### 业务中枢
- ODOO（Odoo Apps） -> `odoo/`
- PG（PostgreSQL，Odoo 主库） -> `infra/`（部署）+ `odoo/`（业务归属）

### 数据与存储
- OBJ（对象存储） -> `storage/obj/`（设计）+ `infra/`（部署）
- TS（时序库，可选） -> `storage/ts/` + `infra/`
- VEC（向量库，可选） -> `storage/vec/` + `infra/` + `ai/ai_cs/`
- EVT（事件/审计库） -> `storage/evt/` + `infra/` + `docs/`

### 外部 AI 服务商 API（云）
- LLM/VIS/STT/TTS/EMB -> `ai/`（适配器与策略）；由 `edge/jarvis` 或 `clients/cs_workspace` 通过 `ai/` 使用

## 2. 现阶段与下一阶段
- 当前仓库：已把目录与职责固定下来，便于并行开发。
- 下一步落地：补齐 `infra/docker-compose.yml`，把 PG/MinIO/Redis/MQ/（可选）Qdrant/Timescale 拉起来，然后按 `scripts/poc_*.sh` 做三条 POC Gate。

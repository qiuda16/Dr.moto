# DrMoto x OpenClaw 对齐架构（精简版）

## 目标
- 保留 OpenClaw 的核心成熟能力：分层记忆、工具策略、任务续跑、可恢复运行。
- 去掉与业务无关能力：多端网关、插件市场、桌面控制、远程设备配对。
- 在 DrMoto 内形成统一 AI 底座：同一个 Agent 同时服务客服问答、员工协作、维修手册识别入库。

## 当前落地能力
- 统一运行时：`SlimOpenClawRuntime`
  - 任务注册与续跑：`tasks.json`
  - Prompt 文档骨架：`AGENTS.md / SOUL.md / TOOLS.md / HEARTBEAT.md / MEMORY.md`
- 统一策略层：`CustomerServiceAgent`
  - 工具白名单与风险分级
  - 高风险写操作强制确认
- 统一写链路：`/chat -> _maybe_execute_write_command`
  - 已支持手册全链路写入：上传/解析/绑定/导入/分段/同步

## 分层记忆模型（已实现）
- HOT（热记忆）
  - 最近对话轮次，直接参与当前轮推理。
  - 数据字段：`turns`
- WARM（温记忆）
  - 从归档轮次压缩出的片段，用于中期上下文延续。
  - 数据字段：`warm_notes`
- COLD（冷记忆）
  - 稳定事实锚点（如 `customer_id`、`work_order_id`、`plate`、`fact_code`）。
  - 数据字段：`cold_facts`
- Working Buffer（工作缓冲区）
  - 记录最近执行动作（例如写操作、fast path/llm 路径）。
  - 数据字段：`working_buffer`

## 读写策略
- 每轮响应前：
  - 读取 HOT/WARM/COLD/Working Buffer，并注入模型提示词。
- 每轮响应后：
  - 记录 `chat_response` 事件到 Working Buffer。
  - 记录问答到 HOT，超过阈值后归档为 WARM，并更新 COLD 事实。
- 高风险写操作后：
  - 记录具体 `write_action` 与结果状态到 Working Buffer。

## 统一客服 Agent 建议（下一步）
- 单 Agent，多角色路由：
  - 客户视角：解释、预约、状态查询、售后沟通。
  - 员工视角：工单推进、报价、配件、手册入库操作。
- 同一权限模型分层：
  - read 默认开放
  - write 按角色+风险+确认词+审计落库联合控制

## 生产稳定性建议
- 增加审计表（DB 持久化）替代仅文件/redis 缓冲：
  - 字段建议：`trace_id`, `user_id`, `role`, `intent`, `tool_id`, `risk_level`, `confirm_token`, `request`, `result`, `status`, `latency_ms`, `created_at`
- 增加重试/幂等键：
  - 手册入库按 `document_id + model_id` 做幂等防重。
- 增加集成测试矩阵：
  - 小文档/大文档/超大文档
  - 同步完成/异步续跑
  - 权限不足/确认缺失/字段缺失

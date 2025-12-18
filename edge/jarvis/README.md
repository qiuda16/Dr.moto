# JARVIS — Orchestrator

## Purpose
现场流程编排：接车/检测/报价/确认/施工/交付的状态机；协调 VID 切片与 AI 检测；将结果回写到工单上下文（通过 GW/BFF）。

## MVP scope
- 工单步骤状态机（与 Odoo 工单状态对齐/映射）
- 语音/口述记录（可选 STT）与检查清单
- 触发 VID 切片与抽帧
- 触发 AI（LLM/VIS）做检查/总结，生成结构化结果
- 将结果写回：附件、检查项、备注（必须走 GW/BFF）

## Interfaces
- calls VID: 触发切片/抽帧并获取 URL
- calls AI: LLM/VIS/STT（通过 ai/ 适配器或云API）
- calls GW/BFF: 写入工单检查结果、媒体元数据、日志

## Rules (MUST)
- 不得绕过 `bff/`（GW）直接写 Odoo 交易真相（库存/收款/会计）。
- 任何写入动作必须可审计（trace_id + operator + reason）。
- 弱网/断网场景需要本地队列与重试策略（后续实现）。

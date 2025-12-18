# RULES — Rule Engine

## Purpose
规则引擎：对流程完整性、阈值、风险点进行卡口与提示；可在边缘侧离线运行，输出风险/缺失项。

## MVP scope
- 规则定义（YAML/JSON）与版本管理
- 完整性检查（必拍角度/必填项/必签收）
- 阈值检查（如扭矩、温度、振动等传感器值，若启用）
- 输出 risk cards（可视化给 STAFF）
- 事件记录写入 EVT（可选）

## Interfaces
- input: JARVIS 的步骤事件 + 可选传感器数据
- output: 风险卡口/提示、阻断条件（如必须补拍/补录）
- storage: EVT/TS（可选）

## Rules (MUST)
- 不得绕过 `bff/`（GW）直接写 Odoo 交易真相（库存/收款/会计）。
- 任何写入动作必须可审计（trace_id + operator + reason）。
- 弱网/断网场景需要本地队列与重试策略（后续实现）。

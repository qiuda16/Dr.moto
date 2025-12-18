# VID — Video Service

## Purpose
多路摄像头接入（RTSP/ONVIF）、环形缓存、切片、抽帧、上传对象存储，并输出结构化索引供 JARVIS/规则引擎使用。

## MVP scope
- 多路 RTSP 输入接入（配置化）
- 本地环形缓存（按时长/容量）
- 按事件切片（start/end）与抽帧
- 上传到 OBJ（MinIO/OSS/S3）并回写元数据（URL/hash/时间范围）
- 提供查询接口：按时间/工单/相机检索片段

## Interfaces
- northbound: 提供给 JARVIS 的本地 API（切片/抽帧/查询）
- southbound: RTSP/ONVIF 摄像头与可选传感器触发
- storage: OBJ（媒体文件），EVT（事件记录，可选）

## Rules (MUST)
- 不得绕过 `bff/`（GW）直接写 Odoo 交易真相（库存/收款/会计）。
- 任何写入动作必须可审计（trace_id + operator + reason）。
- 弱网/断网场景需要本地队列与重试策略（后续实现）。

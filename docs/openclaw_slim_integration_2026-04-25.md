# OpenClaw Slim Integration For DrMoto

## 目标

把 OpenClaw 里真正有价值的 agent runtime 能力，精简后融进 DrMoto AI。

不是把 OpenClaw 整个搬进来，而是：

- 保留：agent runtime
- 删除：多通道网关外壳、桌面/设备控制、与门店业务无关的通用插件层

## 从 OpenClaw 提炼出的核心能力

1. Workspace Prompt Bundle
2. Skills Runtime
3. Task Registry / Workflow Runtime
4. Heartbeat / Recovery
5. Tool Policy / Capability Boundary
6. Session Memory / Prompt Injection

## DrMoto 保留项

1. `workspace prompt bundle`
   - 用于固化 DrMoto agent 的角色、习惯、工具边界和心智模型
2. `skills runtime`
   - 用于按业务域注入能力
3. `task registry`
   - 用于承接 OCR、报价、工单跟进、多步任务
4. `heartbeat / recovery`
   - 用于模型异常时降级和恢复
5. `tool policy`
   - 用于明确 AI 当前允许调用的内部能力

## DrMoto 删除项

1. 多通道消息网关
   - 微信/Telegram/Slack/Discord 不是当前主战场
2. 远程设备配对
3. 桌面控制 / Canvas / 浏览器编排
4. 外部插件市场
5. 与 DrMoto 无关的通用消费级 skill

## 当前落地

1. `ai/app/core/skills.py`
   - 本地 skill 安装、加载、匹配
2. `ai/app/core/agent_runtime.py`
   - 精简版 OpenClaw runtime
3. `ai/app/routers/skills.py`
   - skill 管理接口
4. `ai/app/routers/agent_runtime.py`
   - runtime / tasks 可观察接口
5. `ai/data/agent_workspace/`
   - DrMoto 版 workspace prompt 骨架

## 下一步

1. 把 fast path 与 task registry 接起来
2. 让 skill 可以声明 `force_llm` / `bypass_fast_path`
3. 把 OCR、报价、工单跟进沉淀为显式 task
4. 给后台加 agent runtime 管理界面

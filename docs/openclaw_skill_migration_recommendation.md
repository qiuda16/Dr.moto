# OpenClaw Skill 迁移建议

时间：2026-04-26

## 已落地
- `memory-tiering`
- `automation-workflows`
- `cron-mastery`
- `obsidian`
- `agent-browser`

## 结论
- 机车博士当前已经覆盖了一部分 OpenClaw 的核心能力，但还没有完整接管所有 skill。
- 最值得迁移的是和“门店 AI 助手”强相关的 skill。
- 不建议迁移和当前业务弱相关、或容易引入复杂度的 skill。

## 本地 OpenClaw 已启用 skill
- `agent-browser`
- `automation-workflows`
- `cron-mastery`
- `find-skills`
- `github`  
- `memory-tiering`
- `obsidian`

## 机车博士当前已有的对应能力
- `memory-tiering` 的核心思想已在项目里落地为分层记忆。
- `automation-workflows` 的任务编排思想已在 AI/BFF 里有部分实现。
- `cron-mastery` 的定时/恢复思路可保留，但不需要完整搬运。
- `github` 不是业务 AI 能力，不需要进客服主链路。

## 建议优先迁移
### 1. `memory-tiering`
- 价值最高。
- 原因：你项目最需要的是长期一致性、实体锚点、历史上下文可回忆。
- 当前状态：已经有类似实现，但可以继续对齐 OpenClaw 的记忆层语义。

### 2. `automation-workflows`
- 适合承接：手册导入、写操作门禁、后续异步处理、回调续跑。
- 当前状态：已有任务和写链路，但可以把流程节点定义得更像 OpenClaw。

### 3. `cron-mastery`
- 适合承接：健康检查、恢复任务、定时复查、失败补偿。
- 当前状态：项目有恢复和任务机制，值得保留定时调度的思路。

### 4. `obsidian`
- 适合承接：知识沉淀、维修案例笔记、门店 SOP、人工标注档案。
- 当前状态：如果你后续想做“门店知识库笔记化”，这类 skill 很有价值。

### 5. `agent-browser`
- 适合承接：后台页面自动验证、流程冒烟测试、人工复核辅助。
- 当前状态：对“产品验收/测试”价值高，但不属于客服主链路必需。

## 建议保留但不优先迁移
- `find-skills`
- `github`
- `summarize`
- `proactive-agent`

说明：
- `find-skills` 更像技能发现工具，不是业务能力。
- `github` 对研发协作有用，但不该进入客户对话主链路。
- `summarize` 可作为知识整理辅助，但不是门店核心能力。
- `proactive-agent` 思路很强，但会增加行为复杂度，建议在稳定后再上。

## 暂不建议迁移
- `desktop-control`
- `multi-search-engine`
- `weather`
- `wps-office-automation-skill`
- `product-manager-toolkit`
- `self-improving-agent`
- `ontology`
- `pdf`
- `pmaster`
- `skillhub-preference`
- `ima-skill`

说明：
- 这些 skill 要么偏桌面/外部工具，要么偏通用生产力，要么和当前门店业务关联不强。
- 对你当前最重要的目标是“高成功率 + 高可信度 + 维修手册/客服统一”，这些 skill 暂时不是优先级。

## 对应到机车博士现状
- 已完成：
- 分层记忆
- 主模型路由
- 手册解析入库
- 写操作确认门禁
- 任务运行时

- 还可增强：
- 技能路由的粒度
- 记忆的可解释输出
- 异步流程节点
- 门店知识沉淀

## 推荐下一步
1. 先把 `memory-tiering` 的概念进一步标准化进项目文档和 prompt。
2. 再把 `automation-workflows` 的“流程节点”做成可配置。
3. 最后再考虑 `agent-browser` 和 `obsidian` 这类辅助 skill。

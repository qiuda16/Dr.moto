# AI 0 号员工交付说明（2026-04-07）

## 1. 交付范围

本次交付的是一套轻量化的 AI 业务助手，而不是独立 Agent 平台。核心原则如下：

- AI 不直连数据库，不直接写表。
- 所有查询和写操作统一经由 `BFF`。
- 允许 AI 做上下文汇总、建议动作、预填表单和执行低风险业务动作。
- 高风险动作仍保留人工确认。

当前已经覆盖 3 个落点：

- `bff`：统一 AI 上下文与受控动作网关
- `clients/cs_workspace`：客服/销售工作台
- `clients/web_staff`：员工工单详情页内嵌 AI 工单助理

---

## 2. 已交付能力

### 2.1 统一上下文

`BFF` 已提供统一聚合能力，AI 可以围绕这些业务对象进行理解：

- 客户
- 车辆
- 工单
- 推荐服务/维修项目
- 报价摘要
- 最近体检记录
- 车型知识资料
- 手册步骤
- 配件

接口：

- `POST /ai/ops/context`

### 2.2 受控写动作

AI 写动作不再拼 SQL，而是走统一动作接口：

- `create_customer`
- `update_customer`
- `create_customer_vehicle`
- `update_customer_vehicle`
- `create_work_order`
- `append_work_order_internal_note`
- `create_quote_draft`
- `create_part`
- `update_part`

接口：

- `POST /ai/ops/actions`

### 2.3 AI 助手代理

`BFF` 已提供 AI 助手代理接口，前端不用直连 AI 服务：

- `POST /ai/assistant/chat`

AI 返回内容包括：

- `response`
- `suggested_actions`
- `action_cards`

其中 `action_cards` 可用于“一键执行”或“先填表再确认”。

### 2.4 客服工作台

`clients/cs_workspace` 已具备：

- 登录
- 查询统一业务上下文
- 结构化业务表单
- 风险确认
- 最近动作回执
- AI 指令台
- AI 动作卡一键执行

### 2.5 员工工单工作台

`clients/web_staff` 的工单详情抽屉已集成 AI 助手：

- 基于当前工单、车型资料、报价、体检生成总结
- 检查风险和缺口
- 生成交付说明
- 返回结构化动作卡
- 支持“先填表”或“直接执行”

---

## 3. 关键文件

后端：

- `bff/app/routers/ai_ops.py`
- `bff/app/schemas/ai_ops.py`
- `bff/app/routers/ai_assistant.py`
- `bff/app/main.py`
- `ai/app/main.py`
- `bff/tests/test_ai_ops.py`

前端：

- `clients/cs_workspace/src/App.jsx`
- `clients/cs_workspace/src/index.css`
- `clients/web_staff/src/views/OrderListView.vue`

---

## 4. 建议演示路径

### 路径 A：客服/销售演示

1. 打开 `cs_workspace`
2. 登录后用客户名、车牌或工单号查询
3. 查看统一上下文返回的客户、车辆、工单、报价、知识资料
4. 在 AI 指令台输入：
   - “总结当前客户和工单情况，并建议下一步动作”
5. 点击 AI 返回的动作卡：
   - 追加内部备注
   - 生成报价草稿
   - 新建配件草稿
6. 查看动作回执，确认 BFF 已完成受控写入

### 路径 B：维修助理演示

1. 打开 `web_staff`
2. 进入工单列表，双击任意工单
3. 在“工单工作台”抽屉中找到“AI 工单助理”
4. 使用快捷问题：
   - “总结本单”
   - “检查风险”
   - “生成交付话术”
5. 查看 AI 返回：
   - 工单总结
   - 风险提示
   - 建议动作
   - 一键执行卡片
6. 选择“先填表”或“直接执行”
7. 执行后刷新工单详情，确认备注/报价等状态已变化

---

## 5. 验收清单

- 可以通过 `BFF` 获取统一 AI 上下文
- AI 不需要直接连数据库即可理解当前业务对象
- 客服工作台可以新增客户、车辆、工单、报价草稿、配件和工单备注
- 客服工作台可以通过 AI 指令台获得建议和动作卡
- 员工工单详情页可以直接调用 AI 助手
- AI 建议动作支持“先填表”或“直接执行”
- 所有写操作都通过 `BFF /ai/ops/actions`
- 中风险动作存在人工确认
- 写操作执行后可以在页面中看到结果或刷新后的状态
- `clients/cs_workspace` 可以成功构建
- `clients/web_staff` 可以成功构建

---

## 6. 启动与验证

### 后端

确保 `bff`、`ai`、`odoo` 相关依赖和环境变量已配置完成，再分别启动服务。

建议重点检查：

- `AI_URL`
- `INTERNAL_SERVICE_SECRET`
- 鉴权相关配置
- Odoo/BFF 数据源配置

### 前端构建验证

已完成验证：

- `clients/cs_workspace`：`npm.cmd run build`
- `clients/web_staff`：`npm.cmd run build`

### Python 侧验证

已完成：

- 关键 Python 文件 `py -3.9 -m py_compile` 语法校验通过

当前未完成的自动化验证：

- 完整 `pytest`

原因：

- 当前可用 Python 3.9 环境缺少 `redis` 等依赖，无法在本机直接完成整套测试运行

---

## 7. 上线前建议

- 为 `ai/ops/actions` 增加更细的动作审计落库
- 把“允许直执行 / 必须确认 / 禁止直写”整理成常量或配置表
- 为 AI 回复补更多来源证据，尤其是维修建议引用知识资料时
- 为客服工作台补“操作历史”列表，便于追踪谁执行了什么动作
- 在生产环境接入真实账号后，先用演示门店或测试门店跑一轮冒烟

---

## 8. 当前交付结论

截至 2026-04-07，这套“轻量 AI 0 号员工”已经达到可演示、可联调、可内测交付状态：

- 后端统一了 AI 读写入口
- 客服工作台可查、可写、可让 AI 建议并执行
- 员工工单页已具备维修助理能力

如果后续只做小步增强，建议优先补：

1. 动作审计持久化
2. 更细的权限分级
3. 更多更新类动作卡
4. 完整自动化测试环境

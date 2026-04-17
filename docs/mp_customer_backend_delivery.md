# MP车主端后端交付说明（V1）

> Date: 2026-03-30

## 1. 交付范围

已交付 `BFF` 侧车主端闭环能力：
- 微信登录票据 + 绑定
- 车主 JWT 会话与刷新
- 车主数据权限隔离（仅本人）
- 车辆/体检/保养记录/推荐/科普接口
- 提醒订阅偏好接口

## 2. 新增数据表

迁移文件：
- `bff/migrations/versions/0004_customer_app_auth.sql`
- 回滚模板：
- `bff/migrations/rollback_templates/0004_customer_app_auth_rollback.sql`

包含：
- `customer_wechat_bindings`
- `customer_auth_sessions`
- `customer_subscription_prefs`

## 3. 核心代码

- 路由：`bff/app/routers/customer_app.py`
- Schema：`bff/app/schemas/mp_customer.py`
- 模型：`bff/app/models.py`（新增三类）
- 配置：`bff/app/core/config.py`（新增 `WECHAT_APP_SECRET`）
- 路由注册：`bff/app/main.py`
- 测试：`bff/tests/test_mp_customer_api.py`
- 预检脚本：`scripts/preflight_mp_customer.ps1`
- 验收脚本：`scripts/mp_customer_acceptance.ps1`

## 4. 环境变量建议

必须：
- `BFF_SECRET_KEY`
- `BFF_DATABASE_URL`
- `BFF_REDIS_URL`

建议（生产）：
- `BFF_WECHAT_APP_ID`
- `BFF_WECHAT_APP_SECRET`
- `BFF_ENV=production`
- `BFF_ENABLE_DEV_ENDPOINTS=false`
- `BFF_ENABLE_MOCK_PAYMENT=false`

最小模板：
- `infra/.env.mp_customer.min.sample`

说明：
- 若未配置微信 `appid/secret`，当前实现会使用开发回退的 mock openid 逻辑，仅适合联调。

## 5. 验收清单

1. 能通过 `/mp/customer/auth/wechat-login` 获取未绑定票据。  
2. 能通过 `/mp/customer/auth/bind` 完成手机号+车牌绑定并返回 token。  
3. 使用该 token 访问 `/mp/customer/vehicles` 仅返回本人车辆。  
4. `/mp/customer/home` 能返回体检计数、推荐数量、最近工单状态。  
5. `/mp/customer/auth/logout` 后旧 token 失效。  
6. `/mp/customer/auth/refresh` 能签发新 access token。  

建议执行：
- `powershell -ExecutionPolicy Bypass -File scripts/preflight_mp_customer.ps1 -Phone "<客户手机号>" -PlateNo "<客户车牌>"`
- `powershell -ExecutionPolicy Bypass -File scripts/mp_customer_acceptance.ps1 -Phone "<客户手机号>" -PlateNo "<客户车牌>"`

## 6. 已知后续增强点

1. 将短信验证码校验替换为真实短信网关，不再接受固定码。  
2. 推荐项目从“车型模板”升级为“模板 + 里程 + 体检规则引擎”。  
3. 车主会话增加设备指纹与风控策略（异地登录告警）。  

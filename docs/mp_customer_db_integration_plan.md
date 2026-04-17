# MP客户库对接执行方案（V1）

> Date: 2026-03-30  
> Scope: 微信车主小程序（客户端）对接现有客户数据库（当前实现为 Odoo + BFF + PostgreSQL）

## 1. 目标与结论

本方案目标是让车主在微信端查看：
- 车辆体检信息
- 保养历史信息
- 推荐保养项目
- 保养件科普内容

结论：
- 现有主数据可直接复用，不需要重建客户库。
- 建议延续“微信小程序 -> BFF -> Odoo/PostgreSQL”的方式。
- 需要补齐微信身份绑定与车主权限隔离，才能安全上线。

## 2. 现有数据与能力盘点

已可复用（无需推翻）：
- 客户与车辆主数据：Odoo `res.partner` + `drmoto.partner.vehicle`
- 订单/保养记录：Odoo `drmoto.work.order`
- 体检数据：PostgreSQL `vehicle_health_records`
- 推荐模板：PostgreSQL `vehicle_service_template_*`
- 科普资料：PostgreSQL `vehicle_knowledge_documents`

关键缺口（必须补）：
- 微信 `openid/unionid` 与客户 `partner_id` 的绑定关系
- 车主端独立鉴权（不是后台管理员 token）
- 车主仅可访问“本人车辆”的数据权限

## 3. 字段映射表（现库 -> 小程序展示）

| 小程序模块 | 小程序字段 | 来源系统/表 | 来源字段 | 映射规则 |
|---|---|---|---|---|
| 我的车辆 | customerId | Odoo `res.partner` | `id` | 直接映射为 `partner_id` |
| 我的车辆 | customerName | Odoo `res.partner` | `name` | 去首尾空格 |
| 我的车辆 | phone | Odoo `res.partner` | `phone` | 展示时建议脱敏 `138****1234` |
| 我的车辆 | vehicleId | Odoo `drmoto.partner.vehicle` | `id` | 直接映射 |
| 我的车辆 | plateNo | Odoo `drmoto.partner.vehicle` | `license_plate` | 全部大写 + 去空格 |
| 我的车辆 | vin | Odoo `drmoto.partner.vehicle` | `vin` | 为空时返回 `null` |
| 我的车辆 | make/model/year | Odoo `drmoto.vehicle` | `make/model/year_from` | 通过 `vehicle_id` 关联读取 |
| 体检报告 | measuredAt | PG `vehicle_health_records` | `measured_at` | ISO8601 输出 |
| 体检报告 | odometerKm | PG `vehicle_health_records` | `odometer_km` | 保留 1 位小数 |
| 体检报告 | batteryVoltage | PG `vehicle_health_records` | `battery_voltage` | 为空时返回 `null` |
| 体检报告 | tireFrontPsi | PG `vehicle_health_records` | `tire_front_psi` | 为空时返回 `null` |
| 体检报告 | tireRearPsi | PG `vehicle_health_records` | `tire_rear_psi` | 为空时返回 `null` |
| 体检报告 | notes | PG `vehicle_health_records` | `notes` | 文本清洗后输出 |
| 保养记录 | orderId | Odoo `drmoto.work.order` | `id` / `bff_uuid` | 前端显示短号，内部保留双 ID |
| 保养记录 | orderNo | Odoo `drmoto.work.order` | `name` | 原样展示 |
| 保养记录 | status | Odoo `drmoto.work.order` | `state` | 映射中文状态 |
| 保养记录 | amountTotal | Odoo `drmoto.work.order` | `amount_total` | 保留 2 位小数 |
| 保养记录 | serviceDate | Odoo `drmoto.work.order` | `date_planned/create_date` | 优先 `date_planned` |
| 推荐项目 | serviceCode | PG `vehicle_service_template_items` | `part_code` | 为空可回退 `id` |
| 推荐项目 | serviceName | PG `vehicle_service_template_items` | `part_name` | 直接展示 |
| 推荐项目 | suggestedPrice | PG `vehicle_service_template_profiles` | `suggested_price` | 为空可返回 `null` |
| 推荐项目 | requiredParts | PG `vehicle_service_template_parts` | `part_name/qty` | 组装数组 |
| 科普内容 | docTitle | PG `vehicle_knowledge_documents` | `title` | 直接展示 |
| 科普内容 | docUrl | PG `vehicle_knowledge_documents` | `file_url` | 使用对象存储 URL |
| 科普内容 | category | PG `vehicle_knowledge_documents` | `category` | 建议标准化分类 |

## 4. 新增 3 张最小表（微信绑定/会话/提醒）

说明：不改 Odoo 主表，在 BFF 所在 PostgreSQL 新增“边车表”，最小侵入。

### 4.1 `customer_wechat_bindings`

用途：微信身份与客户主键绑定。

```sql
CREATE TABLE IF NOT EXISTS customer_wechat_bindings (
    id BIGSERIAL PRIMARY KEY,
    store_id VARCHAR(64) NOT NULL DEFAULT 'default',
    partner_id BIGINT NOT NULL,
    openid VARCHAR(128) NOT NULL,
    unionid VARCHAR(128),
    phone VARCHAR(32),
    is_primary BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(32) NOT NULL DEFAULT 'active', -- active/unbound
    bound_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    unbound_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_wechat_binding_store_openid
    ON customer_wechat_bindings (store_id, openid);

CREATE INDEX IF NOT EXISTS idx_wechat_binding_store_partner
    ON customer_wechat_bindings (store_id, partner_id);
```

### 4.2 `customer_auth_sessions`

用途：车主登录态管理（支持踢下线、设备追踪、风控）。

```sql
CREATE TABLE IF NOT EXISTS customer_auth_sessions (
    id BIGSERIAL PRIMARY KEY,
    store_id VARCHAR(64) NOT NULL DEFAULT 'default',
    partner_id BIGINT NOT NULL,
    binding_id BIGINT NOT NULL,
    session_token_hash VARCHAR(128) NOT NULL,
    refresh_token_hash VARCHAR(128),
    device_id VARCHAR(128),
    device_type VARCHAR(32), -- wechat_mini_program
    ip VARCHAR(64),
    user_agent VARCHAR(512),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_auth_session_token_hash
    ON customer_auth_sessions (session_token_hash);

CREATE INDEX IF NOT EXISTS idx_customer_auth_sessions_partner
    ON customer_auth_sessions (store_id, partner_id, expires_at DESC);
```

### 4.3 `customer_subscription_prefs`

用途：保养提醒与模板消息偏好设置。

```sql
CREATE TABLE IF NOT EXISTS customer_subscription_prefs (
    id BIGSERIAL PRIMARY KEY,
    store_id VARCHAR(64) NOT NULL DEFAULT 'default',
    partner_id BIGINT NOT NULL,
    vehicle_id BIGINT,
    notify_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    remind_before_days INTEGER NOT NULL DEFAULT 7,
    remind_before_km INTEGER NOT NULL DEFAULT 500,
    prefer_channel VARCHAR(32) NOT NULL DEFAULT 'wechat_subscribe',
    last_notified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_subscription_vehicle
    ON customer_subscription_prefs (store_id, partner_id, vehicle_id);
```

## 5. 车主端 API 清单（可直接排期）

原则：
- 车主端统一前缀：`/mp/customer/*`
- 后台员工端仍保留：`/mp/workorders/*`、`/mp/catalog/*`、`/mp/knowledge/*`
- 车主端 token 中必须包含：`sub=partner_id`、`role=customer`、`store_id`

### 5.1 认证与绑定

1. `POST /mp/customer/auth/wechat-login`
- 入参：`{ "code": "wx.login code", "store_id": "default" }`
- 逻辑：换取 `openid/unionid`，查询绑定关系，返回登录态或待绑定态
- 出参：
  - 已绑定：`{ "bound": true, "access_token": "...", "expires_in": 1800, "partner_id": 123 }`
  - 未绑定：`{ "bound": false, "openid": "...", "bind_ticket": "..." }`

2. `POST /mp/customer/auth/bind`
- 入参：`{ "bind_ticket": "...", "phone": "138...", "verify_code": "123456", "plate_no": "沪A12345" }`
- 逻辑：按手机号 + 车牌校验 Odoo 客户与车辆，写入 `customer_wechat_bindings`
- 出参：`{ "bound": true, "access_token": "...", "partner_id": 123 }`

3. `POST /mp/customer/auth/logout`
- 入参：无
- 逻辑：废弃当前 session
- 出参：`{ "success": true }`

### 5.2 车辆与首页

4. `GET /mp/customer/vehicles`
- 出参：当前车主可见车辆列表（仅本人）

5. `GET /mp/customer/home?vehicle_id=...`
- 出参聚合：
  - 最近体检摘要
  - 下次保养提醒（时间/里程）
  - 推荐项目数量
  - 最近一次工单状态

### 5.3 体检与保养记录

6. `GET /mp/customer/vehicles/{vehicle_id}/health-records?limit=20`
- 数据源：复用 `vehicle_health_records` 查询逻辑

7. `GET /mp/customer/vehicles/{vehicle_id}/maintenance-orders?page=1&size=20`
- 数据源：复用 Odoo `drmoto.work.order`
- 过滤：`customer_id == token.partner_id` 且 `vehicle_id/plate` 属于本人

8. `GET /mp/customer/maintenance-orders/{order_id}`
- 返回工单详情、金额、状态、项目明细

### 5.4 推荐与科普

9. `GET /mp/customer/vehicles/{vehicle_id}/recommended-services`
- 数据源：`vehicle_service_template_*` + 当前里程 + 最近保养时间
- 返回字段建议：`level(must/suggest/optional)`、`reason`、`suggested_price`

10. `GET /mp/customer/vehicles/{vehicle_id}/knowledge-docs`
- 数据源：`vehicle_knowledge_documents`
- 按车型过滤，支持分类查询

## 6. 权限与安全规则（上线前必须）

1. 车主 token 仅允许 `role=customer` 访问 `/mp/customer/*`。  
2. 所有 `/mp/customer/*` 查询都必须附带 `partner_id = token.sub` 条件。  
3. 禁止通过 URL 直接传他人 `partner_id` 访问数据。  
4. 手机号、VIN、车牌默认脱敏展示。  
5. 绑定、解绑、登录失败要写审计日志。  

## 7. 实施顺序（建议两周）

第 1 周：
1. 新增三张表 + 迁移脚本  
2. 微信登录与绑定 API  
3. 车主 token 与鉴权中间件  

第 2 周：
1. 车辆列表/首页聚合/体检记录 API  
2. 保养记录与推荐接口  
3. 科普接口与提醒偏好接口  
4. 联调与灰度测试  

## 8. 验收标准

1. 车主能通过微信完成登录并绑定本人车辆。  
2. 车主只能看到自己的车辆、工单和体检记录。  
3. 首页可展示体检摘要、保养记录、推荐项目和科普入口。  
4. 推荐项目包含明确依据（里程/时间/检测项）。  
5. 关键接口具备基本审计与错误追踪能力（`trace_id`）。  

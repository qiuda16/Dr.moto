# 微信云托管部署 BFF（FastAPI）

## 1. 适用场景

你已经创建了微信云托管服务：`flask-i7ja`。
本指南用于把该服务从 Flask 示例替换为本项目 BFF（FastAPI）。

## 2. 推荐部署方式

- 代码源：本仓库 `bff/`
- Dockerfile：`bff/deploy/cloudbase/Dockerfile`
- 监听端口：`8080`（自动读取 `PORT`）

## 3. 云托管构建配置

在微信云托管控制台中设置：

1. 构建上下文目录：`bff`
2. Dockerfile 路径：`deploy/cloudbase/Dockerfile`
3. 容器端口：`8080`
4. 健康检查路径：`/health`

## 4. 环境变量（必须）

参考文件：`bff/deploy/cloudbase/.env.cloudbase.sample`

最关键变量：

- `BFF_ENV=prod`
- `BFF_DATABASE_URL`
- `BFF_REDIS_URL`
- `BFF_SECRET_KEY`
- `BFF_WECHAT_APP_ID=wx0bfeb41d1fdc1999`
- `BFF_WECHAT_APP_SECRET`
- `BFF_ENABLE_DEV_ENDPOINTS=false`
- `BFF_ENABLE_MOCK_PAYMENT=false`

## 5. 路径前缀说明（非常重要）

BFF 接口默认是：

- `/health`
- `/mp/customer/...`

你的小程序已支持云托管双路径：

- 先按 `VITE_TCB_BASE_PATH` 调用（例如 `/api`）
- 若返回 404，会自动重试无前缀路径

因此你可以先保持：

- `VITE_TCB_BASE_PATH=/api`

如果你在云托管层已配置去前缀，也可以设为空。

## 6. 部署后验证

先用云托管测试调用：

- `path=/health`
- `X-WX-SERVICE=flask-i7ja`

再测登录接口：

- `path=/mp/customer/auth/wechat-login`
- `method=POST`
- `data={"code":"临时code","store_id":"default"}`

## 7. 小程序侧配置

`clients/mp_customer_uni/.env` 已建议配置：

- `VITE_TCB_ENV=prod-9gbcay06c7c9a82b`
- `VITE_TCB_SERVICE=flask-i7ja`
- `VITE_TCB_BASE_PATH=/api`

构建命令：

```bash
npm run build:mp-weixin
```

## 8. 常见问题

1. `/health` 返回 404：容器里仍是 Flask 示例，未替换为 BFF。
2. 登录 502：`BFF_WECHAT_APP_ID/SECRET` 未正确配置或微信接口不可达。
3. 401：token 失效或容器重启导致旧会话失效，重新登录即可。

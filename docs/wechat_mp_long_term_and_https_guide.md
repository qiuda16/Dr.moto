# 车主小程序长期方案与后端 HTTPS 上线指南

## 1. 长期方案架构（推荐）

- 客户端：`clients/mp_customer_uni`（uni-app 原生小程序）
- 后端：BFF（容器内 `:8080`，宿主机 `:18080`）
- 公网入口：`https://api.your-domain.com`（Nginx 反向代理 + TLS）
- 数据层：PostgreSQL

## 2. 小程序登录链路（已落地）

- 客户端在微信端使用 `uni.login` 获取 `code`
- 服务端 `/mp/customer/auth/wechat-login` 调微信 `jscode2session`
- 若已绑定：直接返回 token
- 若未绑定：返回 `bind_ticket`，再调用 `/mp/customer/auth/bind`

注意：
- 生产环境（`BFF_ENV=prod`）必须配置 `BFF_WECHAT_APP_ID` 与 `BFF_WECHAT_APP_SECRET`
- 生产环境下不再允许 mock openid 回退

## 3. 后端公网 HTTPS 上线步骤

### 第一步：准备域名与服务器

1. 准备域名，例如 `api.your-domain.com`
2. A 记录指向服务器公网 IP
3. 开放端口 `80`、`443`

### 第二步：部署 Nginx

1. 安装 Nginx
2. 使用配置模板：`infra/nginx/bff_https.conf.sample`
3. 把 `api.your-domain.com` 替换成真实域名

### 第三步：申请证书

```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.your-domain.com
sudo certbot renew --dry-run
```

### 第四步：配置 BFF 生产环境变量

建议从 `infra/.env.prod.sample` 复制为生产 `.env`，至少配置：

- `BFF_ENV=prod`
- `BFF_DATABASE_URL=...`
- `BFF_WECHAT_APP_ID=...`
- `BFF_WECHAT_APP_SECRET=...`
- `BFF_ENABLE_DEV_ENDPOINTS=false`
- `BFF_ENABLE_MOCK_PAYMENT=false`

### 第五步：重启 BFF

```bash
cd infra
docker compose --env-file .env up -d bff
```

### 第六步：验证 HTTPS 与接口

```bash
curl -I https://api.your-domain.com/health
```

应返回 `200`。

## 4. 微信公众平台配置

在微信公众平台 -> 开发管理 -> 开发设置：

1. `request 合法域名` 添加 `https://api.your-domain.com`
2. 若有上传/下载，再配置 upload/download 合法域名

## 5. 小程序构建与上传

1. 在 `clients/mp_customer_uni/.env` 配置：
   - `VITE_API_BASE=https://api.your-domain.com`
2. 构建：

```bash
npm run build:mp-weixin
```

3. 微信开发者工具导入：
   - `clients/mp_customer_uni/dist/build/mp-weixin`
4. 上传版本，提体验版 -> 提审 -> 发布

## 6. 审核前必做

1. 隐私政策与用户协议页面完善
2. 客服与联系方式可访问
3. 全链路回归：登录、车辆、体检、保养、推荐、科普
4. 生产数据库已备份

# DrMoto 部署记录

时间：2026-04-26

## 已完成

1. 将本地项目同步到云服务器。
2. 在云服务器 `42.193.113.172` 上用 Docker Compose 启动了核心服务。
3. 初始化了数据库：
   - 创建 `bff` 数据库
   - 初始化 Odoo `base` 模块
4. 在服务器上安装并配置了 `nginx`。
5. 申请并部署了 Let's Encrypt 证书。
6. 将正式域名接入到服务器：
   - `drmoto.cloud`
   - `www.drmoto.cloud`
7. 将小程序默认 API 地址切到线上域名：
   - `https://drmoto.cloud`

## 当前可访问地址

- `https://drmoto.cloud/health`
- `https://www.drmoto.cloud/health`
- `http://42.193.113.172/health`

## 服务器信息

- 公网 IP：`42.193.113.172`
- 系统：Ubuntu
- 登录用户名：`ubuntu`

## SSH 登录信息

- 登录方式：用户名 + 密码
- 用户名：`ubuntu`
- 密码：`Tianxiang2,`

## 服务器上已部署的服务

- `db`：PostgreSQL
- `redis`
- `odoo`
- `bff`
- `minio`
- `ai`
- `db-ui`

## 证书信息

- 域名：`drmoto.cloud`
- 子域名：`www.drmoto.cloud`
- 证书路径：`/etc/letsencrypt/live/drmoto.cloud/fullchain.pem`
- 私钥路径：`/etc/letsencrypt/live/drmoto.cloud/privkey.pem`

## 关键配置变更

- `clients/mp_customer_uni/src/config/env.js`
  - 默认 `API_BASE` 改为 `https://drmoto.cloud`
- `infra/docker-compose.yml`
  - 容器端口改为只绑定 `127.0.0.1`
  - `ocr_vl` 保持不启用 GPU 暴露

## Nginx 入口

- 80 端口：自动跳转或提供入口
- 443 端口：正式 HTTPS 入口
- 反向代理到本机：
  - `127.0.0.1:18080` -> BFF

## 备注

- 这是本地明文记录，适合你自己保管。
- 如果后续改了密码、域名或端口，建议同步更新这份记录。


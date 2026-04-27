# DrMoto 线上部署与运维说明

更新时间：2026-04-27

本文档用于让新接手的人快速理解“机车博士 DrMoto”当前线上环境是什么、怎么访问、怎么部署、怎么测试、哪里还没完成。  
注意：本文档包含线上账号密码等敏感信息，只能留在本地或受控私有仓库中，不要公开发送，不要提交到公开 GitHub。

## 1. 当前结论

当前线上系统已经部署在腾讯云服务器上，后端、数据库、AI 服务、Odoo、MinIO、Redis、Nginx 都在运行。

现在可用入口：

```text
http://<SERVER_IP>
```

当前域名：

```text
<ROOT_DOMAIN>
<PUBLIC_DOMAIN>
```

域名当前有公网访问拦截问题。访问 `<PUBLIC_DOMAIN>` 时，公网侧可能被跳转到：

```text
https://dnspod.qcloud.com/static/webblock.html?d=<PUBLIC_DOMAIN>
```

这不是 DrMoto 程序返回的页面，而是云厂商或 DNSPod 的域名拦截页。典型原因是：中国大陆服务器绑定域名正式访问前需要完成 ICP 备案或接入备案。备案完成前，建议临时使用服务器 IP 访问。

## 2. 服务器信息

服务器公网 IP：

```text
<SERVER_IP>
```

服务器登录用户：

```text
ubuntu
```

线上项目路径：

```text
/home/ubuntu/drmoto
```

Docker Compose 路径：

```text
/home/ubuntu/drmoto/infra
```

Nginx 站点配置：

```text
/etc/nginx/sites-available/drmoto
/etc/nginx/sites-enabled/default -> /etc/nginx/sites-available/drmoto
```

前端静态文件目录：

```text
/var/www/drmoto/web_staff
```

Nginx 配置备份目录：

```text
/root/nginx-config-backups
```

## 3. 访问入口

### 3.1 管理后台

当前临时可用：

```text
http://<SERVER_IP>
```

域名入口目前不稳定或被拦：

```text
https://<PUBLIC_DOMAIN>
https://<ROOT_DOMAIN>
```

原因见“域名和备案状态”。

### 3.2 后端健康检查

```text
http://<SERVER_IP>/api/health
```

正常返回类似：

```json
{
  "status": "ok",
  "db": "ok",
  "odoo": "ok",
  "version": "0.1.0",
  "env": "dev"
}
```

### 3.3 登录接口

公网 Nginx 入口：

```text
POST http://<SERVER_IP>/api/auth/token
```

Nginx 会把 `/api/auth/token` 转发到 BFF 内部的：

```text
http://<BFF_LOCAL_PORT>/auth/token
```

前端 axios 的 `baseURL` 是：

```text
/api
```

所以前端登录最终会请求：

```text
/api/auth/token
```

## 4. 账号说明

当前已经创建过三个管理员账号：

```text
fzy
yjk
sqy
```

这三个账号都是全权限管理账号。

## 4.1 敏感信息处理原则

账号、密码、API 地址、密钥和可直接登录的凭据不要写进仓库。  
如果需要留存，建议只在本机私有笔记、密码管理器或受控的私有文档里保存。

如需排障，请在本地环境变量、服务器私有配置文件或临时运维记录中查找，不要把这些内容提交到 Git。

### 常见示例

以下内容只保留“类型说明”，具体值请在本地私有配置中查看：

- 服务器 SSH 凭据
- 管理后台账号密码
- PostgreSQL / Odoo / MinIO 默认连接信息
- BFF 管理员环境变量
- AI Provider / OpenClaw 配置 JSON 路径
## 5. 服务架构

线上系统大体结构如下：

```text
浏览器/小程序
  |
  v
Nginx
  |
  |-- /              -> /var/www/drmoto/web_staff 前端静态文件
  |-- /api/*         -> BFF FastAPI
  |-- /mp/*          -> BFF FastAPI 小程序相关接口
  |-- /health        -> BFF 健康检查
  |
  v
Docker Compose 服务
  |
  |-- bff            -> 业务后端、登录、客户库、工单、AI ops
  |-- ai             -> AI 助手、维修手册识别、OpenClaw 风格 agent 能力
  |-- odoo           -> Odoo 18，业务底座
  |-- db             -> PostgreSQL 15，包含 odoo 与 bff 数据库
  |-- redis          -> AI 记忆、缓存、限流等
  |-- minio          -> 对象存储
  |-- db-ui          -> Adminer 数据库管理界面，仅绑定本机
  |-- ocr_vl         -> 旧 OCR 服务，当前维修手册主流程倾向 AI 原生解析
```

## 6. Docker Compose 服务

线上 compose 文件：

```text
/home/ubuntu/drmoto/infra/docker-compose.yml
```

主要服务：

```text
db       PostgreSQL 15
redis    Redis 7
odoo     Odoo 18
bff      FastAPI 业务后端
ai       AI 服务
minio    对象存储
db-ui    Adminer
ocr_vl   PaddleOCR-VL 服务
```

当前端口绑定策略：

```text
<BFF_LOCAL_PORT> -> bff:8080
127.0.0.1:8001  -> ai:8000
<ODOO_LOCAL_PORT>  -> odoo:8069
127.0.0.1:8082  -> db-ui:8080
<MINIO_API_LOCAL_PORT>  -> minio api
<MINIO_CONSOLE_LOCAL_PORT>  -> minio console
```

这些服务大多只绑定 `127.0.0.1`，公网不能直接访问，必须经过 Nginx 或 SSH 隧道。这是为了降低暴露面。

## 7. Nginx 反向代理

当前 Nginx 做三件事：

```text
/assets/*  静态资源缓存
/          前端 SPA fallback 到 index.html
/api/*     去掉 /api 前缀后转发到 BFF
/mp/*      转发到 BFF
```

关键规则：

```nginx
location ^~ /api/ {
    rewrite ^/api/(.*)$ /$1 break;
    proxy_pass http://<BFF_LOCAL_PORT>;
    proxy_read_timeout 300s;
    proxy_connect_timeout 60s;
    proxy_send_timeout 300s;
}
```

AI 回复可能较慢，所以代理超时已经拉长到 300 秒。

## 8. 域名和备案状态

域名：

```text
<ROOT_DOMAIN>
<PUBLIC_DOMAIN>
```

DNS 当前解析到：

```text
<SERVER_IP>
```

证书状态：

```text
Let's Encrypt RSA 证书
CN = <ROOT_DOMAIN>
SAN = <ROOT_DOMAIN>, <PUBLIC_DOMAIN>
到期时间：2026-07-26
```

已经从 ECDSA 证书切换为 RSA 证书，以提高 Windows、微信内置浏览器、老设备兼容性。

但是域名仍然可能被公网侧拦截。已观察到：

```text
http://<PUBLIC_DOMAIN>/api/health
```

返回：

```text
302 -> https://dnspod.qcloud.com/static/webblock.html?d=<PUBLIC_DOMAIN>
```

这不是 Nginx 或 DrMoto 返回的内容。  
要让域名正式可用，需要完成 ICP 备案或腾讯云接入备案。备案完成前，建议用 IP 访问。

## 9. AI 架构

当前 AI 服务默认走 OpenClaw 风格 provider 配置：

```text
AI_LLM_PROVIDER=openclaw
OPENCLAW_CONFIG_JSON=/app/data/provider/openclaw.json
OPENCLAW_MODELS_JSON=/app/data/provider/models.json
OPENCLAW_TIMEOUT_SECONDS=300
```

AI 服务位置：

```text
/home/ubuntu/drmoto/ai
```

AI 数据与 agent workspace：

```text
/home/ubuntu/drmoto/ai/data
/home/ubuntu/drmoto/ai/data/openclaw_drmoto_workspace
/home/ubuntu/drmoto/ai/data/openclaw_drmoto_state
```

已经迁移或配置过的 skill：

```text
memory-tiering
automation-workflows
cron-mastery
obsidian
agent-browser
```

AI 记忆后端：

```text
redis://redis:6379/1
```

AI 对 BFF 的访问：

```text
BFF_URL=http://bff:8080
```

AI 回复模式当前是 model-first，不再强行套固定模板：

```text
AI_LLM_FIRST_RESPONSES=true
```

## 10. AI 助手数据库权限

AI 助手已经具备 L4 数据库操作能力，可以通过受控工具查询、增加、修改、删除数据库记录。

当前支持：

```text
database_schema
database_select
database_insert
database_update
database_delete_plan
database_delete_confirm
database_undo
```

安全规则：

```text
删除必须先 database_delete_plan
删除计划会返回 confirmation_token
只有拿 confirmation_token 才能 database_delete_confirm
新增、修改、确认删除都会写 audit_logs
新增、修改、确认删除成功后会返回 undo_id
用 database_undo + undo_id 可以撤销
单次可撤销快照最多 5000 行
database_update 必须有 filters，除非明确 allow_all=true
```

审计表：

```text
audit_logs
```

审计内容：

```text
actor_id
action
target_entity
before_state
after_state
created_at
```

返回示例：

```json
{
  "status": "ok",
  "action": "database_update",
  "result": {
    "target_database": "bff",
    "table": "xxx",
    "updated_rows": 1,
    "audit_id": 11,
    "undo_available": true,
    "undo_id": 11
  },
  "risk_level": "high"
}
```

撤销示例：

```json
{
  "action": "database_undo",
  "payload": {
    "undo_id": 11
  }
}
```

## 11. 维修手册识别

当前维修手册解析方向已经从“传统 OCR 为主”调整为“AI 原生解析为主”。

关键配置：

```text
MANUAL_PARSE_MODE=ai_native
MANUAL_PARSE_ALLOW_LEGACY_OCR_FALLBACK=false
OCR_LLM_PROVIDER=openclaw
OCR_LLM_TIMEOUT_SECONDS=300
```

注意：

```text
ocr_vl 服务仍在 compose 中，但不再作为维修手册主路径。
如果后续遇到超大 PDF 或 AI 原生解析失败，可以再决定是否启用 OCR fallback。
```

## 12. 部署流程

### 12.1 登录服务器

```powershell
ssh ubuntu@<SERVER_IP>
```

如果使用密码登录，密码从项目负责人处获取。  
如果使用 SSH key，请把公钥加入服务器的：

```text
/home/ubuntu/.ssh/authorized_keys
```

### 12.2 进入项目

```bash
cd /home/ubuntu/drmoto
```

### 12.3 重建并启动全部服务

```bash
cd /home/ubuntu/drmoto/infra
sudo docker compose up -d --build
```

### 12.4 只重建 BFF

```bash
cd /home/ubuntu/drmoto/infra
sudo docker compose up -d --build bff
```

### 12.5 只重建 AI

```bash
cd /home/ubuntu/drmoto/infra
sudo docker compose up -d --build ai
```

### 12.6 查看服务状态

```bash
cd /home/ubuntu/drmoto/infra
sudo docker compose ps
```

### 12.7 查看日志

```bash
cd /home/ubuntu/drmoto/infra
sudo docker compose logs --tail=200 bff
sudo docker compose logs --tail=200 ai
sudo docker compose logs --tail=200 odoo
sudo docker compose logs --tail=200 db
```

## 13. 前端部署

前端源码：

```text
clients/web_staff
```

线上静态目录：

```text
/var/www/drmoto/web_staff
```

前端构建后，需要把 dist 内容同步到线上静态目录。典型流程：

```bash
cd clients/web_staff
npm install
npm run build
```

然后把 `dist` 内文件放到服务器：

```text
/var/www/drmoto/web_staff
```

当前线上前端会请求相对路径：

```text
/api
```

所以前端无需写死服务器 IP 或域名。

## 14. 小程序部署要点

小程序需要在微信公众平台配置服务器域名。

当域名备案完成后，推荐配置：

```text
request 合法域名：https://<PUBLIC_DOMAIN>
uploadFile 合法域名：https://<PUBLIC_DOMAIN>
downloadFile 合法域名：https://<PUBLIC_DOMAIN>
socket 合法域名：如暂未使用 WebSocket，可先不填
```

备案完成前，如果微信平台不允许 IP 或未备案域名，小程序正式发布会受阻。  
开发阶段可以使用开发者工具的不校验合法域名选项，但这不能用于正式上线。

## 15. 常用测试命令

### 15.1 测健康检查

```bash
curl -i http://<SERVER_IP>/api/health
```

### 15.2 测登录

```bash
curl -i -X POST http://<SERVER_IP>/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "username=fzy&password=你的密码"
```

### 15.3 服务器内测 BFF

```bash
curl -i http://<BFF_LOCAL_PORT>/health
```

### 15.4 服务器内测 Nginx

```bash
curl -i http://127.0.0.1/api/health
curl -k -i https://127.0.0.1/api/health
```

### 15.5 检查证书

```bash
sudo openssl x509 -in /etc/letsencrypt/live/<ROOT_DOMAIN>/fullchain.pem -noout -subject -issuer -dates -ext subjectAltName
```

### 15.6 检查 Nginx 配置

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 16. 数据库

PostgreSQL 容器：

```text
db
```

数据库：

```text
odoo
bff
```

进入 psql：

```bash
cd /home/ubuntu/drmoto/infra
sudo docker compose exec db psql -U odoo -d bff
sudo docker compose exec db psql -U odoo -d odoo
```

不要在没有备份的情况下直接改生产数据。  
如果必须让 AI 或人工改数据，优先走 BFF 的 AI ops 工具，因为那里有审计日志和撤销能力。

## 17. 备份建议

正式上线前，必须补齐自动备份。

最低要求：

```text
每日备份 PostgreSQL
每日备份 MinIO 数据
每日备份 ai/data
保留最近 7 天日备份
保留最近 4 周周备份
至少每月做一次恢复演练
```

PostgreSQL 手工备份示例：

```bash
cd /home/ubuntu/drmoto/infra
sudo docker compose exec db pg_dump -U odoo bff > bff_$(date +%Y%m%d_%H%M%S).sql
sudo docker compose exec db pg_dump -U odoo odoo > odoo_$(date +%Y%m%d_%H%M%S).sql
```

## 18. 已做过的重要线上操作

### 18.1 初始云端部署

已经在服务器上创建：

```text
/home/ubuntu/drmoto
/home/ubuntu/drmoto/infra
/var/www/drmoto/web_staff
```

已经通过 Docker Compose 启动主要服务：

```text
db
redis
odoo
bff
ai
minio
db-ui
ocr_vl
```

### 18.2 登录保护

管理后台已改为需要登录后才能进入界面。  
未登录访问业务页面会跳转到 `/login`。

### 18.3 管理员账号

已创建三个管理员账号：

```text
fzy
yjk
sqy
```

### 18.4 AI 超时调整

AI 对话和相关代理超时已调整到 300 秒：

```text
AI_PROXY_TIMEOUT_SECONDS=300
OPENCLAW_TIMEOUT_SECONDS=300
OLLAMA_TIMEOUT_SECONDS=300
OCR_LLM_TIMEOUT_SECONDS=300
前端 axios timeout=300000 ms
```

### 18.5 AI 数据库 L4 权限

已经添加：

```text
任意表 schema 查询
任意表 select
任意表 insert
任意表 update
删除预览
删除确认
审计日志
undo 撤销
```

### 18.6 证书调整

Let's Encrypt 证书已从 ECDSA 换成 RSA，提升兼容性：

```text
Issuer: Let's Encrypt R13
Public Key Algorithm: rsaEncryption
Signature Algorithm: sha256WithRSAEncryption
```

### 18.7 HTTP 临时入口

由于域名当前被公网拦截，已开放 IP 的 HTTP 入口：

```text
http://<SERVER_IP>
```

## 19. 当前已知问题

### 19.1 域名访问被拦截

现象：

```text
访问 <PUBLIC_DOMAIN> 可能跳到 dnspod.qcloud.com/static/webblock.html
```

判断：

```text
不是 DrMoto 程序问题
不是 BFF 登录问题
不是数据库问题
不是账号密码问题
```

最可能原因：

```text
大陆云服务器 + 绑定域名 + 未完成 ICP 备案或接入备案
```

临时解决：

```text
使用 http://<SERVER_IP>
```

正式解决：

```text
完成域名备案和腾讯云接入备案
备案完成后再恢复正式域名访问
```

### 19.2 HTTPS 域名在本机握手失败

在当前本地 Windows 环境中，用域名访问 HTTPS 曾出现：

```text
schannel: failed to receive handshake
SSL/TLS connection failed
```

服务器本机用 SNI 测试正常，公网 IP 测试正常。  
该问题与域名公网拦截高度相关，备案完成后需要再次复测。

### 19.3 OCR 服务不是主路径

`ocr_vl` 仍在运行，但当前维修手册主方向是 AI 原生解析。  
如果要完全移除 OCR 服务，需要再确认大 PDF、扫描版 PDF、图片版手册的处理方案。

## 20. 上线前必须完成的清单

正式对客户开放前，至少要完成：

```text
域名 ICP 备案或接入备案
HTTPS 域名访问复测
小程序合法域名配置
数据库自动备份
MinIO 自动备份
AI API Key 正式化管理
关闭不必要的 dev endpoint
检查 SECRET_KEY 和管理员密码是否为生产强密码
检查 CORS 是否不要长期使用 *
配置服务器安全组，只开放 80/443/SSH 必要端口
建立故障恢复文档
建立上线回滚流程
```

## 21. 新人接手时先看什么

建议顺序：

```text
1. 先打开 http://<SERVER_IP> 看前端是否能访问
2. 打开 http://<SERVER_IP>/api/health 看后端健康
3. SSH 登录服务器，看 docker compose ps
4. 看 /home/ubuntu/drmoto/infra/docker-compose.yml
5. 看 /etc/nginx/sites-available/drmoto
6. 看 bff/app/routers/ai_ops.py 理解 AI 数据库写操作
7. 看 ai/app/core/customer_agent.py 理解 AI 助手工具清单
8. 看 ai/data/openclaw_drmoto_workspace 理解 agent 记忆和工作区
```

## 22. 快速排障表

| 问题 | 先查什么 | 常见原因 |
| --- | --- | --- |
| 页面打不开 | `curl http://<SERVER_IP>/` | Nginx、静态文件、服务器网络 |
| 登录失败 | `curl /api/auth/token` | 密码错误、BFF 异常、数据库异常 |
| 客户库 500 | `docker compose logs bff` | BFF 代码异常、Odoo 异常、数据库连接异常 |
| AI 超时 | `docker compose logs ai bff` | 模型 API 慢、OpenClaw provider 配置异常 |
| 域名跳拦截页 | 浏览器地址和 curl 返回 | 未备案或接入备案未完成 |
| HTTPS 握手失败 | `openssl s_client` | 证书链、SNI、云厂商拦截、本地网络 |
| 数据误改 | 查 `audit_logs`，用 `database_undo` | 使用 undo_id 撤销 |

## 23. 不要做的事

```text
不要把服务器密码写进 README
不要把 AI API Key 写进 README
不要直接对生产库 DROP/DELETE，除非已经备份并确认
不要随便 docker compose down -v，这会删除卷数据
不要把 db-ui、minio、odoo 直接暴露到公网
不要在未备案前依赖 <ROOT_DOMAIN> 做正式上线
```

## 24. 推荐下一步

```text
1. 做 ICP 备案/腾讯云接入备案
2. 备案完成后恢复并复测 https://<PUBLIC_DOMAIN>
3. 建立自动备份脚本
4. 把生产 secrets 迁移到 .env 或云端密钥管理，不要散落在 compose 默认值里
5. 给 AI 数据库操作增加前端确认面板，让用户能清楚看到 AI 要改哪张表、哪些字段
6. 做一次完整恢复演练：从备份恢复 bff、odoo、minio、ai/data
```



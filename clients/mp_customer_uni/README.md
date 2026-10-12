# mp_customer_uni（标准长期方案）

这是面向微信小程序的原生工程（uni-app），用于替代当前 H5 方案，支持长期演进。

## 1. 安装与开发

```bash
npm install
npm run dev:mp-weixin
```

## 2. 生产构建（微信小程序）

```bash
npm run build:mp-weixin
```

构建产物目录：`dist/build/mp-weixin`

## 3. 微信开发者工具导入

1. 打开微信开发者工具
2. 选择“导入项目”
3. 项目目录选择：`dist/build/mp-weixin`
4. AppID 使用你的小程序正式 AppID

## 4. 配置 API

复制 `.env.example` 为 `.env`，按需配置：

- `VITE_API_BASE`：小程序和 H5 的 HTTPS API 地址，生产环境必须显式配置，例如 `https://api.example.com/api`
- `VITE_API_FALLBACK_BASE`：当主地址网络失败时的兜底地址，默认留空
- `VITE_USE_CLOUD_CONTAINER`：是否改回云托管调用，默认 `false`
- `VITE_TCB_ENV`：云托管环境 ID，只有切回云托管时才需要
- `VITE_TCB_SERVICE`：云托管服务名，只有切回云托管时才需要
- `VITE_TCB_BASE_PATH`：云托管服务路径前缀（例如 `/api`）

说明：
- 生产构建必须通过环境变量显式注入 HTTPS `VITE_API_BASE`，不再使用服务器 IP 或 HTTP 地址。
- 如果你手动配置了 `VITE_API_FALLBACK_BASE`，前端才会在主地址失败时继续尝试。
- 如果把 `VITE_USE_CLOUD_CONTAINER` 设为 `true`，微信小程序端会改回 `wx.cloud.callContainer`。

## 5. 当前页面

- 驾驶舱：`pages/index/index`
- 商城：`pages/shop/index`
- 我的：`pages/mine/index`
- 绑定车主：`pages/bind/index`
- 车辆详情：`pages/vehicle/detail`
- 预约草稿：`pages/appointment/index`
- 最近任务：`pages/history/index`
- 商品详情：`pages/shop/detail`

## 6. 注意事项

- 小程序正式环境必须使用 HTTPS 或云托管调用。
- 正式登录依赖后端 `WECHAT_APP_ID/WECHAT_APP_SECRET` 配置。
# Trial Release Build

WeChat production compilation requires an absolute HTTPS `VITE_API_BASE` when cloud
container mode is disabled, and rejects `VITE_ALLOW_DEMO_FALLBACK=true`. Keep local
`.env` and `project.private.config.json` outside Git. `project.config.json` contains
the public AppID and imports `dist/build/mp-weixin/` into WeChat DevTools.

CI uses Node 20 and `MP_CUSTOMER_API_BASE` from GitHub repository variables, defaulting
to `https://drmoto.cloud/api`. This default is a target address, not evidence that DNS,
TLS or WeChat request-domain setup is ready. Compilation artifacts require real login,
binding and device acceptance before publication.

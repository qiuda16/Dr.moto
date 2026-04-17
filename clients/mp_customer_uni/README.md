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

- `VITE_TCB_ENV`：云托管环境 ID
- `VITE_TCB_SERVICE`：云托管服务名
- `VITE_TCB_BASE_PATH`：服务路径前缀（例如 `/api`）
- `VITE_API_BASE`：H5 调试备用地址

说明：
- 在微信小程序端，项目会优先走 `wx.cloud.callContainer`。
- 在 H5 端，项目会走 `VITE_API_BASE`。

## 5. 当前页面

- 登录：`pages/auth/login`
- 首页：`pages/dashboard/index`
- 体检：`pages/health/index`
- 保养：`pages/maintenance/index`
- 推荐：`pages/recommendations/index`
- 科普：`pages/knowledge/index`
- 我的：`pages/profile/index`
- 隐私政策：`pages/privacy/index`
- 用户协议：`pages/agreement/index`

## 6. 注意事项

- 小程序正式环境必须使用 HTTPS 或云托管调用。
- 正式登录依赖后端 `WECHAT_APP_ID/WECHAT_APP_SECRET` 配置。

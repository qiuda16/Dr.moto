# DrMoto Landing Site

机车博士官网独立站。根路径用于品牌展示和获客，SaaS 后台作为官网里的登录入口。

## Local Development

```bash
npm install
npm run dev
```

## Environment

```bash
VITE_APP_LOGIN_URL=/app
VITE_API_BASE=/api
```

单域名部署时可以将官网放在 `/`，后台通过反向代理或静态路径放在 `/app`。

## Delivery

The website includes rider/workshop enquiry entry points, a BFF-backed contact form,
responsive navigation and existing workshop photos/product screenshots.

Build from the lockfile with `npm ci` then `npm run build`. Vite variables are public
build-time values: do not put credentials in them. Changing API or staff URLs requires
a rebuild. Set `VITE_APP_LOGIN_URL` to the actual staff URL, or configure `/app` to redirect
to it. Hosting the existing staff build under `/app` requires its own base-path setup;
copying it into an app folder alone is insufficient.

Deploy `dist/` and adapt `deploy/nginx.conf.sample`. The sample supplies SPA deep-link
fallback, hashed asset caching and the `/api/` proxy. It is an HTTP origin example;
configure public HTTPS and certificate renewal before release. Its domain and staff
redirect are placeholders that must be replaced. Run `nginx -t` before reload.

Acceptance before public release:

- Refresh `/contact?type=workshop`; the form should select the workshop identity.
- Submit a disposable enquiry and verify it appears in the staff inbox.
- Verify `/app` reaches the real staff login and no placeholder domain remains.
- Check navigation, images and the form at desktop and 390px mobile widths.
- Confirm public HTTPS, API connectivity and correct operator contact details.

The website delivery archive contains source, dependency lockfile, build output,
this README, environment examples and the deployment sample. Unused image backups,
duplicate photo variants and screenshot source HTML are excluded. It does not contain backend services, secrets or an assertion
that production deployment has passed. Backend integration acceptance is tracked in
`docs/system_acceptance_2026-10-12.md` at the repository root.

import http from '../http'

export function wechatLogin(code) {
  return http.post('/mp/customer/auth/wechat-login', { code, store_id: 'default' })
}

export function bindCustomer(payload) {
  return http.post('/mp/customer/auth/bind', payload)
}

export function refreshToken(token) {
  return http.post('/mp/customer/auth/refresh', { refresh_token: token })
}

export function logoutCustomer() {
  return http.post('/mp/customer/auth/logout')
}

export function fetchMe() {
  return http.get('/mp/customer/me')
}

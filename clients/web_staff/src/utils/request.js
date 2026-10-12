import axios from 'axios'
import { ElMessage } from 'element-plus'
import { v4 as uuidv4 } from 'uuid'
import { clearAuthToken, getAuthToken } from './auth'

const service = axios.create({
  baseURL: '/api',
  timeout: 300000,
  headers: {
    Accept: 'application/json; charset=utf-8',
    'Content-Type': 'application/json; charset=utf-8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
  },
})

const normalizeErrorMessage = (error) => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail.trim()
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object') {
          const field = Array.isArray(item.loc) ? item.loc.join('.') : ''
          const msg = item.msg || JSON.stringify(item)
          return field ? `${field}: ${msg}` : msg
        }
        return String(item)
      })
      .join('; ')
  }
  if (detail && typeof detail === 'object') {
    return detail.message || detail.msg || JSON.stringify(detail)
  }
  return error?.response
    ? '请求失败，请稍后重试'
    : '网络异常，请检查后端服务是否启动'
}

const shouldRetryTransient = (error) => {
  const cfg = error?.config || {}
  const method = String(cfg.method || 'get').toLowerCase()
  if (method !== 'get') return false
  if (cfg._retryTransient) return false
  const status = error?.response?.status
  if (!status) return true
  return status === 408 || status === 429 || status >= 500
}

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

service.interceptors.request.use(
  (config) => {
    const token = getAuthToken()
    if (token) config.headers.Authorization = `Bearer ${token}`

    const storeId = localStorage.getItem('drmoto_store_id') || 'default'
    if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    config.headers['X-Store-Id'] = storeId

    const method = (config.method || 'get').toLowerCase()
    if (['post', 'put', 'delete', 'patch'].includes(method)) {
      config.headers['Idempotency-Key'] = uuidv4()
    }

    return config
  },
  (error) => Promise.reject(error),
)

service.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalConfig = error?.config || {}
    const status = error?.response?.status
    const isAuthEndpoint = typeof originalConfig.url === 'string' && originalConfig.url.includes('/auth/token')

    if (status === 401 && !originalConfig._retryAuth && !isAuthEndpoint) {
      originalConfig._retryAuth = true
      clearAuthToken()
      if (typeof window !== 'undefined' && window.location && window.location.pathname !== '/login') {
        const current = `${window.location.pathname}${window.location.search || ''}`
        window.location.assign(`/login?redirect=${encodeURIComponent(current)}`)
      }
    }

    if (shouldRetryTransient(error)) {
      originalConfig._retryTransient = true
      await delay(350)
      return service(originalConfig)
    }

    ElMessage.error(normalizeErrorMessage(error))
    return Promise.reject(error)
  },
)

export default service

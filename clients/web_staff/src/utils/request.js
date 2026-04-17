import axios from 'axios'
import { ElMessage } from 'element-plus'
import { v4 as uuidv4 } from 'uuid'

const service = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    Accept: 'application/json; charset=utf-8',
    'Content-Type': 'application/json; charset=utf-8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
  }
})

let loginPromise = null

const loginWithStoredCredentials = async () => {
  if (!loginPromise) {
    const username = localStorage.getItem('drmoto_staff_username') || 'admin'
    const password = localStorage.getItem('drmoto_staff_password') || 'change_me_now'
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    loginPromise = axios.post('/api/auth/token', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    }).then((resp) => {
      const token = resp?.data?.access_token
      if (token) localStorage.setItem('drmoto_staff_token', token)
      return token || ''
    }).finally(() => {
      loginPromise = null
    })
  }
  return loginPromise
}

const ensureToken = async () => {
  const existing = localStorage.getItem('drmoto_staff_token')
  if (existing) return existing
  return loginWithStoredCredentials()
}

const normalizeErrorMessage = (error) => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail.trim()
  if (Array.isArray(detail) && detail.length) {
    return detail.map((item) => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object') {
        const field = Array.isArray(item.loc) ? item.loc.join('.') : ''
        const msg = item.msg || JSON.stringify(item)
        return field ? `${field}: ${msg}` : msg
      }
      return String(item)
    }).join('; ')
  }
  if (detail && typeof detail === 'object') {
    return detail.message || detail.msg || JSON.stringify(detail)
  }
  return error?.response ? '\u8BF7\u6C42\u5931\u8D25\uFF0C\u8BF7\u7A0D\u540E\u91CD\u8BD5' : '\u7F51\u7EDC\u5F02\u5E38\uFF0C\u8BF7\u68C0\u67E5\u540E\u7AEF\u670D\u52A1\u662F\u5426\u542F\u52A8'
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
  async (config) => {
    try {
      const token = await ensureToken()
      if (token) config.headers.Authorization = `Bearer ${token}`
    } catch {
      localStorage.removeItem('drmoto_staff_token')
    }
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
  (error) => Promise.reject(error)
)

service.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalConfig = error?.config || {}
    const status = error?.response?.status
    const isAuthEndpoint = typeof originalConfig.url === 'string' && originalConfig.url.includes('/auth/token')
    if (status === 401 && !originalConfig._retryAuth && !isAuthEndpoint) {
      originalConfig._retryAuth = true
      try {
        localStorage.removeItem('drmoto_staff_token')
        const nextToken = await loginWithStoredCredentials()
        if (nextToken) {
          originalConfig.headers = originalConfig.headers || {}
          originalConfig.headers.Authorization = `Bearer ${nextToken}`
        }
        return await service(originalConfig)
      } catch {
        localStorage.removeItem('drmoto_staff_token')
      }
    }
    if (shouldRetryTransient(error)) {
      originalConfig._retryTransient = true
      await delay(350)
      return service(originalConfig)
    }
    ElMessage.error(normalizeErrorMessage(error))
    return Promise.reject(error)
  }
)

export default service

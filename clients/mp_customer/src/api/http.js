import axios from 'axios'
import { showToast } from 'vant'
import { v4 as uuidv4 } from 'uuid'
import { useAuthStore } from '../stores/auth'

const http = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

function normalizeErrorMessage(raw) {
  const msg = String(raw || '').trim()
  if (!msg) return '网络异常，请稍后重试'

  const lower = msg.toLowerCase()
  if (lower.includes('network error')) return '网络异常，请检查网络连接'
  if (lower.includes('timeout')) return '请求超时，请稍后重试'
  if (lower.includes('could not validate customer token')) return '登录状态已失效，请重新登录'
  if (lower.includes('could not validate credentials')) return '登录状态已失效，请重新登录'
  if (lower.includes('unauthorized')) return '无访问权限，请重新登录'

  const hasChinese = /[\u4e00-\u9fa5]/.test(msg)
  const hasEnglish = /[A-Za-z]/.test(msg)
  if (!hasChinese && hasEnglish) return '请求失败，请稍后重试'

  return msg
}

http.interceptors.request.use(
  (config) => {
    const auth = useAuthStore()
    auth.restoreSession()

    config.headers['X-Trace-Id'] = uuidv4()
    if (auth.accessToken) {
      config.headers.Authorization = `Bearer ${auth.accessToken}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error?.response?.status
    const rawMessage = error?.response?.data?.error?.message || error?.response?.data?.detail || ''
    const message = normalizeErrorMessage(rawMessage)

    if (status === 401) {
      const auth = useAuthStore()
      auth.clearSession()
    }

    showToast(message)
    return Promise.reject(error)
  }
)

export default http

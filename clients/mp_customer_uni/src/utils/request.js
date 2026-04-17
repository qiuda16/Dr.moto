import { API_BASE, TCB_BASE_PATH, TCB_ENV, TCB_SERVICE } from '../config/env'
import { clearSession, getAccessToken, getRefreshToken, setAccessToken } from './session'
import { recordErrorLog } from './monitor'

const unauthorizedListeners = new Set()
let lastUnauthorizedEmitAt = 0
let cloudContainerBasePathMode = 'unknown'

const inflight = new Map()
const cacheStore = new Map()
let refreshPromise = null

function generateTraceId() {
  const rnd = Math.random().toString(36).slice(2, 10)
  return `mp_${Date.now().toString(36)}_${rnd}`
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function createRequestError({ message, code, statusCode, url, method, raw }) {
  const err = new Error(String(message || '请求失败'))
  err.name = 'RequestError'
  err.isRequestError = true
  err.code = code || 'REQUEST_FAILED'
  err.statusCode = statusCode
  err.url = url
  err.method = method
  err.raw = raw
  return err
}

function emitUnauthorized(payload) {
  const now = Date.now()
  if (now - lastUnauthorizedEmitAt < 1500) {
    return
  }
  lastUnauthorizedEmitAt = now
  for (const fn of unauthorizedListeners) {
    try {
      fn(payload)
    } catch (_err) {
    }
  }
}

export function onUnauthorized(handler) {
  if (typeof handler !== 'function') {
    return () => {}
  }
  unauthorizedListeners.add(handler)
  return () => unauthorizedListeners.delete(handler)
}

function normalizeMessage(message) {
  const text = String(message || '').trim().toLowerCase()
  if (!text) return '网络异常，请稍后重试'
  if (text.includes('timeout')) return '请求超时，请稍后重试'
  if (text.includes('network')) return '网络异常，请检查网络'
  if (text.includes('unauthorized')) return '登录状态已失效，请重新登录'
  if (text.includes('could not validate')) return '登录状态已失效，请重新登录'
  return /[\u4e00-\u9fa5]/.test(message || '') ? String(message) : '请求失败，请稍后重试'
}

async function requestByCloudContainer({ url, method, data, header }) {
  if (typeof wx === 'undefined' || !wx.cloud || !wx.cloud.callContainer) {
    throw new Error('当前环境不支持云托管调用')
  }

  const callOnce = async (pathValue) =>
    wx.cloud.callContainer({
      config: {
        env: TCB_ENV,
      },
      path: pathValue,
      header: {
        ...header,
        'X-WX-SERVICE': TCB_SERVICE,
      },
      method,
      data,
    })

  let response
  const shouldTryBasePath = Boolean(TCB_BASE_PATH)
  if (!shouldTryBasePath) {
    cloudContainerBasePathMode = 'no_base'
    response = await callOnce(url)
  } else if (cloudContainerBasePathMode === 'with_base') {
    response = await callOnce(`${TCB_BASE_PATH}${url}`)
  } else if (cloudContainerBasePathMode === 'no_base') {
    response = await callOnce(url)
  } else {
    const firstPath = `${TCB_BASE_PATH}${url}`
    response = await callOnce(firstPath)
    if (response?.statusCode === 404) {
      const fallback = await callOnce(url)
      response = fallback
      if (fallback?.statusCode && fallback.statusCode !== 404) {
        cloudContainerBasePathMode = 'no_base'
      }
    } else {
      cloudContainerBasePathMode = 'with_base'
    }
  }

  return {
    statusCode: response?.statusCode || 200,
    data: response?.data,
  }
}

async function requestByHttp({ url, method, data, header, timeoutMs }) {
  const [error, response] = await uni.request({
    url: `${API_BASE}${url}`,
    method,
    data,
    header,
    timeout: timeoutMs,
  })

  if (error) {
    throw error
  }

  return response
}

async function refreshAccessToken() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    return ''
  }

  const url = '/mp/customer/auth/refresh'
  const method = 'POST'
  const header = {
    'Content-Type': 'application/json',
    'X-Trace-Id': generateTraceId(),
  }
  const data = { refresh_token: refreshToken }

  let response
  // #ifdef MP-WEIXIN
  response = await requestByCloudContainer({ url, method, data, header })
  // #endif
  // #ifndef MP-WEIXIN
  response = await requestByHttp({ url, method, data, header, timeoutMs: 12000 })
  // #endif

  const statusCode = response?.statusCode || 0
  const payload = response?.data || {}
  if (statusCode >= 200 && statusCode < 300 && payload?.access_token) {
    setAccessToken(payload.access_token)
    return payload.access_token
  }
  return ''
}

async function refreshAccessTokenSingleFlight() {
  if (refreshPromise) {
    return refreshPromise
  }
  refreshPromise = (async () => {
    try {
      return await refreshAccessToken()
    } catch (_err) {
      return ''
    } finally {
      refreshPromise = null
    }
  })()
  return refreshPromise
}

function buildCacheKey({ url, method, data, auth }) {
  let dataKey = ''
  try {
    dataKey = data ? JSON.stringify(data) : ''
  } catch (_err) {
    dataKey = String(data)
  }
  return `${String(method || 'GET').toUpperCase()}|${String(url)}|${auth ? 'auth' : 'anon'}|${dataKey}`
}

function shouldRetry(err) {
  if (!err || !err.isRequestError) return false
  if (err.code === 'NETWORK_ERROR') return true
  if (err.code === 'HTTP_ERROR' && Number(err.statusCode) >= 500) return true
  if (Number(err.statusCode) === 429) return true
  return false
}

async function executeRequest({ url, upperMethod, data, header, timeoutMs }) {
  let response
  // #ifdef MP-WEIXIN
  response = await requestByCloudContainer({ url, method: upperMethod, data, header })
  // #endif

  // #ifndef MP-WEIXIN
  response = await requestByHttp({ url, method: upperMethod, data, header, timeoutMs })
  // #endif

  const statusCode = response.statusCode
  const payload = response.data || {}

  if (statusCode >= 200 && statusCode < 300) {
    return payload
  }

  if (statusCode === 401) {
    const raw = payload?.error?.message || payload?.detail || payload?.message
    throw createRequestError({
      message: normalizeMessage(raw || '登录状态已失效，请重新登录'),
      code: 'UNAUTHORIZED',
      statusCode,
      url,
      method: upperMethod,
      raw: payload,
    })
  }

  const raw = payload?.error?.message || payload?.detail || payload?.message
  throw createRequestError({
    message: normalizeMessage(raw),
    code: statusCode === 403 ? 'FORBIDDEN' : 'HTTP_ERROR',
    statusCode,
    url,
    method: upperMethod,
    raw: payload,
  })
}

export async function request({
  url,
  method = 'GET',
  data,
  auth = true,
  cache,
  dedupe,
  timeoutMs = 10000,
  retry = 0,
  retryDelayMs = 300,
}) {
  const header = {
    'Content-Type': 'application/json',
    'X-Trace-Id': generateTraceId(),
  }

  if (auth) {
    const token = getAccessToken()
    if (token) {
      header.Authorization = `Bearer ${token}`
    }
  }

  let ownsInflight = false

  try {
    const upperMethod = String(method || 'GET').toUpperCase()
    const enableCache = Boolean(cache && upperMethod === 'GET' && cache.ttlMs && cache.ttlMs > 0)
    const enableDedupe = Boolean(dedupe || enableCache)
    const cacheKey = buildCacheKey({ url, method: upperMethod, data, auth })

    if (enableCache) {
      const hit = cacheStore.get(cacheKey)
      if (hit && hit.expiresAt > Date.now()) {
        return hit.value
      }
      if (hit) {
        cacheStore.delete(cacheKey)
      }
    }

    if (enableDedupe && inflight.has(cacheKey)) {
      return await inflight.get(cacheKey)
    }

    const run = (async () => {
      let attempt = 0
      const maxAttempt = Math.max(0, Number(retry || 0))
      let refreshed = false
      while (true) {
        try {
          return await executeRequest({ url, upperMethod, data, header, timeoutMs })
        } catch (error) {
          if (error?.code === 'UNAUTHORIZED' && auth && !refreshed) {
            refreshed = true
            const newToken = await refreshAccessTokenSingleFlight()
            if (newToken) {
              header.Authorization = `Bearer ${newToken}`
              continue
            }
            clearSession()
            emitUnauthorized({ statusCode: 401, url, method: upperMethod })
            throw error
          }
          if (error && !error.isRequestError) {
            throw createRequestError({
              message: normalizeMessage(error?.message),
              code: 'NETWORK_ERROR',
              statusCode: 0,
              url,
              method: upperMethod,
              raw: error,
            })
          }
          if (attempt >= maxAttempt || !shouldRetry(error)) {
            recordErrorLog({
              message: error?.message,
              code: error?.code,
              statusCode: error?.statusCode,
              url,
              method: upperMethod,
            })
            throw error
          }
          attempt += 1
          await sleep(retryDelayMs * attempt)
        }
      }
    })()

    if (enableDedupe) {
      inflight.set(cacheKey, run)
      ownsInflight = true
    }

    const result = await run
    if (enableCache) {
      cacheStore.set(cacheKey, { value: result, expiresAt: Date.now() + cache.ttlMs })
    }
    return result
  } finally {
    const upperMethod = String(method || 'GET').toUpperCase()
    const enableCache = Boolean(cache && upperMethod === 'GET' && cache.ttlMs && cache.ttlMs > 0)
    const enableDedupe = Boolean(dedupe || enableCache)
    if (enableDedupe) {
      const cacheKey = buildCacheKey({ url, method: upperMethod, data, auth })
      if (ownsInflight) {
        inflight.delete(cacheKey)
      }
    }
  }
}

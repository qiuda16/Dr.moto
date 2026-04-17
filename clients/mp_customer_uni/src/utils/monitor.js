const ERROR_LOG_KEY = 'drmoto_error_logs'
const MAX_LOG_COUNT = 40

function nowIso() {
  try {
    return new Date().toISOString()
  } catch (_err) {
    return ''
  }
}

export function readErrorLogs() {
  try {
    const rows = uni.getStorageSync(ERROR_LOG_KEY)
    return Array.isArray(rows) ? rows : []
  } catch (_err) {
    return []
  }
}

export function recordErrorLog(entry) {
  try {
    const rows = readErrorLogs()
    const next = [
      {
        time: nowIso(),
        message: String(entry?.message || 'unknown'),
        code: entry?.code || '',
        statusCode: entry?.statusCode || 0,
        url: entry?.url || '',
        method: entry?.method || '',
      },
      ...rows,
    ].slice(0, MAX_LOG_COUNT)
    uni.setStorageSync(ERROR_LOG_KEY, next)
  } catch (_err) {
  }
}

export function orderStatusText(status) {
  const map = {
    draft: '待确认',
    confirmed: '已确认',
    diagnosing: '检测中',
    quoted: '已报价',
    in_progress: '施工中',
    ready: '待交付',
    done: '已完成',
    cancel: '已取消',
  }
  return map[status] || (status ? '处理中' : '暂无')
}

export function recommendationLevelText(level) {
  if (level === 'must') return '必须做'
  if (level === 'suggest') return '建议做'
  return '可延后'
}

export function recommendationLevelClass(level) {
  if (level === 'must') return 'is-must'
  if (level === 'suggest') return 'is-suggest'
  return 'is-optional'
}

export function formatDate(value) {
  if (!value) return '--'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return String(value)
  return dt.toLocaleDateString('zh-CN')
}

export function formatDateTime(value) {
  if (!value) return '--'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return String(value)
  return dt.toLocaleString('zh-CN')
}

export function formatAmount(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '--'
  return `¥${num.toFixed(0)}`
}

export function valueOrDash(value, suffix = '') {
  if (value === null || value === undefined || value === '') return '--'
  return `${value}${suffix}`
}

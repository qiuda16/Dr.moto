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
  return map[status] || '处理中'
}

export function levelText(level) {
  if (level === 'must') return '必须做'
  if (level === 'suggest') return '建议做'
  return '可延后'
}

export function fmtDate(value) {
  if (!value) return '--'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return String(value)
  const y = dt.getFullYear()
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const d = String(dt.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export function fmtDateTime(value) {
  if (!value) return '--'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return String(value)
  const hh = String(dt.getHours()).padStart(2, '0')
  const mm = String(dt.getMinutes()).padStart(2, '0')
  return `${fmtDate(dt)} ${hh}:${mm}`
}

export function fmtAmount(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '--'
  return `¥${n.toFixed(0)}`
}

function pad(value) {
  return String(value).padStart(2, '0')
}

export function formatDateTime(value) {
  if (!value) {
    return '-'
  }
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '-'
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function formatMoney(value) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const num = Number(value)
  if (Number.isNaN(num)) {
    return String(value)
  }
  return `￥${num.toFixed(2)}`
}

export function healthLabel(state) {
  const map = {
    normal: '正常',
    notice: '关注',
    warning: '建议处理',
    critical: '紧急',
    unknown: '未知',
  }
  return map[String(state || '').toLowerCase()] || '未知'
}

export function healthClass(state) {
  const map = {
    normal: 'chip chip--success',
    notice: 'chip chip--warning',
    warning: 'chip chip--danger',
    critical: 'chip chip--danger',
    unknown: 'chip',
  }
  return map[String(state || '').toLowerCase()] || 'chip'
}

export function orderStateLabel(state) {
  const map = {
    draft: '草稿',
    confirmed: '已确认',
    in_progress: '施工中',
    done: '已完成',
    cancel: '已取消',
  }
  return map[String(state || '').toLowerCase()] || state || '-'
}

export function productTypeLabel(value) {
  const map = {
    part: '配件',
    service: '服务',
    package: '套餐',
    maintenance: '保养',
    repair: '维修',
    inspection: '检测',
  }
  return map[String(value || '').toLowerCase()] || '商品'
}

export function inspectionStatusLabel(value) {
  const map = {
    normal: '正常',
    notice: '关注',
    warning: '建议处理',
    critical: '紧急',
    unknown: '未采集',
  }
  return map[String(value || '').toLowerCase()] || '未采集'
}

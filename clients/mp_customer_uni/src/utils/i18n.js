const SERVICE_KIND_LABELS = {
  maintenance: '保养',
  repair: '维修',
  inspection: '检测',
  package: '套餐',
  service: '服务',
  part: '配件',
}

const SERVICE_KIND_ALIASES = {
  maintenance: 'maintenance',
  保养: 'maintenance',
  养护: 'maintenance',
  repair: 'repair',
  维修: 'repair',
  inspection: 'inspection',
  检测: 'inspection',
  检查: 'inspection',
  package: 'package',
  套餐: 'package',
  service: 'service',
  服务: 'service',
  part: 'part',
  配件: 'part',
}

export function normalizeServiceKind(value) {
  const raw = String(value || '').trim()
  if (!raw) {
    return ''
  }
  return SERVICE_KIND_ALIASES[raw.toLowerCase()] || SERVICE_KIND_ALIASES[raw] || raw
}

export function serviceKindLabel(value) {
  const normalized = normalizeServiceKind(value)
  return SERVICE_KIND_LABELS[normalized] || normalized || '-'
}

export function normalizeErrorMessage(message, fallback = '请求失败，请稍后再试') {
  const raw = String(message || '').trim()
  if (!raw) {
    return fallback
  }
  if (raw === 'API base URL not configured for this build') {
    return '当前版本还没有配置服务地址'
  }
  const match = raw.match(/^request failed: (\d+)$/i)
  if (match) {
    return `请求失败，HTTP ${match[1]}`
  }
  if (['Network Error', 'timeout', 'request:fail'].includes(raw)) {
    return '网络连接失败，请稍后重试'
  }
  return raw
}

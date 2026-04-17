export const DEFAULT_APP_SETTINGS = {
  store_name: '机车博士',
  brand_name: 'DrMoto',
  sidebar_badge_text: '门店管理',
  primary_color: '#409EFF',
  default_labor_price: 80,
  default_delivery_note: '已向客户说明施工内容，建议按期复检。',
  common_complaint_phrases: [],
}

export function createAppSettingsState(overrides = {}) {
  return {
    ...DEFAULT_APP_SETTINGS,
    ...overrides,
  }
}

export function applyAppSettings(target, data = {}) {
  Object.assign(target, {
    store_name: data?.store_name || DEFAULT_APP_SETTINGS.store_name,
    brand_name: data?.brand_name || DEFAULT_APP_SETTINGS.brand_name,
    sidebar_badge_text: data?.sidebar_badge_text || DEFAULT_APP_SETTINGS.sidebar_badge_text,
    primary_color: data?.primary_color || DEFAULT_APP_SETTINGS.primary_color,
    default_labor_price: Number(data?.default_labor_price ?? DEFAULT_APP_SETTINGS.default_labor_price),
    default_delivery_note: String(data?.default_delivery_note || DEFAULT_APP_SETTINGS.default_delivery_note),
    common_complaint_phrases: Array.isArray(data?.common_complaint_phrases)
      ? data.common_complaint_phrases
      : [...DEFAULT_APP_SETTINGS.common_complaint_phrases],
  })
  return target
}

export function dispatchAppSettingsChanged() {
  window.dispatchEvent(new Event('drmoto-store-changed'))
}

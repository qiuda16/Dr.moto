export const DEFAULT_APP_SETTINGS = {
  store_name: '机车博士',
  brand_name: 'DrMoto',
  sidebar_badge_text: '门店管理',
  primary_color: '#409EFF',
  default_labor_price: 80,
  default_delivery_note: '已向客户说明施工内容，建议按期复检。',
  document_header_note: '摩托车售后服务专业单据',
  customer_document_footer_note: '请客户核对维修项目、金额与交车说明后签字确认。',
  internal_document_footer_note: '用于门店内部留档、责任追溯与施工复核。',
  default_service_advice: '建议客户按保养周期复检，并关注油液、制动与轮胎状态。',
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
    document_header_note: String(data?.document_header_note || DEFAULT_APP_SETTINGS.document_header_note),
    customer_document_footer_note: String(
      data?.customer_document_footer_note || DEFAULT_APP_SETTINGS.customer_document_footer_note
    ),
    internal_document_footer_note: String(
      data?.internal_document_footer_note || DEFAULT_APP_SETTINGS.internal_document_footer_note
    ),
    default_service_advice: String(data?.default_service_advice || DEFAULT_APP_SETTINGS.default_service_advice),
    common_complaint_phrases: Array.isArray(data?.common_complaint_phrases)
      ? data.common_complaint_phrases
      : [...DEFAULT_APP_SETTINGS.common_complaint_phrases],
  })
  return target
}

export function dispatchAppSettingsChanged() {
  window.dispatchEvent(new Event('drmoto-store-changed'))
}

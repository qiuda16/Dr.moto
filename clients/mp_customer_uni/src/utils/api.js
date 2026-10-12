import { request } from './request'
import { ALLOW_DEMO_FALLBACK } from '../config/env'
import {
  clearBindTicket,
  clearSession,
  getAccessToken,
  getActiveVehicleId,
  getBindTicket,
  getProfile,
  saveBindTicket,
  setActiveVehicleId,
  setSession,
} from './session'

function toQueryString(params) {
  const query = Object.entries(params || {})
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&')
  return query ? `?${query}` : ''
}

function normalizeProfile(payload) {
  if (!payload) {
    return null
  }
  return {
    partner_id: payload.partner_id || '',
    customer_name: payload.customer_name || payload.name || '',
    phone_masked: payload.phone_masked || payload.phone || '',
    store_id: payload.store_id || 'default',
  }
}

async function getLoginCode() {
  // #ifdef MP-WEIXIN
  const result = await uni.login({ provider: 'weixin' })
  if (!result?.code) {
    throw new Error('微信登录失败')
  }
  return result.code
  // #endif

  // #ifndef MP-WEIXIN
  if (ALLOW_DEMO_FALLBACK) return 'dev-login-code'
  throw new Error('请在微信小程序中登录')
  // #endif
}

export const api = {
  async ensureCustomerSession() {
    const cachedProfile = getProfile()
    if (getAccessToken()) {
      try {
        const profile = await this.getMe()
        return { bound: true, profile }
      } catch (error) {
        if (Number(error?.statusCode) === 401) {
          clearSession()
        } else {
          return { bound: true, profile: cachedProfile }
        }
      }
    }

    const code = await getLoginCode()
    const payload = await request({
      url: '/mp/customer/auth/wechat-login',
      method: 'POST',
      data: { code, store_id: 'default' },
      auth: false,
      timeoutMs: 12000,
    })

    if (!payload?.bound) {
      saveBindTicket(payload?.bind_ticket || '')
      return {
        bound: false,
        bindTicket: payload?.bind_ticket || '',
      }
    }

    const profile = normalizeProfile(payload) || cachedProfile
    clearBindTicket()
    setSession({
      accessToken: payload?.access_token || '',
      refreshToken: payload?.refresh_token || '',
      profile,
    })
    return {
      bound: true,
      profile,
    }
  },

  async bindCustomer(payload) {
    const response = await request({
      url: '/mp/customer/auth/bind',
      method: 'POST',
      data: payload,
      auth: false,
      timeoutMs: 12000,
    })
    setSession({
      accessToken: response?.access_token || '',
      refreshToken: response?.refresh_token || '',
      profile: normalizeProfile(response),
    })
    clearBindTicket()
    return response
  },

  logoutCustomer() {
    return request({
      url: '/mp/customer/auth/logout',
      method: 'POST',
      retry: 0,
    })
  },

  getMe() {
    return request({
      url: '/mp/customer/me',
      cache: { ttlMs: 10000 },
      retry: 1,
    })
  },

  getVehicles() {
    return request({
      url: '/mp/customer/vehicles',
      cache: { ttlMs: 30000 },
      dedupe: true,
      retry: 1,
    })
  },

  createVehicle(payload) {
    return request({
      url: '/mp/customer/vehicles',
      method: 'POST',
      data: payload,
      retry: 1,
    })
  },

  deleteVehicle(vehicleId) {
    return request({
      url: `/mp/customer/vehicles/${vehicleId}`,
      method: 'DELETE',
      retry: 1,
    })
  },

  getHomeSummary(vehicleId) {
    return request({
      url: `/mp/customer/home${toQueryString({ vehicle_id: vehicleId })}`,
      cache: { ttlMs: 20000 },
      dedupe: true,
      retry: 1,
    })
  },

  getCockpit(vehicleId) {
    return request({
      url: `/mp/customer/cockpit${toQueryString({ vehicle_id: vehicleId })}`,
      cache: { ttlMs: 15000 },
      dedupe: true,
      retry: 1,
    })
  },

  getShopProducts(options = {}) {
    return request({
      url: `/mp/customer/shop/products${toQueryString(options)}`,
      cache: { ttlMs: 8000 },
      dedupe: true,
      retry: 1,
    })
  },

  getShopRecommendations(vehicleId) {
    return request({
      url: `/mp/customer/shop/recommendations${toQueryString({ vehicle_id: vehicleId })}`,
      cache: { ttlMs: 15000 },
      dedupe: true,
      retry: 1,
    })
  },

  getShopProductDetail(productId, options = {}) {
    return request({
      url: `/mp/customer/shop/products/${productId}${toQueryString(options)}`,
      retry: 1,
    })
  },

  getVehicleHealthRecords(vehicleId, limit = 30) {
    return request({
      url: `/mp/customer/vehicles/${vehicleId}/health-records${toQueryString({ limit })}`,
      retry: 1,
    })
  },

  createVehicleHealthRecord(vehicleId, payload) {
    return request({
      url: `/mp/customer/vehicles/${vehicleId}/health-records`,
      method: 'POST',
      data: payload,
      retry: 1,
    })
  },

  getVehicleMaintenanceOrders(vehicleId, page = 1, size = 20) {
    return request({
      url: `/mp/customer/vehicles/${vehicleId}/maintenance-orders${toQueryString({ page, size })}`,
      retry: 1,
    })
  },

  getVehicleRecommendedServices(vehicleId) {
    return request({
      url: `/mp/customer/vehicles/${vehicleId}/recommended-services`,
      retry: 1,
    })
  },

  getVehicleKnowledgeDocs(vehicleId) {
    return request({
      url: `/mp/customer/vehicles/${vehicleId}/knowledge-docs`,
      retry: 1,
    })
  },

  getSubscriptions() {
    return request({
      url: '/mp/customer/subscriptions',
      cache: { ttlMs: 15000 },
      dedupe: true,
      retry: 1,
    })
  },

  createAppointmentDraft(payload) {
    return request({
      url: '/mp/customer/appointments/draft',
      method: 'POST',
      data: payload,
      retry: 1,
    })
  },

  getAppointmentDraft(draftId) {
    return request({
      url: `/mp/customer/appointments/draft/${draftId}`,
      retry: 1,
    })
  },

  saveSelectedVehicleId(vehicleId) {
    setActiveVehicleId(vehicleId)
  },

  getSelectedVehicleId() {
    return getActiveVehicleId()
  },

  getBindTicket() {
    return getBindTicket()
  },
}

﻿﻿﻿import { request } from './request'

export const api = {
  wechatLogin(code) {
    return request({
      url: '/mp/customer/auth/wechat-login',
      method: 'POST',
      data: { code, store_id: 'default' },
      auth: false,
      timeoutMs: 12000,
      retry: 1,
    })
  },
  bindCustomer(payload) {
    return request({
      url: '/mp/customer/auth/bind',
      method: 'POST',
      data: payload,
      auth: false,
      timeoutMs: 12000,
    })
  },
  logout() {
    return request({
      url: '/mp/customer/auth/logout',
      method: 'POST',
      retry: 0,
    })
  },
  fetchVehicles() {
    return request({
      url: '/mp/customer/vehicles',
      cache: { ttlMs: 60000 },
      dedupe: true,
      retry: 1,
    })
  },
  fetchHome(vehicleId) {
    return request({
      url: `/mp/customer/home?vehicle_id=${vehicleId}`,
      cache: { ttlMs: 30000 },
      dedupe: true,
      retry: 1,
    })
  },
  fetchHealthRecords(vehicleId, limit = 30) {
    return request({
      url: `/mp/customer/vehicles/${vehicleId}/health-records?limit=${limit}`,
      retry: 1,
    })
  },
  fetchMaintenanceOrders(vehicleId, page = 1, size = 20) {
    return request({
      url: `/mp/customer/vehicles/${vehicleId}/maintenance-orders?page=${page}&size=${size}`,
      retry: 1,
    })
  },
  fetchRecommendations(vehicleId) {
    return request({
      url: `/mp/customer/vehicles/${vehicleId}/recommended-services`,
      retry: 1,
    })
  },
  fetchKnowledgeDocs(vehicleId) {
    return request({
      url: `/mp/customer/vehicles/${vehicleId}/knowledge-docs`,
      retry: 1,
    })
  },
}

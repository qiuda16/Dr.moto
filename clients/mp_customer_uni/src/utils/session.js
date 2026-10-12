const TOKEN_KEY = 'drmoto_access_token'
const REFRESH_TOKEN_KEY = 'drmoto_refresh_token'
const PROFILE_KEY = 'drmoto_customer_profile'
const VEHICLE_ID_KEY = 'drmoto_vehicle_id'
const BIND_TICKET_KEY = 'drmoto_customer_bind_ticket'

let lastLoginRedirectAt = 0

export function setSession({ accessToken, refreshToken, profile }) {
  uni.setStorageSync(TOKEN_KEY, accessToken || '')
  uni.setStorageSync(REFRESH_TOKEN_KEY, refreshToken || '')
  uni.setStorageSync(PROFILE_KEY, profile || null)
}

export function clearSession() {
  uni.removeStorageSync(TOKEN_KEY)
  uni.removeStorageSync(REFRESH_TOKEN_KEY)
  uni.removeStorageSync(PROFILE_KEY)
  uni.removeStorageSync(VEHICLE_ID_KEY)
}

export function getAccessToken() {
  return uni.getStorageSync(TOKEN_KEY) || ''
}

export function setAccessToken(token) {
  if (!token) {
    uni.removeStorageSync(TOKEN_KEY)
    return
  }
  uni.setStorageSync(TOKEN_KEY, token)
}

export function getRefreshToken() {
  return uni.getStorageSync(REFRESH_TOKEN_KEY) || ''
}

export function getProfile() {
  return uni.getStorageSync(PROFILE_KEY) || null
}

export function saveBindTicket(bindTicket) {
  if (!bindTicket) {
    return
  }
  uni.setStorageSync(BIND_TICKET_KEY, bindTicket)
}

export function getBindTicket() {
  return uni.getStorageSync(BIND_TICKET_KEY) || ''
}

export function clearBindTicket() {
  uni.removeStorageSync(BIND_TICKET_KEY)
}

export function setActiveVehicleId(id) {
  if (!id) {
    uni.removeStorageSync(VEHICLE_ID_KEY)
    return
  }
  uni.setStorageSync(VEHICLE_ID_KEY, String(id))
}

export function getActiveVehicleId() {
  return uni.getStorageSync(VEHICLE_ID_KEY) || ''
}

export function redirectToLoginOnce() {
  const now = Date.now()
  if (now - lastLoginRedirectAt < 1500) {
    return
  }
  lastLoginRedirectAt = now
  uni.redirectTo({ url: '/pages/bind/index' })
}

export function ensureLogin() {
  const token = getAccessToken()
  if (!token) {
    redirectToLoginOnce()
    return false
  }
  return true
}

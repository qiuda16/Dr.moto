const STAFF_TOKEN_KEY = 'drmoto_staff_token'
const STAFF_USERNAME_KEY = 'drmoto_staff_username'

export function getAuthToken() {
  return localStorage.getItem(STAFF_TOKEN_KEY) || ''
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem(STAFF_TOKEN_KEY, token)
  } else {
    localStorage.removeItem(STAFF_TOKEN_KEY)
  }
}

export function clearAuthToken() {
  localStorage.removeItem(STAFF_TOKEN_KEY)
}

export function getSavedStaffUsername() {
  return localStorage.getItem(STAFF_USERNAME_KEY) || 'admin'
}

export function setSavedStaffUsername(username) {
  const value = String(username || '').trim()
  if (value) {
    localStorage.setItem(STAFF_USERNAME_KEY, value)
  } else {
    localStorage.removeItem(STAFF_USERNAME_KEY)
  }
}

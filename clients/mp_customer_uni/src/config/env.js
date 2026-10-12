// Production builds must receive an HTTPS API base from the build environment.
// Same-origin is the safe fallback for local previews behind the landing proxy.
export const API_BASE = import.meta.env.VITE_API_BASE || '/api'
export const API_FALLBACK_BASE = import.meta.env.VITE_API_FALLBACK_BASE || ''
export const USE_CLOUD_CONTAINER = import.meta.env.VITE_USE_CLOUD_CONTAINER === 'true'
export const ALLOW_DEMO_FALLBACK = import.meta.env.VITE_ALLOW_DEMO_FALLBACK === 'true'

export const TCB_ENV = import.meta.env.VITE_TCB_ENV || 'prod-9gbcay06c7c9a82b'
export const TCB_SERVICE = import.meta.env.VITE_TCB_SERVICE || 'flask-i7ja'
export const TCB_BASE_PATH = import.meta.env.VITE_TCB_BASE_PATH || '/api'

export const LOGIN_DEFAULTS = {
  phone: '',
  plateNo: '',
}

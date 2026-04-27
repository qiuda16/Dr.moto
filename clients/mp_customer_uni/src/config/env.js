export const API_BASE = import.meta.env.VITE_API_BASE || 'https://drmoto.cloud'

export const TCB_ENV = import.meta.env.VITE_TCB_ENV || 'prod-9gbcay06c7c9a82b'
export const TCB_SERVICE = import.meta.env.VITE_TCB_SERVICE || 'flask-i7ja'
export const TCB_BASE_PATH = import.meta.env.VITE_TCB_BASE_PATH || '/api'

export const LOGIN_DEFAULTS = {
  phone: '13900001111',
  plateNo: 'TEST1234',
}

import { defineStore } from 'pinia'

const STORAGE_KEY = 'drmoto_customer_session'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: '',
    refreshToken: '',
    partnerId: null,
    customerName: '',
    phoneMasked: '',
    loaded: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.accessToken && state.partnerId),
  },
  actions: {
    restoreSession() {
      if (this.loaded) {
        return
      }
      this.loaded = true
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) {
        return
      }
      try {
        const parsed = JSON.parse(raw)
        this.accessToken = parsed.accessToken || ''
        this.refreshToken = parsed.refreshToken || ''
        this.partnerId = parsed.partnerId ?? null
        this.customerName = parsed.customerName || ''
        this.phoneMasked = parsed.phoneMasked || ''
      } catch (err) {
        localStorage.removeItem(STORAGE_KEY)
      }
    },
    setSession(payload) {
      this.accessToken = payload.accessToken || ''
      this.refreshToken = payload.refreshToken || ''
      this.partnerId = payload.partnerId ?? null
      this.customerName = payload.customerName || ''
      this.phoneMasked = payload.phoneMasked || ''
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          accessToken: this.accessToken,
          refreshToken: this.refreshToken,
          partnerId: this.partnerId,
          customerName: this.customerName,
          phoneMasked: this.phoneMasked,
        })
      )
    },
    clearSession() {
      this.accessToken = ''
      this.refreshToken = ''
      this.partnerId = null
      this.customerName = ''
      this.phoneMasked = ''
      localStorage.removeItem(STORAGE_KEY)
    },
  },
})

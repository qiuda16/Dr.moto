import { defineStore } from 'pinia'

const STORAGE_KEY = 'drmoto_active_vehicle_id'

export const useVehicleStore = defineStore('vehicle', {
  state: () => ({
    vehicles: [],
    activeVehicleId: null,
    loading: false,
  }),
  getters: {
    activeVehicle(state) {
      return state.vehicles.find((v) => v.id === state.activeVehicleId) || null
    },
  },
  actions: {
    setVehicles(items) {
      this.vehicles = Array.isArray(items) ? items : []
      const cached = Number(localStorage.getItem(STORAGE_KEY) || '')
      if (!this.activeVehicleId && Number.isFinite(cached) && this.vehicles.some((v) => v.id === cached)) {
        this.activeVehicleId = cached
      }
      if (!this.activeVehicleId && this.vehicles.length > 0) {
        this.activeVehicleId = this.vehicles[0].id
        localStorage.setItem(STORAGE_KEY, String(this.activeVehicleId))
      }
    },
    setActiveVehicle(vehicleId) {
      this.activeVehicleId = vehicleId
      if (vehicleId) {
        localStorage.setItem(STORAGE_KEY, String(vehicleId))
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }
    },
  },
})

import http from '../http'

export function fetchVehicles() {
  return http.get('/mp/customer/vehicles')
}

export function fetchHome(vehicleId) {
  return http.get('/mp/customer/home', { params: { vehicle_id: vehicleId } })
}

export function fetchHealthRecords(vehicleId, limit = 20) {
  return http.get(`/mp/customer/vehicles/${vehicleId}/health-records`, { params: { limit } })
}

export function fetchMaintenanceOrders(vehicleId, page = 1, size = 20) {
  return http.get(`/mp/customer/vehicles/${vehicleId}/maintenance-orders`, { params: { page, size } })
}

export function fetchRecommendations(vehicleId) {
  return http.get(`/mp/customer/vehicles/${vehicleId}/recommended-services`)
}

export function fetchKnowledgeDocs(vehicleId, category = '') {
  return http.get(`/mp/customer/vehicles/${vehicleId}/knowledge-docs`, { params: { category } })
}

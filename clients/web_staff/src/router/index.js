import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import OrderListView from '../views/OrderListView.vue'
import CustomersView from '../views/CustomersView.vue'
import InventoryView from '../views/InventoryView.vue'
import SettingsView from '../views/SettingsView.vue'
import LoginView from '../views/LoginView.vue'
import { getAuthToken } from '../utils/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
    { path: '/', name: 'dashboard', component: DashboardView },
    { path: '/orders', name: 'orders', component: OrderListView },
    { path: '/customers', name: 'customers', component: CustomersView },
    { path: '/inventory', name: 'inventory', component: InventoryView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})

router.beforeEach((to) => {
  const token = getAuthToken()
  if (to.meta?.public && token) {
    return { name: 'dashboard' }
  }
  if (to.meta?.public) return true
  if (!token) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }
  return true
})

export default router

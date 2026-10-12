import { createRouter, createWebHistory } from 'vue-router'
import { getAuthToken } from '../utils/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
    { path: '/', name: 'dashboard', component: () => import('../views/DashboardView.vue') },
    { path: '/orders', name: 'orders', component: () => import('../views/OrderListView.vue') },
    { path: '/customers', name: 'customers', component: () => import('../views/CustomersView.vue') },
    { path: '/inventory', name: 'inventory', component: () => import('../views/InventoryView.vue') },
    { path: '/shop', name: 'shop', component: () => import('../views/ShopView.vue') },
    { path: '/trial-inbox', name: 'trial-inbox', component: () => import('../views/TrialInboxView.vue') },
    { path: '/settings', name: 'settings', component: () => import('../views/SettingsView.vue') },
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

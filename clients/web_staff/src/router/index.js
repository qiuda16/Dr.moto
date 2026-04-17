import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import OrderListView from '../views/OrderListView.vue'
import CustomersView from '../views/CustomersView.vue'
import InventoryView from '../views/InventoryView.vue'
import SettingsView from '../views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: DashboardView },
    { path: '/orders', name: 'orders', component: OrderListView },
    { path: '/customers', name: 'customers', component: CustomersView },
    { path: '/inventory', name: 'inventory', component: InventoryView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})

export default router

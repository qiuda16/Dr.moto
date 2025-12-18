import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import OrderListView from '../views/OrderListView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: DashboardView },
    { path: '/orders', component: OrderListView },
  ]
})

export default router

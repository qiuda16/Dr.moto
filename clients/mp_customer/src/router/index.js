import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import OrdersView from '../views/OrdersView.vue'
import OrderDetailView from '../views/OrderDetailView.vue'
import ProfileView from '../views/ProfileView.vue'
import AiHelpView from '../views/AiHelpView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/orders', component: OrdersView },
    { path: '/orders/:id', component: OrderDetailView },
    { path: '/profile', component: ProfileView },
    { path: '/ai-help', component: AiHelpView }
  ]
})

export default router

import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import TaskBoardView from '../views/TaskBoardView.vue'
import WorkbenchView from '../views/WorkbenchView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    { path: '/', component: TaskBoardView },
    { path: '/workorder/:id', component: WorkbenchView }
  ]
})

// Guard
router.beforeEach((to, from, next) => {
  const staff = localStorage.getItem('drmoto_staff')
  if (!staff && to.path !== '/login') {
    next('/login')
  } else {
    next()
  }
})

export default router

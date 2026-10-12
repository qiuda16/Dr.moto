import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './styles.css'
import AboutPage from './pages/AboutPage.vue'
import BusinessPage from './pages/BusinessPage.vue'
import ContactPage from './pages/ContactPage.vue'
import HomePage from './pages/HomePage.vue'
import RidersPage from './pages/RidersPage.vue'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, top: 96 }
    return { top: 0 }
  },
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/riders', name: 'riders', component: RidersPage },
    { path: '/business', name: 'business', component: BusinessPage },
    { path: '/about', name: 'about', component: AboutPage },
    { path: '/contact', name: 'contact', component: ContactPage },
  ],
})

createApp(App).use(router).mount('#app')

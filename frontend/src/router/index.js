import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import DyslexiaPage from '../views/DyslexiaPage.vue'

const routes = [
  { path: '/', name: 'Home', component: HomePage },
  { path: '/dyslexia', name: 'Dyslexia', component: DyslexiaPage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router

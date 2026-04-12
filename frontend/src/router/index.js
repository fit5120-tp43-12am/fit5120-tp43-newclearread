import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import DyslexiaPage from '../views/DyslexiaPage.vue'
import ReadingPage from '../views/ReadingPage.vue'

const routes = [
  { path: '/',        name: 'Home',    component: HomePage },
  { path: '/dyslexia', name: 'Dyslexia', component: DyslexiaPage },
  { path: '/reading',  name: 'Reading',  component: ReadingPage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router

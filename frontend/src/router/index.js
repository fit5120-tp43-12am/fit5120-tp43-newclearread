import { createRouter, createWebHistory } from 'vue-router'
import HomePage        from '../views/HomePage.vue'
import DyslexiaPage   from '../views/DyslexiaPage.vue'
import ReadingPage     from '../views/ReadingPage.vue'
import FocusReaderPage from '../views/FocusReaderPage.vue'

const routes = [
  { path: '/',         name: 'Home',          component: HomePage },
  { path: '/dyslexia', name: 'Dyslexia',      component: DyslexiaPage },
  { path: '/reading',  name: 'Read Easier',   component: ReadingPage },
  { path: '/training', name: 'Focus Reader',  component: FocusReaderPage },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router

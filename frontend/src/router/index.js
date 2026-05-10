// ── Router (Vue Router 4) ─────────────────────────────────────────────────────
// Vue Router maps URL paths to page components.
// When the user navigates to a path (e.g. "/reading"), Vue Router renders
// the matching component inside the <RouterView /> in App.vue.
import { createRouter, createWebHistory } from 'vue-router'
import HomePage        from '../views/HomePage.vue'
import DyslexiaPage   from '../views/DyslexiaPage.vue'
import ReadingPage     from '../views/ReadingPage.vue'
import FocusReaderPage from '../views/FocusReaderPage.vue'
import DictionaryPage  from '../views/DictionaryPage.vue'

// Each route object maps one URL path to one page component.
const routes = [
  { path: '/',           name: 'Home',           component: HomePage },        // landing page
  { path: '/dyslexia',   name: 'Dyslexia',       component: DyslexiaPage },   // info + charts
  { path: '/reading',    name: 'Read Easier',    component: ReadingPage },    // AI simplify + TTS
  { path: '/training',   name: 'Focus Reader',   component: FocusReaderPage },// letter-training game
  { path: '/dictionary', name: 'Dictionary',     component: DictionaryPage }, // word lookup
]

const router = createRouter({
  // createWebHistory uses the HTML5 History API so URLs look like /reading
  // instead of /#/reading (which is the older hash-based approach).
  // import.meta.env.BASE_URL is set by Vite to the deployment sub-path (e.g. "/" in dev).
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  // Always scroll back to the top of the new page when navigating between routes.
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router

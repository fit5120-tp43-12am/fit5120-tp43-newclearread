// ── Entry point ──────────────────────────────────────────────────────────────
// This is the first file that runs when the app loads.
// createApp() initialises the Vue 3 application with App.vue as the root component.
// .use(router) registers Vue Router so <RouterLink> and <RouterView> work everywhere.
// .mount('#app') injects the whole app into the <div id="app"> in index.html.
import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router/index.js'

createApp(App).use(router).mount('#app')

<script setup>
import { onMounted } from 'vue'
import { initAccessibility } from './composables/useAccessibility.js'
import AccessibilityToolbar from './components/AccessibilityToolbar.vue'

onMounted(() => initAccessibility())
</script>

<template>
  <RouterView />
  <AccessibilityToolbar />
</template>

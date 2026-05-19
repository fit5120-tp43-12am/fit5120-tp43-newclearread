<script setup>
import { onMounted, onUnmounted } from 'vue'
import AccessibilityToolbar from './components/AccessibilityToolbar.vue'
import GlobalDictPopup from './components/GlobalDictPopup.vue'
import { useGlobalDict } from './composables/useGlobalDict'

const { handleWordDblClick, closeDictPopup } = useGlobalDict()

function handleKeydown(event) {
  if (event.key === 'Escape') closeDictPopup()
}

onMounted(() => {
  document.addEventListener('dblclick', handleWordDblClick)
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('dblclick', handleWordDblClick)
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <AccessibilityToolbar />
  <RouterView />
  <GlobalDictPopup />
</template>

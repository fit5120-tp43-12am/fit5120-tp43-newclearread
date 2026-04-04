<!-- <script setup>
import HelloWorld from './components/HelloWorld.vue'
</script>

<template>
  <HelloWorld />
</template> -->

<script setup>
import { ref, onMounted } from 'vue'

const message = ref('Loading...')

onMounted(async () => {
  const res = await fetch('http://127.0.0.1:8000/api/test')
  const data = await res.json()
  message.value = data.message
})
</script>

<template>
  <h1>{{ message }}</h1>
</template>
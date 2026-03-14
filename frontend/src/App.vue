<template>
  <div class="app" :class="{ 'dark-mode': isDarkMode }">
    <router-view />
  </div>
</template>

<script setup>
import { ref, onMounted, provide } from 'vue'

const isDarkMode = ref(false)
const fontSize = ref(16)
const lineHeight = ref(1.8)

const updateReadingSettings = () => {
  const settings = JSON.parse(localStorage.getItem('reading-settings') || '{}')
  isDarkMode.value = settings.isDarkMode || false
  fontSize.value = settings.fontSize || 16
  lineHeight.value = settings.lineHeight || 1.8
}

const setDarkMode = (value) => {
  isDarkMode.value = value
  const settings = JSON.parse(localStorage.getItem('reading-settings') || '{}')
  settings.isDarkMode = value
  localStorage.setItem('reading-settings', JSON.stringify(settings))
}

const setFontSize = (value) => {
  fontSize.value = Math.max(12, Math.min(28, value))
  const settings = JSON.parse(localStorage.getItem('reading-settings') || '{}')
  settings.fontSize = fontSize.value
  localStorage.setItem('reading-settings', JSON.stringify(settings))
}

const setLineHeight = (value) => {
  lineHeight.value = Math.max(1.2, Math.min(2.5, value))
  const settings = JSON.parse(localStorage.getItem('reading-settings') || '{}')
  settings.lineHeight = lineHeight.value
  localStorage.setItem('reading-settings', JSON.stringify(settings))
}

provide('isDarkMode', isDarkMode)
provide('fontSize', fontSize)
provide('lineHeight', lineHeight)
provide('setDarkMode', setDarkMode)
provide('setFontSize', setFontSize)
provide('setLineHeight', setLineHeight)

onMounted(() => {
  updateReadingSettings()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --bg-color: #f5f7fa;
  --sidebar-bg: #ffffff;
  --text-primary: #333333;
  --text-secondary: #666666;
  --border-color: #e0e0e0;
  --primary-color: #4a4cf7;
  --hover-bg: #f0f2ff;
  --card-bg: #ffffff;
  --shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.dark-mode {
  --bg-color: #1a1a2e;
  --sidebar-bg: #16213e;
  --text-primary: #e0e0e0;
  --text-secondary: #a0a0a0;
  --border-color: #2a2a4a;
  --primary-color: #6c7bff;
  --hover-bg: #1f2040;
  --card-bg: #16213e;
  --shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

body {
  font-family: 'Noto Serif SC', 'Source Han Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
  background-color: var(--bg-color);
  color: var(--text-primary);
  transition: background-color 0.3s, color 0.3s;
}

.app {
  min-height: 100vh;
}
</style>

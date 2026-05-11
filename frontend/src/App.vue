<template>
  <n-config-provider :theme="isDark ? darkTheme : null" :theme-overrides="themeOverrides">
    <n-message-provider>
      <router-view />
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { NConfigProvider, NMessageProvider, darkTheme } from 'naive-ui'
import { useDark } from '@vueuse/core'
import { watch } from 'vue'

const isDark = useDark()

// Sync dark mode with html class for Tailwind
watch(isDark, (newValue) => {
  if (newValue) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}, { immediate: true })

const themeOverrides = {
  common: {
    primaryColor: '#6366F1FF',
    primaryColorHover: '#818CF8FF',
    primaryColorPressed: '#4F46E5FF',
    primaryColorSuppl: '#8B5CF6FF',
    borderRadius: '16px',
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
  },
  Button: {
    borderRadiusMedium: '12px',
    fontWeightMedium: '600',
  },
  Card: {
    borderRadius: '20px',
  },
  DataTable: {
    borderRadius: '16px',
  },
}
</script>

<style scoped>
</style>

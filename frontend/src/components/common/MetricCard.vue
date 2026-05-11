<template>
  <div class="p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
    <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">{{ title }}</h3>
    <div class="mt-2 flex items-baseline gap-2">
      <span class="text-3xl font-bold text-gray-900 dark:text-white">{{ formattedValue }}</span>
      <span 
        v-if="trend !== null" 
        :class="['text-sm font-medium flex items-center', trend > 0 ? 'text-green-600' : 'text-red-600']"
      >
        <!-- Icon panah simpel (bisa diganti Heroicons) -->
        <span v-if="trend > 0">↑</span>
        <span v-else>↓</span>
        {{ Math.abs(trend) }}%
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  value: number
  trend: number | null // misal: 5 (naik 5%), -2 (turun 2%)
  prefix?: string
}>()

const formattedValue = computed(() => {
  return `${props.prefix || ''} ${props.value.toLocaleString('id-ID')}`
})
</script>
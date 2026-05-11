<template>
  <div class="flex items-center gap-2 bg-white dark:bg-gray-800 p-2 rounded-lg border dark:border-gray-700 shadow-sm">
    <select v-model="quickSelect" @change="applyQuickSelect" class="bg-transparent text-sm border-r dark:border-gray-700 pr-2 focus:outline-none dark:text-white">
      <option value="today">Hari Ini</option>
      <option value="this_month">Bulan Ini</option>
      <option value="ytd">YTD</option>
      <option value="custom">Custom Range</option>
    </select>

    <div class="flex items-center gap-2 px-2" v-if="quickSelect === 'custom' || true">
      <input 
        type="date" 
        v-model="filters.dateRange.start"
        class="text-sm bg-transparent focus:outline-none dark:text-white dark:[color-scheme:dark]"
      />
      <span class="text-gray-400">-</span>
      <input 
        type="date" 
        v-model="filters.dateRange.end"
        class="text-sm bg-transparent focus:outline-none dark:text-white dark:[color-scheme:dark]"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useFilterStore } from '@/stores/filterStores'

const filterStore = useFilterStore()
const { currentFilters: filters } = storeToRefs(filterStore)

const quickSelect = ref('this_month')

const applyQuickSelect = () => {
  const today = new Date()
  if (quickSelect.value === 'today') {
    filters.value.dateRange.start = today.toISOString().split('T')[0]
    filters.value.dateRange.end = today.toISOString().split('T')[0]
  } else if (quickSelect.value === 'this_month') {
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
    filters.value.dateRange.start = firstDay.toISOString().split('T')[0]
    filters.value.dateRange.end = today.toISOString().split('T')[0]
  }
  // Tambahkan logic YTD sesuai kebutuhan
}
</script>
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useFilterStore = defineStore('filter', () => {
  // State filter aktif
  const currentFilters = ref({
    dateRange: { start: '', end: '' },
    region: null,
    product: null
  })

  // State untuk menyimpan daftar preset favorit user
  const savedPresets = ref([
    { id: 1, name: 'Laporan Rutin Jatim', filters: { region: 'Jatim', dateRange: 'ThisMonth' } }
  ])

  function applyPreset(presetId: number) {
    const preset = savedPresets.value.find(p => p.id === presetId)
    if (preset) {
      currentFilters.value = { ...currentFilters.value, ...preset.filters }
    }
  }

  function saveAsPreset(name: string) {
    savedPresets.value.push({
      id: Date.now(),
      name,
      filters: { ...currentFilters.value }
    })
  }

  return { currentFilters, savedPresets, applyPreset, saveAsPreset }
})
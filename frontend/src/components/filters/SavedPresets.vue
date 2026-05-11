<template>
  <div class="relative">
    <div class="flex items-center gap-2">
      <select 
        @change="(e) => apply(Number((e.target as HTMLSelectElement).value))"
        class="border dark:border-gray-700 bg-white dark:bg-gray-800 dark:text-white text-sm rounded-lg p-2 focus:ring-2 focus:ring-blue-500"
      >
        <option value="" disabled selected>Pilih Preset Laporan...</option>
        <option v-for="preset in savedPresets" :key="preset.id" :value="preset.id">
          ⭐ {{ preset.name }}
        </option>
      </select>
      
      <button 
        @click="showSaveModal = true"
        class="p-2 text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg dark:bg-gray-800 dark:text-blue-400"
        title="Simpan Filter Saat Ini"
      >
        💾
      </button>
    </div>

    <!-- Simple Modal untuk Save Preset -->
    <div v-if="showSaveModal" class="absolute top-12 right-0 w-64 bg-white dark:bg-gray-800 p-4 rounded-lg shadow-xl border dark:border-gray-700 z-50">
      <h4 class="text-sm font-bold mb-2 dark:text-white">Simpan Preset Baru</h4>
      <input 
        v-model="newPresetName" 
        type="text" 
        placeholder="Nama Preset (Misal: Jatim Q1)"
        class="w-full border p-2 rounded text-sm mb-2 dark:bg-gray-900 dark:border-gray-700 dark:text-white"
      />
      <div class="flex gap-2 justify-end">
        <button @click="showSaveModal = false" class="text-xs px-3 py-1 text-gray-500">Batal</button>
        <button @click="save" class="text-xs px-3 py-1 bg-blue-600 text-white rounded">Simpan</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useFilterStore } from '@/stores/filterStores'

const filterStore = useFilterStore()
const { savedPresets } = storeToRefs(filterStore)

const showSaveModal = ref(false)
const newPresetName = ref('')

const apply = (id: number) => {
  filterStore.applyPreset(id)
}

const save = () => {
  if (newPresetName.value.trim() === '') return
  filterStore.saveAsPreset(newPresetName.value)
  newPresetName.value = ''
  showSaveModal.value = false
  alert('Preset berhasil disimpan!')
}
</script>
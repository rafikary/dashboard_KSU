<template>
  <div class="flex gap-2">
    <button @click="exportToCSV" class="px-3 py-1.5 text-sm bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-700 hover:bg-green-100 dark:hover:bg-green-900/50 rounded-md transition-colors flex items-center gap-1">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
      CSV
    </button>
    <button @click="exportToExcel" class="px-3 py-1.5 text-sm bg-green-600 dark:bg-green-700 text-white hover:bg-green-700 dark:hover:bg-green-600 rounded-md transition-colors flex items-center gap-1">
      Excel
    </button>
    <button @click="exportToPDF" class="px-3 py-1.5 text-sm bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-700 hover:bg-red-100 dark:hover:bg-red-900/50 rounded-md transition-colors flex items-center gap-1">
      PDF
    </button>
  </div>
</template>

<script setup lang="ts">
import ExcelJS from 'exceljs'
import { saveAs } from 'file-saver'

const props = defineProps<{
  data: any[] // Data dari tabel yang sedang aktif
  filename?: string
}>()

const defaultName = props.filename || 'Laporan_Export'

const exportToExcel = async () => {
  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet('Data')

  // Asumsi props.data adalah array of objects [{ id: 1, nama: 'A' }, ...]
  if (props.data && props.data.length > 0) {
    // Buat header otomatis dari keys object pertama
    worksheet.columns = Object.keys(props.data[0]).map(key => ({
      header: key.toUpperCase(),
      key: key,
      width: 20
    }))
    
    // Masukkan baris data
    worksheet.addRows(props.data)
  }

  // Generate file dan trigger download
  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  saveAs(blob, `${defaultName}.xlsx`)
}

const exportToCSV = () => {
  alert("export to csv")
}

const exportToPDF = () => {
  // Gunakan library seperti jspdf + jspdf-autotable
  alert('Logic PDF dijalankan (butuh jspdf)')
}
</script>
<template>
  <div class="space-y-6">
    <!-- Header with Actions -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold text-gray-800 dark:text-white">Data Customer</h2>
        <p class="text-gray-500 dark:text-gray-400 mt-1">Kelola dan monitor performa customer Anda</p>
      </div>
      <n-button type="primary" size="large" round class="shadow-lg">
        <template #icon>
          <n-icon :component="AddOutline" />
        </template>
        Tambah Customer
      </n-button>
    </div>

    <!-- Modern DataTable with Glass Effect -->
    <div class="glass-card rounded-3xl p-6 overflow-hidden">
      <!-- Table Header Actions -->
      <div class="flex items-center justify-between mb-6">
        <n-input
          v-model:value="searchQuery"
          placeholder="Cari customer..."
          class="w-80"
          round
        >
          <template #prefix>
            <n-icon :component="SearchOutline" />
          </template>
        </n-input>

        <div class="flex gap-3">
          <n-button circle quaternary>
            <template #icon>
              <n-icon :component="FilterOutline" />
            </template>
          </n-button>
          <n-button circle quaternary @click="exportToExcel">
            <template #icon>
              <n-icon :component="DownloadOutline" />
            </template>
          </n-button>
        </div>
      </div>

      <!-- Beautiful DataTable -->
      <n-data-table
        :columns="columns"
        :data="filteredCustomers"
        :pagination="pagination"
        :bordered="false"
        :row-class-name="rowClassName"
        striped
        class="modern-table"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { NDataTable, NButton, NInput, NIcon, NTag, NSpace } from 'naive-ui'
import {
  AddOutline,
  SearchOutline,
  FilterOutline,
  DownloadOutline,
  EyeOutline,
  CreateOutline,
  TrashOutline,
  CallOutline,
} from '@vicons/ionicons5'
import * as XLSX from 'xlsx'
import type { CustomerData } from '@/types'
import type { DataTableColumns } from 'naive-ui'

const searchQuery = ref('')

const customers = ref<CustomerData[]>([
  {
    custname: 'PT Maju Jaya',
    area: 'Jakarta',
    kota: 'Jakarta Pusat',
    total_omzet: 500000000,
    total_transactions: 45,
    avg_transaction: 11111111,
    last_transaction: '2026-05-05',
  },
  {
    custname: 'CV Berkah Sejahtera',
    area: 'Surabaya',
    kota: 'Surabaya',
    total_omzet: 350000000,
    total_transactions: 32,
    avg_transaction: 10937500,
    last_transaction: '2026-05-03',
  },
  {
    custname: 'Toko Sukses Makmur',
    area: 'Bandung',
    kota: 'Bandung',
    total_omzet: 280000000,
    total_transactions: 28,
    avg_transaction: 10000000,
    last_transaction: '2026-05-07',
  },
])

const filteredCustomers = computed(() => {
  if (!searchQuery.value) return customers.value
  
  const query = searchQuery.value.toLowerCase()
  return customers.value.filter(
    (c) =>
      c.custname.toLowerCase().includes(query) ||
      c.area.toLowerCase().includes(query) ||
      c.kota.toLowerCase().includes(query)
  )
})

const formatCurrency = (value: number) => {
  if (value >= 1e9) return `Rp ${(value / 1e9).toFixed(1)} M`
  if (value >= 1e6) return `Rp ${(value / 1e6).toFixed(1)} Jt`
  return `Rp ${value.toLocaleString('id-ID')}`
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('id-ID', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

const columns: DataTableColumns<CustomerData> = [
  {
    title: 'Nama Customer',
    key: 'custname',
    width: 250,
    ellipsis: {
      tooltip: true,
    },
    render: (row) =>
      h(
        'div',
        { class: 'font-semibold text-gray-800 dark:text-gray-200' },
        row.custname
      ),
  },
  {
    title: 'Area',
    key: 'area',
    width: 120,
    render: (row) =>
      h(
        NTag,
        {
          type: 'info',
          round: true,
          size: 'small',
        },
        { default: () => row.area }
      ),
  },
  {
    title: 'Kota',
    key: 'kota',
    width: 150,
  },
  {
    title: 'Total Omzet',
    key: 'total_omzet',
    width: 150,
    align: 'right',
    sorter: (a, b) => a.total_omzet - b.total_omzet,
    render: (row) =>
      h(
        'span',
        { class: 'font-semibold text-indigo-600 dark:text-indigo-400' },
        formatCurrency(row.total_omzet)
      ),
  },
  {
    title: 'Transaksi',
    key: 'total_transactions',
    width: 120,
    align: 'right',
    sorter: (a, b) => a.total_transactions - b.total_transactions,
  },
  {
    title: 'Rata-rata',
    key: 'avg_transaction',
    width: 150,
    align: 'right',
    render: (row) => formatCurrency(row.avg_transaction),
  },
  {
    title: 'Terakhir',
    key: 'last_transaction',
    width: 130,
    render: (row) => formatDate(row.last_transaction),
  },
  {
    title: 'Aksi',
    key: 'actions',
    width: 180,
    align: 'center',
    render: (row) =>
      h(
        NSpace,
        { justify: 'center' },
        {
          default: () => [
            h(
              NButton,
              {
                size: 'small',
                circle: true,
                quaternary: true,
                type: 'info',
                onClick: () => handleView(row),
              },
              { icon: () => h(NIcon, { component: EyeOutline }) }
            ),
            h(
              NButton,
              {
                size: 'small',
                circle: true,
                quaternary: true,
                type: 'primary',
                onClick: () => handleEdit(row),
              },
              { icon: () => h(NIcon, { component: CreateOutline }) }
            ),
            h(
              NButton,
              {
                size: 'small',
                circle: true,
                quaternary: true,
                type: 'success',
                onClick: () => handleCall(row),
              },
              { icon: () => h(NIcon, { component: CallOutline }) }
            ),
          ],
        }
      ),
  },
]

const pagination = {
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [5, 10, 25, 50],
  showQuickJumper: true,
  prefix: (info: any) => `Total ${info.itemCount} customer`,
}

function rowClassName(row: CustomerData, index: number) {
  return 'hover:bg-indigo-50/50 dark:hover:bg-indigo-900/20 transition-colors cursor-pointer'
}

function handleView(row: CustomerData) {
  console.log('View:', row)
}

function handleEdit(row: CustomerData) {
  console.log('Edit:', row)
}

function handleCall(row: CustomerData) {
  console.log('Call:', row)
}

function exportToExcel() {
  const ws = XLSX.utils.json_to_sheet(customers.value)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Customers')
  XLSX.writeFile(wb, `customers-${Date.now()}.xlsx`)
}
</script>

<style scoped>
:deep(.n-data-table-th) {
  font-weight: 600 !important;
  background: linear-gradient(to bottom, #f8fafc, #f1f5f9) !important;
}

:global(.dark) :deep(.n-data-table-th) {
  background: linear-gradient(to bottom, #1f2937, #111827) !important;
}

:deep(.n-data-table-td) {
  padding: 16px 12px !important;
}

:deep(.n-data-table-tr:hover) {
  transform: scale(1.01);
  transition: all 0.2s ease;
}
</style>

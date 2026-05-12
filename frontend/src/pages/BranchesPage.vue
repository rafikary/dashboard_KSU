<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Data Cabang KSU</h1>
      <n-button type="primary" @click="refreshData">
        <template #icon>
          <n-icon :component="RefreshOutline" />
        </template>
        Refresh
      </n-button>
    </div>

    <!-- Filters -->
    <div class="glass-card rounded-2xl p-6">
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
        <n-select
          v-model:value="filterMode"
          :options="filterModeOptions"
          class="w-full"
        />
        <n-date-picker
          v-if="filterMode === 'date'"
          v-model:value="selectedDate"
          type="date"
          placeholder="Pilih Tanggal"
          clearable
          class="w-full"
        />
        <n-date-picker
          v-else-if="filterMode === 'month'"
          v-model:value="selectedMonth"
          type="month"
          placeholder="Pilih Bulan"
          clearable
          class="w-full"
        />
        <n-date-picker
          v-else
          v-model:value="selectedYear"
          type="year"
          placeholder="Pilih Tahun"
          clearable
          class="w-full"
        />
        <n-select
          v-model:value="sortBy"
          :options="sortOptions"
          placeholder="Urutkan Berdasarkan"
          class="w-full"
        />
        <n-select
          v-model:value="sortOrder"
          :options="orderOptions"
          placeholder="Urutan"
          class="w-full"
        />
        <n-button type="primary" @click="applyFilter">Terapkan Filter</n-button>
      </div>
      <p class="text-xs text-gray-500 mt-3">Data performa cabang dan semua angka akan menyesuaikan tanggal, bulan, atau tahun pilihan Anda.</p>
    </div>

    <!-- Summary Cards -->
    <div class="grid grid-cols-1 md:grid-cols-5 gap-6">
      <div class="glass-card rounded-2xl p-6">
        <div class="text-sm text-gray-500 dark:text-gray-400">Cabang Aktif</div>
        <div class="text-2xl font-bold text-gray-900 dark:text-white mt-2">
          {{ branchSummary.total_cabang_aktif }}
        </div>
      </div>
      <div class="glass-card rounded-2xl p-6 border border-amber-200 bg-amber-50/40">
        <div class="text-sm text-amber-700">Cabang Nonaktif</div>
        <div class="text-2xl font-bold text-amber-700 mt-2">
          {{ branchSummary.total_cabang_nonaktif }}
        </div>
      </div>
      <div class="glass-card rounded-2xl p-6">
        <div class="text-sm text-gray-500 dark:text-gray-400">Total Pinjaman</div>
        <div class="text-2xl font-bold text-gray-900 dark:text-white mt-2">
          {{ formatCurrency(totalPinjaman) }}
        </div>
      </div>
      <div class="glass-card rounded-2xl p-6">
        <div class="text-sm text-gray-500 dark:text-gray-400">Rasio NPL (Rata-rata per Cabang)</div>
        <div class="text-2xl font-bold mt-2" :class="nplColor">
          {{ avgNPL.toFixed(2) }}%
        </div>
        <div class="text-xs text-gray-400 mt-1">Pinjaman menunggak >3 bulan</div>
      </div>
      <div class="glass-card rounded-2xl p-6">
        <div class="text-sm text-gray-500 dark:text-gray-400">Collection Rate</div>
        <div class="text-2xl font-bold text-green-600 dark:text-green-400 mt-2">
          {{ avgCollectionRate.toFixed(1) }}%
        </div>
      </div>
    </div>

    <!-- Table -->
    <div class="glass-card rounded-2xl p-6">
      <n-data-table
        :columns="columns"
        :data="branches"
        :loading="loading"
        :pagination="pagination"
        :row-class-name="rowClassName"
      />
    </div>

    <!-- Branch Detail Modal -->
    <n-modal v-model:show="showDetailModal" preset="card" title="Detail Cabang" class="w-full max-w-4xl">
      <div v-if="selectedBranch" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <div class="text-sm text-gray-500">Kode Cabang</div>
            <div class="font-bold">{{ selectedBranch.kode }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Nama Cabang</div>
            <div class="font-bold">{{ selectedBranch.nama }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Flag (Jenis)</div>
            <div class="font-bold">
              {{ selectedBranch.flag }}
              <span class="text-xs text-gray-400">({{ selectedBranch.flag === 'A+B' ? 'Pajak + Non Pajak' : selectedBranch.flag === 'A' ? 'Pajak' : 'Non Pajak' }})</span>
            </div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Status Cabang</div>
            <div :class="selectedBranch.is_nonaktif ? 'font-bold text-amber-600' : 'font-bold text-emerald-600'">
              {{ selectedBranch.is_nonaktif ? 'Nonaktif' : 'Aktif' }}
              <span v-if="selectedBranch.is_nonaktif && selectedBranch.nonaktif_reason" class="text-xs text-amber-500">({{ selectedBranch.nonaktif_reason }})</span>
            </div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Total Pinjaman</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.pinjaman) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Sisa Pinjaman</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.sisa_pinjaman) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Jasa Tertunggak 1 Bulan</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.jasa_ttg_1) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Jasa Tertunggak 2 Bulan</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.jasa_ttg_2) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Jasa Tertunggak 3 Bulan</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.jasa_ttg_3) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Jasa Tertunggak NP (>3 Bulan)</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.jasa_ttg_np) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Sisa Pinjaman NP (Menunggak >3 Bulan)</div>
            <div class="font-bold text-red-600">{{ formatCurrency(selectedBranch.sisa_pinjaman_np) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Rasio NPL (>3 Bulan)</div>
            <div class="font-bold text-red-600">{{ selectedBranch.npl_ratio.toFixed(2) }}%</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Saldo Kas</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.saldo_kas) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Saldo Bank</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.saldo_bank) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Total Likuiditas</div>
            <div class="font-bold text-green-600">{{ formatCurrency(selectedBranch.total_liquidity) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Collection Rate</div>
            <div class="font-bold text-green-600">{{ selectedBranch.collection_rate.toFixed(1) }}%</div>
          </div>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, h } from 'vue'
import { NButton, NIcon, NDataTable, NTag, NDatePicker, NSelect, NModal } from 'naive-ui'
import { RefreshOutline, EyeOutline } from '@vicons/ionicons5'
import type { DataTableColumns } from 'naive-ui'

const loading = ref(true)
const branches = ref<any[]>([])
const branchSummary = ref({
  total_cabang_all: 0,
  total_cabang_aktif: 0,
  total_cabang_nonaktif: 0,
  total_sisa_pinjaman_aktif: 0,
  avg_npl_aktif: 0,
  avg_collection_rate_aktif: 0,
})
const filterMode = ref<'date' | 'month' | 'year'>('date')
const selectedDate = ref<number | null>(null)
const selectedMonth = ref<number | null>(null)
const selectedYear = ref<number | null>(null)
const sortBy = ref('sisapinjaman')
const sortOrder = ref('desc')
const showDetailModal = ref(false)
const selectedBranch = ref<any>(null)

const filterModeOptions = [
  { label: 'Filter Tanggal', value: 'date' },
  { label: 'Filter Bulan', value: 'month' },
  { label: 'Filter Tahun', value: 'year' },
]

const sortOptions = [
  { label: 'Sisa Pinjaman', value: 'sisa_pinjaman' },
  { label: 'Rasio NPL (>3 Bulan)', value: 'npl_ratio' },
  { label: 'Total Jasa Tertunggak', value: 'total_jasa_ttg' },
  { label: 'Collection Rate', value: 'collection_rate' },
  { label: 'Total Likuiditas', value: 'total_liquidity' },
]

const orderOptions = [
  { label: 'Tertinggi ke Terendah', value: 'desc' },
  { label: 'Terendah ke Tertinggi', value: 'asc' },
]

const pagination = {
  pageSize: 20,
}

const columns: DataTableColumns = [
  {
    title: 'Kode',
    key: 'kode',
    width: 100,
    fixed: 'left',
  },
  {
    title: 'Nama Cabang',
    key: 'nama',
    width: 200,
    fixed: 'left',
  },
  {
    title: 'Status',
    key: 'status',
    width: 140,
    render: (row: any) => h(
      NTag,
      { type: row.is_nonaktif ? 'warning' : 'success' },
      { default: () => row.is_nonaktif ? 'Nonaktif' : 'Aktif' }
    ),
  },
  {
    title: 'Sisa Pinjaman',
    key: 'sisa_pinjaman',
    width: 150,
    render: (row: any) => formatCurrency(row.sisa_pinjaman),
    sorter: (a: any, b: any) => a.sisa_pinjaman - b.sisa_pinjaman,
  },
  {
    title: 'Rasio NPL (>3 Bulan)',
    key: 'npl_ratio',
    width: 120,
    render: (row: any) => {
      const color = row.npl_ratio > 10 ? 'error' : row.npl_ratio > 5 ? 'warning' : 'success'
      return h(NTag, { type: color }, { default: () => `${row.npl_ratio.toFixed(2)}%` })
    },
    sorter: (a: any, b: any) => a.npl_ratio - b.npl_ratio,
  },
  {
    title: 'Jasa Tertunggak',
    key: 'total_jasa_ttg',
    width: 150,
    render: (row: any) => formatCurrency(row.total_jasa_ttg),
    sorter: (a: any, b: any) => a.total_jasa_ttg - b.total_jasa_ttg,
  },
  {
    title: 'Collection Rate',
    key: 'collection_rate',
    width: 140,
    render: (row: any) => {
      const color = row.collection_rate > 80 ? 'success' : row.collection_rate > 60 ? 'warning' : 'error'
      return h(NTag, { type: color }, { default: () => `${row.collection_rate.toFixed(1)}%` })
    },
    sorter: (a: any, b: any) => a.collection_rate - b.collection_rate,
  },
  {
    title: 'Likuiditas',
    key: 'total_liquidity',
    width: 150,
    render: (row: any) => formatCurrency(row.total_liquidity),
    sorter: (a: any, b: any) => a.total_liquidity - b.total_liquidity,
  },
  {
    title: 'Aksi',
    key: 'actions',
    width: 100,
    fixed: 'right',
    render: (row: any) => {
      return h(
        NButton,
        {
          size: 'small',
          type: 'primary',
          onClick: () => showDetail(row),
        },
        { default: () => 'Detail', icon: () => h(NIcon, { component: EyeOutline }) }
      )
    },
  },
]

const totalPinjaman = computed(() => {
  return branchSummary.value.total_sisa_pinjaman_aktif
})

const avgNPL = computed(() => {
  return branchSummary.value.avg_npl_aktif || 0
})

const avgCollectionRate = computed(() => {
  return branchSummary.value.avg_collection_rate_aktif || 0
})

const nplColor = computed(() => {
  if (avgNPL.value > 10) return 'text-red-600 dark:text-red-400'
  if (avgNPL.value > 5) return 'text-orange-600 dark:text-orange-400'
  return 'text-green-600 dark:text-green-400'
})

async function fetchBranches() {
  try {
    loading.value = true
    const params = new URLSearchParams()

    const range = getSelectedRange()
    if (range) {
      params.append('date_from', range.dateFrom)
      params.append('date_to', range.dateTo)
    }

    params.append('sort_by', sortBy.value)
    params.append('order', sortOrder.value)
    
    const response = await fetch(`http://localhost:5000/api/ksu/branches?${params}`)
    const data = await response.json()
    branches.value = data.branches || []
    branchSummary.value = data.summary || branchSummary.value
  } catch (error) {
    console.error('Error fetching branches:', error)
  } finally {
    loading.value = false
  }
}

function refreshData() {
  fetchBranches()
}

function applyFilter() {
  fetchBranches()
}

function toIsoDate(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function getSelectedRange(): { dateFrom: string; dateTo: string } | null {
  if (filterMode.value === 'date' && selectedDate.value) {
    const target = new Date(selectedDate.value)
    const iso = toIsoDate(target)
    return { dateFrom: iso, dateTo: iso }
  }

  if (filterMode.value === 'month' && selectedMonth.value) {
    const target = new Date(selectedMonth.value)
    const start = new Date(target.getFullYear(), target.getMonth(), 1)
    const end = new Date(target.getFullYear(), target.getMonth() + 1, 0)
    return { dateFrom: toIsoDate(start), dateTo: toIsoDate(end) }
  }

  if (filterMode.value === 'year' && selectedYear.value) {
    const target = new Date(selectedYear.value)
    const start = new Date(target.getFullYear(), 0, 1)
    const end = new Date(target.getFullYear(), 11, 31)
    return { dateFrom: toIsoDate(start), dateTo: toIsoDate(end) }
  }

  return null
}

function showDetail(branch: any) {
  selectedBranch.value = branch
  showDetailModal.value = true
}

function rowClassName(row: any) {
  if (row.is_nonaktif) return 'branch-inactive'
  if (row.npl_ratio > 10) return 'npl-high'
  if (row.npl_ratio > 5) return 'npl-medium'
  return ''
}

function formatCurrency(value: number) {
  if (value >= 1e9) return `Rp ${(value / 1e9).toFixed(2)}M`
  if (value >= 1e6) return `Rp ${(value / 1e6).toFixed(2)}Jt`
  if (value >= 1e3) return `Rp ${(value / 1e3).toFixed(0)}rb`
  return `Rp ${value.toLocaleString('id-ID')}`
}

watch([sortBy, sortOrder], () => {
  fetchBranches()
})

onMounted(() => {
  fetchBranches()
})
</script>

<style scoped>
:deep(.npl-high) {
  background-color: rgba(239, 68, 68, 0.1);
}

:deep(.npl-medium) {
  background-color: rgba(251, 146, 60, 0.1);
}

:deep(.branch-inactive) {
  background-color: rgba(245, 158, 11, 0.12);
}
</style>

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
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <n-date-picker
          v-model:value="dateFilter"
          type="date"
          placeholder="Pilih Tanggal"
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
      </div>
    </div>

    <!-- Summary Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
      <div class="glass-card rounded-2xl p-6">
        <div class="text-sm text-gray-500 dark:text-gray-400">Total Cabang</div>
        <div class="text-2xl font-bold text-gray-900 dark:text-white mt-2">
          {{ branches.length }}
        </div>
      </div>
      <div class="glass-card rounded-2xl p-6">
        <div class="text-sm text-gray-500 dark:text-gray-400">Total Pinjaman</div>
        <div class="text-2xl font-bold text-gray-900 dark:text-white mt-2">
          {{ formatCurrency(totalPinjaman) }}
        </div>
      </div>
      <div class="glass-card rounded-2xl p-6">
        <div class="text-sm text-gray-500 dark:text-gray-400">NPL Ratio</div>
        <div class="text-2xl font-bold mt-2" :class="nplColor">
          {{ avgNPL.toFixed(2) }}%
        </div>
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
            <div class="text-sm text-gray-500">Total Pinjaman</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.pinjaman) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Sisa Pinjaman</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.sisa_pinjaman) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Jasa Tertunggak 1</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.jasa_ttg_1) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Jasa Tertunggak 2</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.jasa_ttg_2) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Jasa Tertunggak 3</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.jasa_ttg_3) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Jasa Tertunggak NP</div>
            <div class="font-bold">{{ formatCurrency(selectedBranch.jasa_ttg_np) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">Sisa Pinjaman NP</div>
            <div class="font-bold text-red-600">{{ formatCurrency(selectedBranch.sisa_pinjaman_np) }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">NPL Ratio</div>
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
const dateFilter = ref<number | null>(null)
const sortBy = ref('sisapinjaman')
const sortOrder = ref('desc')
const showDetailModal = ref(false)
const selectedBranch = ref<any>(null)

const sortOptions = [
  { label: 'Sisa Pinjaman', value: 'sisa_pinjaman' },
  { label: 'NPL Ratio', value: 'npl_ratio' },
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
    title: 'Sisa Pinjaman',
    key: 'sisa_pinjaman',
    width: 150,
    render: (row: any) => formatCurrency(row.sisa_pinjaman),
    sorter: (a: any, b: any) => a.sisa_pinjaman - b.sisa_pinjaman,
  },
  {
    title: 'NPL Ratio',
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
  return branches.value.reduce((sum, b) => sum + b.sisa_pinjaman, 0)
})

const avgNPL = computed(() => {
  if (branches.value.length === 0) return 0
  const sum = branches.value.reduce((s, b) => s + b.npl_ratio, 0)
  return sum / branches.value.length
})

const avgCollectionRate = computed(() => {
  if (branches.value.length === 0) return 0
  const sum = branches.value.reduce((s, b) => s + b.collection_rate, 0)
  return sum / branches.value.length
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
    if (dateFilter.value) {
      const date = new Date(dateFilter.value)
      params.append('date', date.toISOString().split('T')[0])
    }
    params.append('sort_by', sortBy.value)
    params.append('order', sortOrder.value)
    
    const response = await fetch(`http://localhost:5000/api/ksu/branches?${params}`)
    const data = await response.json()
    branches.value = data.branches || []
  } catch (error) {
    console.error('Error fetching branches:', error)
  } finally {
    loading.value = false
  }
}

function refreshData() {
  fetchBranches()
}

function showDetail(branch: any) {
  selectedBranch.value = branch
  showDetailModal.value = true
}

function rowClassName(row: any) {
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

watch([dateFilter, sortBy, sortOrder], () => {
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
</style>

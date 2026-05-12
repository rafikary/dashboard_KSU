<template>
  <div class="dashboard-container space-y-5">
    <div class="filter-card">
      <div class="filter-grid">
        <n-select
          v-model:value="filterMode"
          :options="filterModeOptions"
          class="filter-input"
        />

        <n-date-picker
          v-if="filterMode === 'date'"
          v-model:value="selectedDate"
          type="date"
          clearable
          placeholder="Pilih tanggal"
          class="filter-input"
        />

        <n-date-picker
          v-else-if="filterMode === 'month'"
          v-model:value="selectedMonth"
          type="month"
          clearable
          placeholder="Pilih bulan"
          class="filter-input"
        />

        <n-date-picker
          v-else
          v-model:value="selectedYear"
          type="year"
          clearable
          placeholder="Pilih tahun"
          class="filter-input"
        />

        <n-button type="primary" @click="applyFilter">Terapkan</n-button>
        <n-button quaternary @click="resetFilter">Reset</n-button>
      </div>
      <p class="filter-note">Semua KPI dan chart mengikuti filter tanggal, bulan, atau tahun yang dipilih.</p>
    </div>

    <!-- Compact KPI Cards -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <n-skeleton height="120px" v-for="i in 4" :key="i" />
    </div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div
        v-for="(metric, index) in metrics"
        :key="index"
        class="kpi-card"
        :style="{ animationDelay: `${index * 0.1}s` }"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="flex-1">
            <p class="kpi-label">{{ metric.label }}</p>
            <h3 class="kpi-value" :style="{ color: metric.valueColor }">
              {{ formatValue(metric.value, metric.format) }}
            </h3>
            <p v-if="metric.subtitle" class="kpi-subtitle">{{ metric.subtitle }}</p>
          </div>
          <div class="kpi-icon" :style="{ background: metric.iconBg }">
            <n-icon :component="metric.icon" size="22" class="text-white" />
          </div>
        </div>
      </div>
    </div>

    <!-- Summary Info Bar -->
    <div class="info-bar" v-if="summary">
      <div class="info-item">
        <span class="info-label">Cabang Aktif</span>
        <span class="info-value">{{ summary.jumlah_cabang_aktif || summary.jumlah_cabang }} Cabang</span>
      </div>
      <div class="info-divider"></div>
      <div class="info-item">
        <span class="info-label">Cabang Nonaktif</span>
        <span class="info-value text-yellow-300">{{ summary.jumlah_cabang_nonaktif || 0 }} Cabang</span>
      </div>
      <div class="info-divider"></div>
      <div class="info-item">
        <span class="info-label">Rasio NPL (Menunggak >3 Bulan)</span>
        <span class="info-value" :class="summary.npl_ratio > 10 ? 'text-red-600' : summary.npl_ratio > 5 ? 'text-orange-600' : 'text-green-600'">
          {{ formatPercent(summary.npl_ratio) }}%
        </span>
      </div>
      <div class="info-divider"></div>
      <div class="info-item">
        <span class="info-label">Collection Rate</span>
        <span class="info-value text-blue-600">{{ formatPercent(summary.collection_rate) }}%</span>
      </div>
      <div class="info-divider"></div>
      <div class="info-item">
        <span class="info-label">Update Terakhir</span>
        <span class="info-value">{{ summary.latest_date }}</span>
      </div>
    </div>

    <!-- Charts Section -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Trend Chart -->
      <div class="chart-card">
        <div class="chart-header">
          <h3 class="chart-title">Trend Pinjaman 6 Bulan Terakhir</h3>
          <p class="chart-subtitle">Monitoring perkembangan pinjaman dan NPL (menunggak >3 bulan)</p>
        </div>
        <div v-if="loadingCharts" class="chart-loading">
          <n-spin size="large" />
        </div>
        <v-chart v-else :option="trendChartOption" style="height: 320px" autoresize />
      </div>

      <!-- NPL Ranking Chart -->
      <div class="chart-card">
        <div class="chart-header">
          <h3 class="chart-title">Top 10 Cabang dengan NPL Tertinggi</h3>
          <p class="chart-subtitle">Pinjaman menunggak lebih dari 3 bulan</p>
        </div>
        <div v-if="loadingCharts" class="chart-loading">
          <n-spin size="large" />
        </div>
        <v-chart v-else :option="nplRankingOption" style="height: 320px" autoresize />
      </div>

      <!-- Collection Rate Distribution -->
      <div class="chart-card">
        <div class="chart-header">
          <h3 class="chart-title">Distribusi Collection Rate</h3>
          <p class="chart-subtitle">Persentase cabang per kategori collection</p>
        </div>
        <div v-if="loadingCharts" class="chart-loading">
          <n-spin size="large" />
        </div>
        <v-chart v-else :option="collectionDistOption" style="height: 320px" autoresize />
      </div>

      <!-- Liquidity Overview -->
      <div class="chart-card">
        <div class="chart-header">
          <h3 class="chart-title">Overview Likuiditas</h3>
          <p class="chart-subtitle">Komposisi kas dan bank</p>
        </div>
        <div v-if="loadingCharts" class="chart-loading">
          <n-spin size="large" />
        </div>
        <v-chart v-else :option="liquidityOption" style="height: 320px" autoresize />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { NIcon, NSkeleton, NSpin, NSelect, NDatePicker, NButton } from 'naive-ui'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import {
  CashOutline,
  WalletOutline,
  BusinessOutline,
  TrendingDownOutline,
} from '@vicons/ionicons5'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
])

const loading = ref(true)
const loadingCharts = ref(true)
const summary = ref<any>(null)
const trendData = ref<any[]>([])
const branchesData = ref<any[]>([])
const filterMode = ref<'date' | 'month' | 'year'>('date')
const selectedDate = ref<number | null>(null)
const selectedMonth = ref<number | null>(null)
const selectedYear = ref<number | null>(null)

const filterModeOptions = [
  { label: 'Filter Tanggal', value: 'date' },
  { label: 'Filter Bulan', value: 'month' },
  { label: 'Filter Tahun', value: 'year' },
]

const metrics = ref([
  {
    label: 'Total Pinjaman',
    value: 0,
    subtitle: '',
    format: 'currency',
    icon: CashOutline,
    valueColor: '#3b82f6',
    iconBg: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
  },
  {
    label: 'Sisa Pinjaman',
    value: 0,
    subtitle: '',
    format: 'currency',
    icon: WalletOutline,
    valueColor: '#10b981',
    iconBg: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
  },
  {
    label: 'Jasa Tertunggak',
    value: 0,
    subtitle: '',
    format: 'currency',
    icon: TrendingDownOutline,
    valueColor: '#ef4444',
    iconBg: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
  },
  {
    label: 'Total Likuiditas',
    value: 0,
    subtitle: 'Kas + Bank',
    format: 'currency',
    icon: BusinessOutline,
    valueColor: '#f59e0b',
    iconBg: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
  },
])

async function fetchData() {
  try {
    loading.value = true
    loadingCharts.value = true

    const range = getSelectedRange()
    const summaryParams = new URLSearchParams()
    const trendParams = new URLSearchParams({ granularity: 'month', include_nonaktif: 'false' })
    const branchParams = new URLSearchParams({ sort_by: 'npl_ratio', order: 'desc', include_nonaktif: 'false' })

    if (range) {
      summaryParams.append('date_from', range.dateFrom)
      summaryParams.append('date_to', range.dateTo)
      trendParams.append('date_from', range.dateFrom)
      trendParams.append('date_to', range.dateTo)
      branchParams.append('date_from', range.dateFrom)
      branchParams.append('date_to', range.dateTo)
    }

    const summaryUrl = summaryParams.toString()
      ? `http://localhost:5000/api/ksu/summary?${summaryParams}`
      : 'http://localhost:5000/api/ksu/summary'
    const summaryRes = await fetch(summaryUrl)
    const summaryData = await summaryRes.json()
    summary.value = summaryData

    if (!range) {
      const now = new Date()
      const sixMonthsAgo = new Date(now.getFullYear(), now.getMonth() - 6, 1)
      trendParams.append('date_from', toIsoDate(sixMonthsAgo))
    }

    const trendRes = await fetch(`http://localhost:5000/api/ksu/trend?${trendParams}`)
    const trendResult = await trendRes.json()
    trendData.value = trendResult.data || []

    const branchesRes = await fetch(`http://localhost:5000/api/ksu/branches?${branchParams}`)
    const branchesResult = await branchesRes.json()
    branchesData.value = branchesResult.branches || []

    metrics.value[0].value = summaryData.total_pinjaman
    metrics.value[0].subtitle = `${summaryData.jumlah_cabang_aktif || summaryData.jumlah_cabang} Cabang Aktif`

    metrics.value[1].value = summaryData.total_sisa_pinjaman
    metrics.value[1].subtitle = `${summaryData.collection_rate.toFixed(1)}% terkumpul`

    metrics.value[2].value = summaryData.total_jasa_tertunggak
    metrics.value[2].subtitle = `NPL (>3 Bulan): Rp ${(summaryData.total_sisa_pinjaman_np / 1e9).toFixed(1)}M`

    metrics.value[3].value = summaryData.total_saldo_kas + summaryData.total_saldo_bank
    metrics.value[3].subtitle = `Bank: Rp ${(summaryData.total_saldo_bank / 1e9).toFixed(1)}M`

  } catch (error) {
    console.error('Error fetching data:', error)
  } finally {
    loading.value = false
    loadingCharts.value = false
  }
}

function applyFilter() {
  fetchData()
}

function resetFilter() {
  selectedDate.value = null
  selectedMonth.value = null
  selectedYear.value = null
  filterMode.value = 'date'
  fetchData()
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

const trendChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderColor: '#e5e7eb',
    borderWidth: 1,
    textStyle: { color: '#374151', fontSize: 12 },
  },
  legend: {
    data: ['Sisa Pinjaman', 'Rasio NPL (>3 Bulan)'],
    bottom: 0,
    textStyle: { fontSize: 11, color: '#6b7280' }
  },
  grid: { left: '3%', right: '4%', bottom: '12%', top: '8%', containLabel: true },
  xAxis: {
    type: 'category',
    data: trendData.value.map(d => {
      const date = new Date(d.period)
      return date.toLocaleDateString('id-ID', { month: 'short', year: '2-digit' })
    }),
    axisLabel: { fontSize: 11, color: '#6b7280' },
    axisLine: { lineStyle: { color: '#e5e7eb' } }
  },
  yAxis: [
    {
      type: 'value',
      name: 'Miliar Rp',
      nameTextStyle: { fontSize: 11, color: '#6b7280' },
      axisLabel: { 
        fontSize: 11, 
        color: '#6b7280',
        formatter: (val: number) => `${(val / 1e9).toFixed(0)}`
      },
      splitLine: { lineStyle: { color: '#f3f4f6' } }
    },
    {
      type: 'value',
      name: 'Rasio NPL (>3 Bulan) %',
      nameTextStyle: { fontSize: 11, color: '#6b7280' },
      axisLabel: { fontSize: 11, color: '#6b7280', formatter: '{value}%' },
      splitLine: { show: false }
    }
  ],
  series: [
    {
      name: 'Sisa Pinjaman',
      type: 'line',
      data: trendData.value.map(d => d.sisa_pinjaman),
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 2.5, color: '#3b82f6' },
      itemStyle: { color: '#3b82f6' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(59, 130, 246, 0.25)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
          ]
        }
      }
    },
    {
      name: 'Rasio NPL (>3 Bulan)',
      type: 'line',
      yAxisIndex: 1,
      data: trendData.value.map(d => d.npl_ratio),
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 2.5, color: '#ef4444' },
      itemStyle: { color: '#ef4444' }
    }
  ]
}))

const nplRankingOption = computed(() => {
  const top10 = branchesData.value.slice(0, 10)
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: { color: '#374151', fontSize: 12 },
    },
    grid: { left: '15%', right: '4%', bottom: '3%', top: '3%', containLabel: true },
    xAxis: {
      type: 'value',
      axisLabel: { fontSize: 11, color: '#6b7280', formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#f3f4f6' } }
    },
    yAxis: {
      type: 'category',
      data: top10.map(b => b.kode),
      axisLabel: { fontSize: 11, color: '#6b7280' },
      axisLine: { lineStyle: { color: '#e5e7eb' } }
    },
    series: [{
      type: 'bar',
      data: top10.map(b => ({
        value: b.npl_ratio,
        itemStyle: {
          color: b.npl_ratio > 50 ? '#dc2626' : b.npl_ratio > 30 ? '#ef4444' : b.npl_ratio > 10 ? '#f59e0b' : '#10b981'
        }
      })),
      barWidth: '60%',
      label: {
        show: true,
        position: 'right',
        formatter: '{c}%',
        fontSize: 11,
        color: '#374151'
      }
    }]
  }
})

const collectionDistOption = computed(() => {
  const excellent = branchesData.value.filter(b => b.collection_rate >= 80).length
  const good = branchesData.value.filter(b => b.collection_rate >= 60 && b.collection_rate < 80).length
  const fair = branchesData.value.filter(b => b.collection_rate >= 40 && b.collection_rate < 60).length
  const poor = branchesData.value.filter(b => b.collection_rate < 40).length

  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: { color: '#374151', fontSize: 12 },
      formatter: '{b}: {c} cabang ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: '10%',
      top: 'center',
      textStyle: { fontSize: 11, color: '#6b7280' }
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      label: {
        show: false
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 14,
          fontWeight: 'bold'
        }
      },
      data: [
        { value: excellent, name: 'Excellent (≥80%)', itemStyle: { color: '#10b981' } },
        { value: good, name: 'Good (60-79%)', itemStyle: { color: '#3b82f6' } },
        { value: fair, name: 'Fair (40-59%)', itemStyle: { color: '#f59e0b' } },
        { value: poor, name: 'Poor (<40%)', itemStyle: { color: '#ef4444' } }
      ]
    }]
  }
})

const liquidityOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderColor: '#e5e7eb',
    borderWidth: 1,
    textStyle: { color: '#374151', fontSize: 12 },
  },
  legend: {
    orient: 'vertical',
    right: '10%',
    top: 'center',
    textStyle: { fontSize: 11, color: '#6b7280' }
  },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    center: ['35%', '50%'],
    data: [
      { 
        value: summary.value?.total_saldo_kas || 0, 
        name: 'Saldo Kas',
        itemStyle: { color: '#3b82f6' }
      },
      { 
        value: summary.value?.total_saldo_bank || 0, 
        name: 'Saldo Bank',
        itemStyle: { color: '#10b981' }
      }
    ],
    label: {
      fontSize: 11,
      color: '#374151',
      formatter: '{b}\n{d}%'
    },
    emphasis: {
      label: {
        show: true,
        fontSize: 14,
        fontWeight: 'bold'
      }
    }
  }]
}))

onMounted(() => {
  fetchData()
})

function formatValue(value: number, format?: string) {
  if (format === 'currency') {
    if (value >= 1e9) return `Rp ${(value / 1e9).toFixed(1)}M`
    if (value >= 1e6) return `Rp ${(value / 1e6).toFixed(1)}Jt`
    return `Rp ${value.toLocaleString('id-ID')}`
  }
  return value.toLocaleString('id-ID')
}

function formatPercent(value: number) {
  return Math.abs(value).toFixed(1)
}
</script>

<style scoped>
.dashboard-container {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  max-width: 1400px;
  margin: 0 auto;
}

.filter-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 14px 16px;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  align-items: center;
}

.filter-input {
  width: 100%;
}

.filter-note {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.kpi-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 18px;
  transition: all 0.3s ease;
  animation: fadeInUp 0.5s ease-out forwards;
}

.kpi-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.kpi-label {
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
  display: block;
}

.kpi-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 4px;
}

.kpi-subtitle {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 500;
}

.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.info-bar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  animation: fadeInUp 0.6s ease-out forwards;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 11px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 16px;
  font-weight: 700;
  color: white;
}

.info-divider {
  width: 1px;
  height: 36px;
  background: rgba(255, 255, 255, 0.2);
}

.chart-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  animation: fadeInUp 0.7s ease-out forwards;
}

.chart-header {
  margin-bottom: 16px;
}

.chart-title {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  margin-bottom: 4px;
}

.chart-subtitle {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.chart-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 320px;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 992px) {
  .filter-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>

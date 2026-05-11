<template>
  <div class="space-y-6">
    <!-- Period Selector with Modern Design -->
    <div class="glass-card rounded-3xl p-6">
      <div class="flex items-center justify-between flex-wrap gap-4">
        <div class="flex items-center gap-3">
          <span class="text-sm font-medium text-gray-600 dark:text-gray-400">Periode:</span>
          <n-tag
            v-for="period in periods"
            :key="period.id"
            :type="period.id === 'current' ? 'primary' : 'default'"
            size="medium"
            round
            class="px-4 py-2"
          >
            <span :style="{ color: period.color }">{{ period.label }}</span>
          </n-tag>
        </div>
        
        <n-button-group>
          <n-button
            :type="timeframe === 'month' ? 'primary' : 'default'"
            @click="timeframe = 'month'"
          >
            Bulanan
          </n-button>
          <n-button
            :type="timeframe === 'quarter' ? 'primary' : 'default'"
            @click="timeframe = 'quarter'"
          >
            Quarterly
          </n-button>
          <n-button
            :type="timeframe === 'year' ? 'primary' : 'default'"
            @click="timeframe = 'year'"
          >
            Tahunan
          </n-button>
        </n-button-group>
      </div>
    </div>

    <!-- KPI Comparison Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <div
        v-for="metric in metrics"
        :key="metric.id"
        class="glass-card rounded-3xl p-6 hover-lift"
      >
        <div class="flex items-center justify-between mb-4">
          <span class="text-sm font-medium text-gray-500 dark:text-gray-400">{{ metric.label }}</span>
          <n-icon :component="TrendingUpOutline" size="20" :class="metric.change >= 0 ? 'text-green-500 dark:text-green-400' : 'text-red-500 dark:text-red-400'" />
        </div>
        
        <h3 class="text-3xl font-bold text-gray-800 dark:text-white mb-3">
          {{ formatValue(metric.currentValue, metric.format) }}
        </h3>
        
        <div class="space-y-2">
          <div class="flex items-center justify-between text-sm">
            <span class="text-gray-500 dark:text-gray-400">Sebelumnya:</span>
            <span class="font-medium text-gray-600 dark:text-gray-300">
              {{ formatValue(metric.previousValue, metric.format) }}
            </span>
          </div>
          
          <n-tag
            :type="metric.change >= 0 ? 'success' : 'error'"
            size="small"
            round
            class="w-full justify-center font-semibold"
          >
            {{ metric.change >= 0 ? '+' : '' }}{{ metric.changePercent.toFixed(1) }}%
          </n-tag>
        </div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Line Chart -->
      <div class="glass-card rounded-3xl p-6">
        <h3 class="text-xl font-bold text-gray-800 dark:text-white mb-4">Trend Omzet Bulanan</h3>
        <v-chart :option="lineChartOption" style="height: 350px" autoresize />
      </div>

      <!-- Bar Chart -->
      <div class="glass-card rounded-3xl p-6">
        <h3 class="text-xl font-bold text-gray-800 dark:text-white mb-4">Perbandingan Per Bulan</h3>
        <v-chart :option="barChartOption" style="height: 350px" autoresize />
      </div>
    </div>

    <!-- Category Comparison -->
    <div class="glass-card rounded-3xl p-6">
      <h3 class="text-xl font-bold text-gray-800 dark:text-white mb-6">Perbandingan Per Kategori</h3>
      
      <div class="space-y-6">
        <div v-for="category in categoryData" :key="category.metric" class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="font-semibold text-gray-800 dark:text-gray-200">{{ category.metric }}</span>
            <n-tag type="success" size="small" round v-if="category.current > category.previous">
              +{{ ((category.current - category.previous) / category.previous * 100).toFixed(1) }}%
            </n-tag>
          </div>
          
          <div class="grid grid-cols-3 gap-4">
            <div
              v-for="(period, idx) in periods"
              :key="period.id"
              class="space-y-2"
            >
              <div class="flex justify-between text-sm">
                <span class="text-gray-500 dark:text-gray-400">{{ period.label }}</span>
                <span class="font-semibold dark:text-gray-300">
                  {{ formatValue(category[period.id], 'currency') }}
                </span>
              </div>
              
              <div class="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :style="{
                    width: `${(category[period.id] / Math.max(...Object.values(category).filter(v => typeof v === 'number'))) * 100}%`,
                    background: period.color,
                  }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Insights Card -->
    <div class="glass-card rounded-3xl p-8 bg-gradient-to-r from-indigo-500 to-purple-600 text-white">
      <div class="flex items-start gap-4">
        <div class="w-12 h-12 rounded-2xl bg-white/20 flex items-center justify-center flex-shrink-0">
          <n-icon :component="BulbOutline" size="28" />
        </div>
        <div class="flex-1">
          <h3 class="text-2xl font-bold mb-4">Insight & Rekomendasi</h3>
          <div class="space-y-3 text-white/90">
            <p>• <strong>Pertumbuhan Positif:</strong> Omzet bulan ini naik 13.6% dibanding bulan lalu</p>
            <p>• <strong>Jakarta Melampaui Target:</strong> Area Jakarta mencapai 111% dari target</p>
            <p>• <strong>Perhatian Surabaya:</strong> Area Surabaya masih di bawah target 6.7%</p>
            <p>• <strong>Kategori Tumbuh:</strong> Semua kategori menunjukkan pertumbuhan positif</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDark } from '@vueuse/core'
import { NButton, NButtonGroup, NTag, NIcon } from 'naive-ui'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import {
  TrendingUpOutline,
  BulbOutline,
} from '@vicons/ionicons5'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
])

const isDark = useDark()
const timeframe = ref('month')

const periods = [
  { id: 'current', label: 'Bulan Ini', color: '#6366f1' },
  { id: 'previous', label: 'Bulan Lalu', color: '#94a3b8' },
  { id: 'lastYear', label: 'Tahun Lalu', color: '#f59e0b' },
]

const metrics = ref([
  {
    id: 'omzet',
    label: 'Total Omzet',
    currentValue: 2500000000,
    previousValue: 2200000000,
    change: 300000000,
    changePercent: 13.6,
    format: 'currency',
  },
  {
    id: 'transactions',
    label: 'Jumlah Transaksi',
    currentValue: 1250,
    previousValue: 1180,
    change: 70,
    changePercent: 5.9,
    format: 'number',
  },
  {
    id: 'customers',
    label: 'Customer Aktif',
    currentValue: 342,
    previousValue: 328,
    change: 14,
    changePercent: 4.3,
    format: 'number',
  },
  {
    id: 'avg',
    label: 'Rata-rata Transaksi',
    currentValue: 2000000,
    previousValue: 1864406,
    change: 135594,
    changePercent: 7.3,
    format: 'currency',
  },
])

const monthlyData = [
  { name: 'Jan', current: 1800000000, previous: 1600000000, lastYear: 1500000000 },
  { name: 'Feb', current: 1900000000, previous: 1700000000, lastYear: 1600000000 },
  { name: 'Mar', current: 2100000000, previous: 1950000000, lastYear: 1800000000 },
  { name: 'Apr', current: 2200000000, previous: 2050000000, lastYear: 1900000000 },
  { name: 'Mei', current: 2500000000, previous: 2200000000, lastYear: 2000000000 },
]

const categoryData = ref([
  { metric: 'Elektronik', current: 800000000, previous: 700000000, lastYear: 650000000 },
  { metric: 'Furniture', current: 600000000, previous: 550000000, lastYear: 500000000 },
  { metric: 'Makanan & Minuman', current: 450000000, previous: 420000000, lastYear: 400000000 },
  { metric: 'Pakaian', current: 350000000, previous: 330000000, lastYear: 300000000 },
  { metric: 'Lain-lain', current: 300000000, previous: 200000000, lastYear: 150000000 },
])

const lineChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'cross' },
    backgroundColor: isDark.value ? '#1f2937' : '#ffffff',
    borderColor: isDark.value ? '#374151' : '#e5e7eb',
    textStyle: {
      color: isDark.value ? '#f3f4f6' : '#1f2937',
    },
  },
  legend: {
    data: periods.map((p) => p.label),
    bottom: 0,
    textStyle: {
      color: isDark.value ? '#e5e7eb' : '#374151',
    },
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '10%',
    top: '5%',
    containLabel: true,
  },
  xAxis: {
    type: 'category',
    data: monthlyData.map((d) => d.name),
    axisLine: {
      lineStyle: {
        color: isDark.value ? '#4b5563' : '#d1d5db',
      },
    },
    axisLabel: {
      color: isDark.value ? '#9ca3af' : '#6b7280',
    },
  },
  yAxis: {
    type: 'value',
    axisLine: {
      lineStyle: {
        color: isDark.value ? '#4b5563' : '#d1d5db',
      },
    },
    axisLabel: {
      color: isDark.value ? '#9ca3af' : '#6b7280',
      formatter: (value: number) => {
        if (value >= 1e9) return `${(value / 1e9).toFixed(1)}M`
        if (value >= 1e6) return `${(value / 1e6).toFixed(0)}Jt`
        return value
      },
    },
    splitLine: {
      lineStyle: {
        color: isDark.value ? '#374151' : '#e5e7eb',
      },
    },
  },
  series: [
    {
      name: 'Bulan Ini',
      type: 'line',
      smooth: true,
      data: monthlyData.map((d) => d.current),
      itemStyle: { color: '#6366f1' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(99, 102, 241, 0.3)' },
            { offset: 1, color: 'rgba(99, 102, 241, 0.0)' },
          ],
        },
      },
    },
    {
      name: 'Bulan Lalu',
      type: 'line',
      smooth: true,
      data: monthlyData.map((d) => d.previous),
      itemStyle: { color: '#94a3b8' },
    },
    {
      name: 'Tahun Lalu',
      type: 'line',
      smooth: true,
      data: monthlyData.map((d) => d.lastYear),
      itemStyle: { color: '#f59e0b' },
    },
  ],
}))

const barChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
    backgroundColor: isDark.value ? '#1f2937' : '#ffffff',
    borderColor: isDark.value ? '#374151' : '#e5e7eb',
    textStyle: {
      color: isDark.value ? '#f3f4f6' : '#1f2937',
    },
  },
  legend: {
    data: periods.map((p) => p.label),
    bottom: 0,
    textStyle: {
      color: isDark.value ? '#e5e7eb' : '#374151',
    },
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '10%',
    top: '5%',
    containLabel: true,
  },
  xAxis: {
    type: 'category',
    data: monthlyData.map((d) => d.name),
    axisLine: {
      lineStyle: {
        color: isDark.value ? '#4b5563' : '#d1d5db',
      },
    },
    axisLabel: {
      color: isDark.value ? '#9ca3af' : '#6b7280',
    },
  },
  yAxis: {
    type: 'value',
    axisLine: {
      lineStyle: {
        color: isDark.value ? '#4b5563' : '#d1d5db',
      },
    },
    axisLabel: {
      color: isDark.value ? '#9ca3af' : '#6b7280',
      formatter: (value: number) => {
        if (value >= 1e9) return `${(value / 1e9).toFixed(1)}M`
        if (value >= 1e6) return `${(value / 1e6).toFixed(0)}Jt`
        return value
      },
    },
    splitLine: {
      lineStyle: {
        color: isDark.value ? '#374151' : '#e5e7eb',
      },
    },
  },
  series: periods.map((period, idx) => ({
    name: period.label,
    type: 'bar',
    data: monthlyData.map((d) => d[period.id as keyof typeof d]),
    itemStyle: {
      color: period.color,
      borderRadius: [8, 8, 0, 0],
    },
  })),
}))

function formatValue(value: number, format?: string) {
  if (format === 'currency') {
    if (value >= 1e9) return `Rp ${(value / 1e9).toFixed(1)} M`
    if (value >= 1e6) return `Rp ${(value / 1e6).toFixed(1)} Jt`
    return `Rp ${value.toLocaleString('id-ID')}`
  }
  return value.toLocaleString('id-ID')
}
</script>

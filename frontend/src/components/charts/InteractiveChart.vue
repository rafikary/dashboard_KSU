<template>
  <div class="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border dark:border-gray-700">
    <div class="flex justify-between items-center mb-4">
      <h3 class="font-semibold text-gray-800 dark:text-gray-100">{{ title }}</h3>
    </div>
    
    <!-- Chart Component with ECharts -->
    <v-chart 
      :option="chartOptions" 
      style="height: 350px" 
      autoresize
      @click="handleDrillDown"
    />

    <!-- Drill-down Modal Simulasi -->
    <div v-if="selectedPoint" class="mt-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border dark:border-gray-700">
      <div class="flex justify-between items-center mb-2">
        <h4 class="text-sm font-bold dark:text-white">Detail Drill-down: {{ selectedPoint.category }}</h4>
        <button @click="selectedPoint = null" class="text-red-500 text-xs">Tutup</button>
      </div>
      <p class="text-sm text-gray-600 dark:text-gray-400">
        Menampilkan tabel breakdown untuk nilai <strong>{{ selectedPoint.value }}</strong>. 
        (Di sini kamu bisa memanggil komponen DataTable dan request ke API backend Flask kamu berdasarkan kategori yang diklik).
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'

// Register ECharts components
use([
  CanvasRenderer,
  BarChart,
  PieChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
])

const props = defineProps<{
  title: string
  type: 'bar' | 'pie' | 'line' | 'area'
  seriesData: any[]
  categories: string[]
}>()

const selectedPoint = ref<any>(null)

// Konfigurasi ECharts
const chartOptions = computed(() => {
  const baseOption = {
    tooltip: {
      trigger: props.type === 'pie' ? 'item' : 'axis',
    },
    legend: {
      data: props.seriesData.map(s => s.name),
      textStyle: { color: '#9ca3af' },
    },
    color: ['#3b82f6', '#10b981', '#f59e0b'],
  }

  if (props.type === 'pie') {
    return {
      ...baseOption,
      series: [{
        type: 'pie',
        data: props.categories.map((cat, idx) => ({
          name: cat,
          value: props.seriesData[0]?.data[idx] || 0,
        })),
        radius: '60%',
        label: {
          color: '#9ca3af',
        },
      }],
    }
  }

  return {
    ...baseOption,
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: props.categories,
      axisLabel: { color: '#9ca3af' },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#9ca3af' },
    },
    series: props.seriesData.map(s => ({
      name: s.name,
      type: props.type === 'area' ? 'line' : props.type,
      data: s.data,
      smooth: props.type === 'line' || props.type === 'area',
      areaStyle: props.type === 'area' ? {} : undefined,
    })),
  }
})

function handleDrillDown(params: any) {
  if (params.componentType === 'series') {
    selectedPoint.value = {
      category: params.name || props.categories[params.dataIndex],
      value: params.value || params.data?.value,
    }
  }
}
</script>
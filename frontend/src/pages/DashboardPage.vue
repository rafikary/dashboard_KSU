<template>
  <div class="space-y-6">
    <!-- Modern KPI Cards with Gradient -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <div
        v-for="(metric, index) in metrics"
        :key="index"
        class="glass-card rounded-3xl p-6 hover-lift cursor-pointer"
        :style="{ animationDelay: `${index * 0.1}s` }"
      >
        <div class="flex items-start justify-between mb-4">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400 font-medium">{{ metric.label }}</p>
            <h3 class="text-3xl font-bold mt-2 bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
              {{ formatValue(metric.value, metric.format) }}
            </h3>
          </div>
          <div
            class="w-14 h-14 rounded-2xl flex items-center justify-center"
            :class="metric.color"
          >
            <n-icon :component="metric.icon" size="28" class="text-white" />
          </div>
        </div>
        
        <div class="flex items-center gap-2">
          <n-tag
            :type="metric.change >= 0 ? 'success' : 'error'"
            size="small"
            round
            class="font-semibold"
          >
            <template #icon>
              <n-icon :component="metric.change >= 0 ? TrendingUpOutline : TrendingDownOutline" />
            </template>
            {{ metric.change >= 0 ? '+' : '' }}{{ formatPercent(metric.change) }}
          </n-tag>
          <span class="text-xs text-gray-500 dark:text-gray-400">vs bulan lalu</span>
        </div>
      </div>
    </div>

    <!-- Welcome Section with Gradient -->
    <div class="glass-card rounded-3xl p-8 gradient-primary text-white overflow-hidden relative">
      <div class="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-32 -mt-32"></div>
      <div class="absolute bottom-0 left-0 w-48 h-48 bg-white/10 rounded-full -ml-24 -mb-24"></div>
      
      <div class="relative z-10">
        <h2 class="text-3xl font-bold mb-2">Selamat Datang di QL Dashboard! 🎉</h2>
        <p class="text-white/90 mb-6">
          Dashboard analytics modern dengan komponen yang cantik dan powerful
        </p>
        
        <div class="flex gap-4">
          <n-button
            type="default"
            size="large"
            round
            class="bg-white/20 hover:bg-white/30 backdrop-blur-sm border-white/30"
            @click="navigateTo('Customers')"
          >
            <template #icon>
              <n-icon :component="PeopleOutline" />
            </template>
            Lihat Customer
          </n-button>
          <n-button
            type="default"
            size="large"
            round
            class="bg-white/20 hover:bg-white/30 backdrop-blur-sm border-white/30"
            @click="navigateTo('Comparison')"
          >
            <template #icon>
              <n-icon :component="StatsChartOutline" />
            </template>
            Analisa Perbandingan
          </n-button>
        </div>
      </div>
    </div>

    <!-- Quick Stats -->
    <div class="glass-card rounded-3xl p-8">
      <h3 class="text-2xl font-bold mb-6 text-gray-900 dark:text-white">Fitur Unggulan</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="flex items-start gap-4 p-4 rounded-2xl hover:bg-indigo-50/50 dark:hover:bg-indigo-900/20 transition-colors">
          <div class="w-12 h-12 rounded-xl bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center flex-shrink-0">
            <n-icon :component="GridOutline" size="24" class="text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h4 class="font-semibold text-gray-800 dark:text-gray-200 mb-1">Interactive DataTable</h4>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              Table dengan sorting, filter, search, dan export to Excel/CSV
            </p>
          </div>
        </div>

        <div class="flex items-start gap-4 p-4 rounded-2xl hover:bg-purple-50/50 dark:hover:bg-purple-900/20 transition-colors">
          <div class="w-12 h-12 rounded-xl bg-purple-100 dark:bg-purple-900/50 flex items-center justify-center flex-shrink-0">
            <n-icon :component="SwapHorizontalOutline" size="24" class="text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h4 class="font-semibold text-gray-800 dark:text-gray-200 mb-1">Comparison Mode</h4>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              Bandingkan data antar periode dengan visualisasi yang cantik
            </p>
          </div>
        </div>

        <div class="flex items-start gap-4 p-4 rounded-2xl hover:bg-pink-50/50 dark:hover:bg-pink-900/20 transition-colors">
          <div class="w-12 h-12 rounded-xl bg-pink-100 dark:bg-pink-900/50 flex items-center justify-center flex-shrink-0">
            <n-icon :component="TrendingUpOutline" size="24" class="text-pink-600 dark:text-pink-400" />
          </div>
          <div>
            <h4 class="font-semibold text-gray-800 dark:text-gray-200 mb-1">Real-time Analytics</h4>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              Monitoring performa penjualan secara real-time
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NTag } from 'naive-ui'
import {
  CashOutline,
  CartOutline,
  PeopleOutline,
  TrendingUpOutline,
  TrendingDownOutline,
  StatsChartOutline,
  GridOutline,
  SwapHorizontalOutline,
} from '@vicons/ionicons5'

const router = useRouter()

const metrics = ref([
  {
    label: 'Total Omzet',
    value: 2500000000,
    change: 13.6,
    format: 'currency',
    icon: CashOutline,
    color: 'gradient-primary',
  },
  {
    label: 'Total Transaksi',
    value: 1250,
    change: 5.9,
    format: 'number',
    icon: CartOutline,
    color: 'gradient-success',
  },
  {
    label: 'Customer Aktif',
    value: 342,
    change: 4.3,
    format: 'number',
    icon: PeopleOutline,
    color: 'bg-gradient-to-br from-pink-500 to-rose-500',
  },
  {
    label: 'Avg. Transaksi',
    value: 2000000,
    change: 7.3,
    format: 'currency',
    icon: TrendingUpOutline,
    color: 'bg-gradient-to-br from-amber-500 to-orange-500',
  },
])

function formatValue(value: number, format?: string) {
  if (format === 'currency') {
    if (value >= 1e9) return `Rp ${(value / 1e9).toFixed(1)} M`
    if (value >= 1e6) return `Rp ${(value / 1e6).toFixed(1)} Jt`
    return `Rp ${value.toLocaleString('id-ID')}`
  }
  return value.toLocaleString('id-ID')
}

function formatPercent(value: number) {
  return `${Math.abs(value).toFixed(1)}%`
}

function navigateTo(name: string) {
  router.push({ name })
}
</script>

<style scoped>
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.glass-card {
  animation: slideUp 0.5s ease-out forwards;
}
</style>

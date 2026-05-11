<template>
  <div class="min-h-screen transition-colors duration-300" :class="{ 'dark': isDark }">
    <n-layout has-sider class="min-h-screen" :style="{ background: isDark ? '#111827' : '#f9fafb' }">
      
      <!-- Modern Glassmorphism Sidebar -->
      <n-layout-sider
        bordered
        collapse-mode="width"
        :collapsed-width="80"
        :width="280"
        :native-scrollbar="false"
        show-trigger
        v-model:collapsed="collapsed"
        :inverted="isDark"
        class="glass-sidebar"
        :style="{ 
          background: isDark ? 'rgba(31, 41, 55, 0.95)' : 'rgba(255, 255, 255, 0.9)',
          borderRight: isDark ? '1px solid rgba(75, 85, 99, 0.5)' : '1px solid rgba(229, 231, 235, 0.5)'
        }"
      >
        <div class="py-8" :class="collapsed ? 'px-4' : 'px-6'">
          
          <!-- Logo with gradient -->
          <div class="flex items-center gap-3 mb-8 transition-all duration-300" :class="{ 'justify-center': collapsed }">
            <div class="w-12 h-12 rounded-2xl gradient-primary flex items-center justify-center shadow-lg shrink-0" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);">
              <span class="text-2xl font-bold text-white">QL</span>
            </div>
            <div class="flex-1 overflow-hidden whitespace-nowrap" v-show="!collapsed">
              <h1 class="text-xl font-bold" :class="isDark ? 'text-white' : 'bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent'">
                QL Dashboard
              </h1>
              <p class="text-xs" :class="isDark ? 'text-gray-400' : 'text-gray-500'">Sales Analytics</p>
            </div>
          </div>

          <!-- Modern Navigation Menu -->
          <n-menu
            :value="activeKey"
            :options="menuOptions"
            @update:value="handleMenuClick"
            :collapsed="collapsed"
            :collapsed-width="64"
            :indent="20"
            class="custom-menu"
          />
        </div>
      </n-layout-sider>

      <!-- Main Content Area -->
      <n-layout :style="{ background: 'transparent' }">
        
        <!-- Modern Header with Glass Effect -->
        <n-layout-header 
          bordered 
          class="glass-header px-8 py-4"
          :style="{ 
            background: isDark ? 'rgba(17, 24, 39, 0.8)' : 'rgba(255, 255, 255, 0.8)',
            borderBottom: isDark ? '1px solid rgba(75, 85, 99, 0.5)' : '1px solid rgba(229, 231, 235, 0.5)',
            backdropFilter: 'blur(20px)'
          }"
        >
          <div class="flex items-center justify-between">
            <div class="flex-1">
              <h2 class="text-2xl font-bold transition-colors" :class="isDark ? 'text-white' : 'text-gray-800'">{{ pageTitle }}</h2>
              <p class="text-sm mt-1 transition-colors" :class="isDark ? 'text-gray-400' : 'text-gray-500'">{{ pageDescription }}</p>
            </div>
            
            <div class="flex items-center gap-4">
              <!-- Search -->
              <n-input
                placeholder="Cari data..."
                class="w-64 hidden md:flex"
                round
              >
                <template #prefix>
                  <n-icon :component="SearchOutline" />
                </template>
              </n-input>

              <!-- Dark Mode Toggle with Animation -->
              <n-button circle quaternary class="hover-lift dark-mode-toggle" @click="toggleDark()">
                <template #icon>
                  <n-icon 
                    :component="isDark ? SunnyOutline : MoonOutline" 
                    size="20" 
                    :class="[
                      'transition-all duration-300',
                      isDark ? 'text-yellow-400 rotate-180' : 'text-gray-700 rotate-0'
                    ]" 
                  />
                </template>
              </n-button>

              <!-- Notifications -->
              <n-badge :value="3" :max="9" dot>
                <n-button circle quaternary class="hover-lift">
                  <template #icon>
                    <n-icon :component="NotificationsOutline" size="20" class="dark:text-gray-300" />
                  </template>
                </n-button>
              </n-badge>

              <!-- User Avatar -->
              <n-dropdown :options="userOptions" @select="handleUserSelect">
                <n-avatar
                  round
                  size="large"
                  class="cursor-pointer hover-lift ml-2"
                  style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);"
                >
                  <span class="text-white font-semibold">A</span>
                </n-avatar>
              </n-dropdown>
            </div>
          </div>
        </n-layout-header>

        <!-- Content with beautiful spacing -->
        <n-layout-content class="p-8 bg-transparent">
          <div class="animate-fade-in">
            <router-view />
          </div>
        </n-layout-content>
      </n-layout>
    </n-layout>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useDark, useToggle } from '@vueuse/core'
import {
  NLayout,
  NLayoutSider,
  NLayoutHeader,
  NLayoutContent,
  NMenu,
  NInput,
  NButton,
  NIcon,
  NAvatar,
  NBadge,
  NDropdown,
  type MenuOption,
} from 'naive-ui'
import {
  HomeOutline,
  TrendingUpOutline,
  SwapHorizontalOutline,
  PeopleOutline,
  GridOutline,
  MapOutline,
  MegaphoneOutline,
  WarningOutline,
  StatsChartOutline,
  ChatbubbleOutline,
  DocumentTextOutline,
  SearchOutline,
  NotificationsOutline,
  PersonOutline,
  SettingsOutline,
  LogOutOutline,
  MoonOutline,
  SunnyOutline
} from '@vicons/ionicons5'

// State for Sidebar & Dark Mode
const collapsed = ref(false)
const isDark = useDark()
const toggleDark = useToggle(isDark)

const router = useRouter()
const route = useRoute()

const activeKey = computed(() => route.name as string)

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    Dashboard: 'Dashboard',
    Customers: 'Data Customer',
    Comparison: 'Perbandingan Penjualan',
  }
  return titles[activeKey.value] || 'Dashboard'
})

const pageDescription = computed(() => {
  const descriptions: Record<string, string> = {
    Dashboard: 'Overview performa penjualan Anda',
    Customers: 'Kelola dan monitor performa customer',
    Comparison: 'Analisa perbandingan multi-periode',
  }
  return descriptions[activeKey.value] || ''
})

function renderIcon(icon: any) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions: MenuOption[] = [
  { label: 'Dashboard', key: 'Dashboard', icon: renderIcon(HomeOutline) },
  { label: 'Analisa Penjualan', key: 'sales', icon: renderIcon(TrendingUpOutline) },
  { label: 'Perbandingan', key: 'Comparison', icon: renderIcon(SwapHorizontalOutline) },
  { label: 'Data Customer', key: 'Customers', icon: renderIcon(PeopleOutline) },
  { label: 'Analisa Kategori', key: 'categories', icon: renderIcon(GridOutline) },
  { label: 'Geografis', key: 'geography', icon: renderIcon(MapOutline) },
  { label: 'Marketing', key: 'marketing', icon: renderIcon(MegaphoneOutline) },
  { label: 'Customer Menurun', key: 'declining', icon: renderIcon(WarningOutline) },
  { label: 'Kualitas Data', key: 'data-quality', icon: renderIcon(StatsChartOutline) },
  { label: 'AI Chatbot', key: 'chatbot', icon: renderIcon(ChatbubbleOutline) },
  { label: 'Laporan', key: 'reports', icon: renderIcon(DocumentTextOutline) },
]

const userOptions = [
  { label: 'Profile', key: 'profile', icon: renderIcon(PersonOutline) },
  { label: 'Settings', key: 'settings', icon: renderIcon(SettingsOutline) },
  { type: 'divider', key: 'd1' },
  { label: 'Logout', key: 'logout', icon: renderIcon(LogOutOutline) },
]

function handleMenuClick(key: string) {
  router.push({ name: key })
}

function handleUserSelect(key: string) {
  if (key === 'logout') {
    console.log('Logout')
  }
}
</script>

<style scoped>
/* Dark mode toggle animation */
.dark-mode-toggle {
  position: relative;
  overflow: hidden;
}

.dark-mode-toggle::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.2) 0%, transparent 70%);
  transform: translate(-50%, -50%);
  transition: width 0.6s ease, height 0.6s ease;
}

.dark-mode-toggle:active::before {
  width: 200%;
  height: 200%;
}

/* Menu Item Styling */
:deep(.n-menu-item-content) {
  border-radius: 12px !important;
  margin: 4px 8px;
  font-weight: 500;
  transition: all 0.3s ease;
}

:deep(.n-menu-item-content:hover) {
  transform: translateX(4px);
}

/* Fix Active State Text Color & Background */
:deep(.n-menu-item-content.n-menu-item-content--selected) {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

/* Target Header text inside Naive UI Menu */
:deep(.n-menu-item-content.n-menu-item-content--selected .n-menu-item-content-header) {
  color: white !important;
}

/* Target Icon inside Naive UI Menu */
:deep(.n-menu-item-content.n-menu-item-content--selected .n-menu-item-content__icon) {
  color: white !important;
}

/* Target Icon inside Naive UI Menu */
:deep(.n-menu-item-content.n-menu-item-content--selected .n-menu-item-content__icon) {
  color: white !important;
}

/* Adjust Naive UI default text colors for dark mode if not using n-config-provider */
:global(.dark) :deep(.n-menu-item-content-header) {
  color: #e5e7eb; /* gray-200 */
}

:global(.dark) :deep(.n-menu-item-content__icon) {
  color: #9ca3af; /* gray-400 */
}

.hover-lift {
  transition: transform 0.2s ease;
}
.hover-lift:hover {
  transform: translateY(-2px);
}
</style>
<template>
  <div class="min-h-screen transition-colors duration-300 ksu-shell" :class="{ 'dark': isDark }">
    <n-layout :has-sider="!isMobile" class="min-h-screen app-frame" :style="{ background: isDark ? '#0b1220' : '#eef3fb' }">
      
      <!-- Modern Glassmorphism Sidebar -->
      <n-layout-sider
        v-if="!isMobile"
        bordered
        collapse-mode="width"
        :collapsed-width="76"
        :width="280"
        :native-scrollbar="false"
        v-model:collapsed="collapsed"
        :inverted="isDark"
        class="sidebar-panel fixed-sidebar"
        :style="{ 
          background: isDark ? 'linear-gradient(180deg, #0f1a2b 0%, #0b1320 100%)' : 'linear-gradient(180deg, #f8fbff 0%, #f1f6fe 100%)',
          borderRight: isDark ? '1px solid rgba(148, 163, 184, 0.15)' : '1px solid rgba(148, 163, 184, 0.28)'
        }"
      >
        <div class="relative h-full flex flex-col">
          <!-- Sidebar Content -->
          <div class="flex-1 py-7 overflow-y-auto overflow-x-hidden" :class="collapsed ? 'px-2' : 'px-5'">
            
            <!-- Logo with gradient -->
            <div class="brand-block flex items-center gap-3 mb-7 transition-all duration-300" :class="{ 'justify-center': collapsed }">
              <div class="w-11 h-11 rounded-xl flex items-center justify-center shadow-lg shrink-0 brand-mark">
                <span class="text-lg font-black text-white tracking-wide">QL</span>
              </div>
              <div class="flex-1 min-w-0 brand-text" v-show="!collapsed">
                <h1 class="brand-title" :class="isDark ? 'text-slate-100' : 'text-slate-800'">
                  KSU
                </h1>
                <p class="brand-subtitle" :class="isDark ? 'text-slate-400' : 'text-slate-500'">KOPERASI SIMPAN PINJAM</p>
              </div>
            </div>

            <!-- Modern Navigation Menu -->
            <n-menu
              :value="activeKey"
              :options="menuOptions"
              @update:value="handleMenuClick"
              :collapsed="collapsed"
              :collapsed-width="76"
              :indent="collapsed ? 0 : 20"
              class="custom-menu menu-surface w-full"
              :class="{ 'menu-collapsed': collapsed }"
            />
          </div>

          <!-- Custom Collapse Toggle Button -->
          <!-- <div class="collapse-trigger-container" :class="collapsed ? 'px-2' : 'px-5'">
            <n-button
              quaternary
              class="collapse-btn w-full"
              @click="collapsed = !collapsed"
              :title="collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'"
            >
              <template #icon>
                <n-icon
                  :component="collapsed ? MenuOutline : CloseOutline"
                  :class="['transition-transform duration-300', { 'rotate-0': !collapsed, 'rotate-180': collapsed }]"
                />
              </template>
              <span v-if="!collapsed" class="ml-2 text-sm font-medium">
                {{ collapsed ? 'Expand' : 'Collapse' }}
              </span>
            </n-button>
          </div> -->
        </div>
      </n-layout-sider>

      <n-drawer
        v-model:show="mobileMenuOpen"
        placement="left"
        :width="284"
        :trap-focus="true"
        :auto-focus="false"
        :show-mask="true"
      >
        <n-drawer-content body-content-style="padding: 0;">
          <div
            class="h-full overflow-y-auto overflow-x-hidden px-5 py-7"
            :style="{
              background: isDark ? 'linear-gradient(180deg, #0f1a2b 0%, #0b1320 100%)' : 'linear-gradient(180deg, #f8fbff 0%, #f1f6fe 100%)'
            }"
          >
            <div class="brand-block flex items-center gap-3 mb-7 transition-all duration-300">
              <div class="w-11 h-11 rounded-xl flex items-center justify-center shadow-lg shrink-0 brand-mark">
                <span class="text-lg font-black text-white tracking-wide">QL</span>
              </div>
              <div class="flex-1 min-w-0 brand-text">
                <h1 class="brand-title" :class="isDark ? 'text-slate-100' : 'text-slate-800'">KSU</h1>
                <p class="brand-subtitle" :class="isDark ? 'text-slate-400' : 'text-slate-500'">KOPERASI SIMPAN PINJAM</p>
              </div>
            </div>

            <n-menu
              :value="activeKey"
              :options="menuOptions"
              @update:value="handleMenuClick"
              :indent="20"
              class="menu-surface w-full"
            />
          </div>
        </n-drawer-content>
      </n-drawer>

      <!-- Main Content Area -->
      <n-layout :style="{ background: 'transparent' }" class="main-panel">
        
        <!-- Modern Header with Glass Effect -->
        <n-layout-header
          bordered 
          class="top-header px-5 md:px-8 py-4 md:py-5"
          :style="{ 
            background: isDark ? 'rgba(13, 23, 38, 0.82)' : 'rgba(255, 255, 255, 0.76)',
            borderBottom: isDark ? '1px solid rgba(148, 163, 184, 0.2)' : '1px solid rgba(148, 163, 184, 0.3)',
            backdropFilter: 'blur(20px)'
          }"
        >
          <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div class="flex-1 min-w-0">
              <div class="flex items-start gap-3">
                <n-button
                  v-if="isMobile"
                  circle
                  quaternary
                  class="control-btn mt-1"
                  @click="mobileMenuOpen = true"
                >
                  <template #icon>
                    <n-icon :component="MenuOutline" size="20" />
                  </template>
                </n-button>

                <div class="min-w-0">
              <p class="text-[0.66rem] md:text-[0.72rem] font-semibold uppercase tracking-[0.18em] md:tracking-[0.22em]" :class="isDark ? 'text-sky-300/90' : 'text-sky-700/85'">Ringkasan Kinerja</p>
              <h2 class="text-[1.45rem] md:text-[2.1rem] font-black tracking-tight leading-tight transition-colors" :class="isDark ? 'text-slate-100' : 'text-slate-800'">{{ pageTitle }}</h2>
              <p class="text-sm mt-1 transition-colors" :class="isDark ? 'text-slate-400' : 'text-slate-500'">{{ pageDescription }}</p>
                </div>
              </div>
            </div>
            
            <div class="flex items-center gap-2 md:gap-3 flex-wrap md:flex-nowrap">
              <!-- Search -->
              <n-input
                placeholder="Cari data..."
                class="w-52 lg:w-64 hidden md:flex"
                round
              >
                <template #prefix>
                  <n-icon :component="SearchOutline" />
                </template>
              </n-input>

              <!-- Dark Mode Toggle with Animation -->
              <n-button circle quaternary class="hover-lift dark-mode-toggle control-btn" @click="toggleDark()">
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
                <n-button circle quaternary class="hover-lift control-btn">
                  <template #icon>
                    <n-icon :component="NotificationsOutline" size="20" class="dark:text-slate-300" />
                  </template>
                </n-button>
              </n-badge>

              <!-- User Avatar -->
              <n-dropdown :options="userOptions" @select="handleUserSelect">
                <n-avatar
                  round
                  size="large"
                  class="cursor-pointer hover-lift ml-2"
                  style="background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);"
                >
                  <span class="text-white font-semibold">A</span>
                </n-avatar>
              </n-dropdown>
            </div>
          </div>
        </n-layout-header>

        <!-- Content with beautiful spacing -->
        <n-layout-content class="px-4 md:px-8 py-6 md:py-8 bg-transparent content-scroll">
          <div class="animate-fade-in">
            <router-view />
          </div>
        </n-layout-content>
      </n-layout>
    </n-layout>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { breakpointsTailwind, useBreakpoints, useDark, useToggle } from '@vueuse/core'
import {
  NLayout,
  NLayoutSider,
  NLayoutHeader,
  NLayoutContent,
  NDrawer,
  NDrawerContent,
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
  SunnyOutline,
  MenuOutline,
  CloseOutline,
  BusinessOutline
} from '@vicons/ionicons5'

// State for Sidebar & Dark Mode
const collapsed = ref(false)
const mobileMenuOpen = ref(false)
const isDark = useDark()
const toggleDark = useToggle(isDark)
const breakpoints = useBreakpoints(breakpointsTailwind)
const isMobile = breakpoints.smaller('md')

const router = useRouter()
const route = useRoute()

const activeKey = computed(() => route.name as string)

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    Dashboard: 'Dashboard KSU',
    Branches: 'Data Cabang',
  }
  return titles[activeKey.value] || 'Dashboard'
})

const pageDescription = computed(() => {
  const descriptions: Record<string, string> = {
    Dashboard: 'Overview kesehatan keuangan KSU',
    Branches: 'Monitor performa cabang dan NPL (pinjaman menunggak >3 bulan)',
  }
  return descriptions[activeKey.value] || ''
})

function renderIcon(icon: any) {
  return () =>
    h(
      'span',
      { class: 'menu-icon-wrap inline-flex items-center justify-center w-5 h-5' },
      [h(NIcon, { size: 20 }, { default: () => h(icon) })]
    )
}

const menuOptions: MenuOption[] = [
  { label: 'Dashboard', key: 'Dashboard', icon: renderIcon(HomeOutline), show: true },
  { label: 'Data Cabang', key: 'Branches', icon: renderIcon(BusinessOutline), show: true },
  // Disabled menu items (not relevant for KSU):
  // { label: 'Analisa Penjualan', key: 'sales', icon: renderIcon(TrendingUpOutline) },
  // { label: 'Perbandingan', key: 'Comparison', icon: renderIcon(SwapHorizontalOutline) },
  // { label: 'Data Customer', key: 'Customers', icon: renderIcon(PeopleOutline) },
  // { label: 'Analisa Kategori', key: 'categories', icon: renderIcon(GridOutline) },
  // { label: 'Geografis', key: 'geography', icon: renderIcon(MapOutline) },
  // { label: 'Marketing', key: 'marketing', icon: renderIcon(MegaphoneOutline) },
  // { label: 'Customer Menurun', key: 'declining', icon: renderIcon(WarningOutline) },
  // { label: 'Kualitas Data', key: 'data-quality', icon: renderIcon(StatsChartOutline) },
  // { label: 'AI Chatbot', key: 'chatbot', icon: renderIcon(ChatbubbleOutline) },
  // { label: 'Laporan', key: 'reports', icon: renderIcon(DocumentTextOutline) },
]

const userOptions = [
  { label: 'Profile', key: 'profile', icon: renderIcon(PersonOutline) },
  { label: 'Settings', key: 'settings', icon: renderIcon(SettingsOutline) },
  { type: 'divider', key: 'd1' },
  { label: 'Logout', key: 'logout', icon: renderIcon(LogOutOutline) },
]

function handleMenuClick(key: string) {
  router.push({ name: key })
  if (isMobile.value) {
    mobileMenuOpen.value = false
  }
}

function handleUserSelect(key: string) {
  if (key === 'logout') {
    console.log('Logout')
  }
}

watch(
  () => route.fullPath,
  () => {
    mobileMenuOpen.value = false
  }
)

watch(isMobile, (mobile) => {
  if (!mobile) {
    mobileMenuOpen.value = false
  }
})
</script>

<style scoped>
:global(body) {
  font-family: 'Poppins', 'Segoe UI', sans-serif;
}

.ksu-shell {
  background:
    radial-gradient(800px 360px at -120px -100px, rgba(14, 165, 233, 0.16), transparent 60%),
    radial-gradient(600px 300px at 105% -60px, rgba(59, 130, 246, 0.14), transparent 58%);
}

.app-frame {
  height: 100vh;
  overflow: hidden;
}

.sidebar-panel {
  box-shadow: 14px 0 26px rgba(15, 23, 42, 0.08);
}

.fixed-sidebar {
  height: 100vh;
  position: sticky;
  top: 0;
}

.main-panel {
  height: 100vh;
  overflow: hidden;
}

:deep(.main-panel > .n-layout-scroll-container) {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.content-scroll {
  flex: 1;
  overflow: hidden;
  min-height: 0;
  overscroll-behavior: contain;
}

:deep(.content-scroll > .n-layout-scroll-container) {
  height: 100%;
  min-height: 0;
  overflow-y: auto;
}

.brand-block {
  padding: 0.72rem 0.78rem;
  border-radius: 0.9rem;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(255, 255, 255, 0.42);
}

.brand-text {
  overflow: visible;
}

.brand-title {
  font-size: 1.72rem;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.012em;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand-subtitle {
  margin-top: 0.34rem;
  font-size: 0.56rem;
  letter-spacing: 0.18em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

:global(.dark) .brand-block {
  background: rgba(30, 41, 59, 0.34);
  border-color: rgba(148, 163, 184, 0.2);
}

.brand-mark {
  background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
}

.menu-surface {
  padding-top: 0.45rem;
}

/* Custom Collapse Button */
.collapse-trigger-container {
  padding-top: 0.75rem;
  padding-bottom: 1rem;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
}

:global(.dark) .collapse-trigger-container {
  border-top-color: rgba(148, 163, 184, 0.08);
}

.collapse-btn {
  border-radius: 10px;
  transition: all 0.3s ease;
  padding: 0.65rem 1rem;
  font-weight: 500;
}

.collapse-btn:hover {
  background: rgba(56, 189, 248, 0.1);
  transform: translateY(-1px);
}

:global(.dark) .collapse-btn:hover {
  background: rgba(56, 189, 248, 0.08);
}

.top-header {
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.control-btn {
  border: 1px solid rgba(148, 163, 184, 0.26);
}

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
  border-radius: 13px !important;
  margin: 4px 8px;
  font-weight: 500;
  transition: all 0.3s ease;
  min-height: 46px;
}

:deep(.n-menu-item-content:hover) {
  transform: translateX(3px);
  background: rgba(56, 189, 248, 0.12);
}

:deep(.menu-collapsed.n-menu) {
  display: flex;
  flex-direction: column;
  align-items: center;
}

:deep(.menu-collapsed .n-menu-item) {
  width: 100%;
  display: flex;
  justify-content: center;
  padding-left: 0.25rem !important;
  padding-right: 0.25rem !important;
}

:deep(.menu-collapsed .n-menu-item-content) {
  width: 100%;
  height: 3rem;
  min-height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  max-width: 3rem;
  margin: 0.5rem auto !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.menu-collapsed .n-menu-item-content:hover) {
  transform: none;
}

:deep(.menu-collapsed .n-menu-item-content__icon) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: auto;
  height: auto;
  margin-right: 0 !important;
  margin-left: 0 !important;
}

:deep(.menu-collapsed .n-menu-item-content__icon .n-icon) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

:deep(.menu-collapsed .n-menu-item-content.n-menu-item-content--selected) {
  width: 100%;
  max-width: 3rem;
}

/* Fix Active State Text Color & Background */
:deep(.n-menu-item-content.n-menu-item-content--selected) {
  background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important;
  font-weight: 600;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.28);
}

/* Target Header text inside Naive UI Menu */
:deep(.n-menu-item-content.n-menu-item-content--selected .n-menu-item-content-header) {
  color: white !important;
}

/* Target Icon inside Naive UI Menu */
:deep(.n-menu-item-content.n-menu-item-content--selected .n-menu-item-content__icon) {
  color: white !important;
}

/* Adjust Naive UI default text colors for dark mode if not using n-config-provider */
:global(.dark) :deep(.n-menu-item-content-header) {
  color: #dbeafe;
}

:global(.dark) :deep(.n-menu-item-content__icon) {
  color: #94a3b8;
}

.hover-lift {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.hover-lift:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(15, 23, 42, 0.14);
}

@media (max-width: 768px) {
  .brand-block {
    padding: 0.62rem 0.68rem;
    border-radius: 0.85rem;
  }

  .brand-title {
    font-size: 1.08rem;
  }

  .brand-subtitle {
    font-size: 0.52rem;
    letter-spacing: 0.12em;
  }
}
</style>
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/pages/DashboardPage.vue'),
      },
      {
        path: 'branches',
        name: 'Branches',
        component: () => import('@/pages/BranchesPage.vue'),
      },
      // Disabled old routes (not relevant for KSU):
      // {
      //   path: 'customers',
      //   name: 'Customers',
      //   component: () => import('@/pages/CustomersPage.vue'),
      // },
      // {
      //   path: 'comparison',
      //   name: 'Comparison',
      //   component: () => import('@/pages/SalesComparisonPage.vue'),
      // },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

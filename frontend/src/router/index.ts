import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { crumbs: ['Dashboard'] },
  },
  {
    path: '/charts',
    name: 'charts',
    component: () => import('@/views/ChartsView.vue'),
    meta: { crumbs: ['Charts'] },
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('@/views/HistoryView.vue'),
    meta: { crumbs: ['History'] },
  },
  {
    path: '/analysis/:id',
    name: 'analysis-detail',
    component: () => import('@/views/AnalysisDetailView.vue'),
    meta: { crumbs: ['History', 'Analysis'] },
  },
  {
    path: '/notifications',
    name: 'notifications',
    component: () => import('@/views/NotificationsView.vue'),
    meta: { crumbs: ['Notifications'] },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { crumbs: ['Settings'] },
  },
  {
    path: '/strategy',
    name: 'strategy',
    component: () => import('@/views/StrategyView.vue'),
    meta: { crumbs: ['Strategy'] },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()
  if (to.meta.guest) {
    if (auth.isAuthenticated) {
      next('/')
    } else {
      next()
    }
  } else {
    if (!auth.isAuthenticated) {
      next('/login')
    } else {
      next()
    }
  }
})

export default router

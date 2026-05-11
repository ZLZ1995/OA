import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { pinia } from '@/store/pinia'
import AppLayout from '@/layout/AppLayout.vue'

function detectRouterBase() {
  const configured = import.meta.env.VITE_ROUTER_BASE as string | undefined
  if (configured) {
    return configured
  }
  return window.location.pathname.startsWith('/frontend/') ? '/frontend/' : '/'
}

const routes: RouteRecordRaw[] = [
  { path: '/login', component: () => import('@/views/auth/LoginView.vue') },
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', redirect: '/login' },
      { path: 'dashboard', redirect: '/workbench' },
      { path: 'workbench', component: () => import('@/views/dashboard/HomeView.vue') },
      { path: 'projects', component: () => import('@/views/projects/ProjectListView.vue') },
      { path: 'projects/:id', component: () => import('@/views/projects/ProjectDetailView.vue') },
      { path: 'projects/:id/flow', component: () => import('@/views/projects/ProjectFlowView.vue') },
      { path: 'workorders', component: () => import('@/views/workorders/WorkOrderListView.vue') },
      { path: 'workorders/:id', component: () => import('@/views/workorders/WorkOrderDetailView.vue') },
      { path: 'reviews', component: () => import('@/views/reviews/ReviewHandleView.vue') },
      { path: 'report-versions', component: () => import('@/views/report-versions/ReportVersionView.vue') },
      { path: 'project-members', component: () => import('@/views/project-members/ProjectMemberView.vue') },
      { path: 'print-room', component: () => import('@/views/printroom/PrintRoomHandleView.vue') },
      { path: 'finance', component: () => import('@/views/finance/FinanceView.vue') },
      { path: 'archives', component: () => import('@/views/archives/ArchiveView.vue') },
      { path: 'project-exports', component: () => import('@/views/exports/ProjectExportView.vue') },
      { path: 'accounts', component: () => import('@/views/accounts/AccountManageView.vue') }
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/login' }
]

const router = createRouter({
  history: createWebHistory(detectRouterBase()),
  routes
})

router.beforeEach(async (to) => {
  const auth = useAuthStore(pinia)

  try {
    if (to.path === '/login') {
      return true
    }

    if (!auth.isLoggedIn) {
      return `/login?redirect=${encodeURIComponent(to.fullPath)}`
    }

    const profile = await auth.ensureUserLoaded()
    if (!profile) {
      return `/login?redirect=${encodeURIComponent(to.fullPath)}`
    }
    const isAdmin = (profile.roles || []).includes('ADMIN')
    const adminPaths = ['/accounts', '/project-exports', '/workbench']
    if (adminPaths.includes(to.path) && !isAdmin) return '/dashboard'
    if (!adminPaths.includes(to.path) && isAdmin) return '/accounts'
    return true
  } catch {
    auth.clearAuth()
    return '/login'
  }
})

export default router

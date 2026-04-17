import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { pinia } from '@/store/pinia'
import AppLayout from '@/layout/AppLayout.vue'

const routes: RouteRecordRaw[] = [
  { path: '/login', component: () => import('@/views/auth/LoginView.vue') },
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: () => import('@/views/dashboard/HomeView.vue') },
      { path: 'projects', component: () => import('@/views/projects/ProjectListView.vue') },
      { path: 'projects/:id', component: () => import('@/views/projects/ProjectDetailView.vue') },
      { path: 'workorders', component: () => import('@/views/workorders/WorkOrderListView.vue') },
      { path: 'workorders/:id', component: () => import('@/views/workorders/WorkOrderDetailView.vue') },
      { path: 'reviews', component: () => import('@/views/reviews/ReviewHandleView.vue') },
      { path: 'report-versions', component: () => import('@/views/report-versions/ReportVersionView.vue') },
      { path: 'project-members', component: () => import('@/views/project-members/ProjectMemberView.vue') },
      { path: 'print-room', component: () => import('@/views/printroom/PrintRoomHandleView.vue') },
      { path: 'finance', component: () => import('@/views/finance/FinanceView.vue') },
      { path: 'archives', component: () => import('@/views/archives/ArchiveView.vue') },
      { path: 'accounts', component: () => import('@/views/accounts/AccountManageView.vue') }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const auth = useAuthStore(pinia)

  if (to.path === '/login') {
    return true
  }

  if (!auth.isLoggedIn) {
    return '/login'
  }

  const profile = await auth.ensureUserLoaded()
  if (!profile) {
    return '/login'
  }

  return true
})

export default router

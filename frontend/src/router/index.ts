import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/store/auth'
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
      { path: 'print-room', component: () => import('@/views/printroom/PrintRoomHandleView.vue') },
      { path: 'accounts', component: () => import('@/views/accounts/AccountManageView.vue') }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.isLoggedIn) {
    return '/login'
  }
  if (to.path === '/login' && auth.isLoggedIn) {
    return '/dashboard'
  }
  return true
})

export default router

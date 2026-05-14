<template>
  <div class="menu-wrapper">
    <div class="menu-brand">
      <div class="brand-badge">中勤</div>
      <div>
        <strong>项目工作台</strong>
        <span>流程管理系统</span>
      </div>
    </div>
    <el-menu :default-active="active" class="menu" router>
      <el-menu-item v-for="item in visibleMenus" :key="item.key" :index="item.path">
        <span>{{ item.title }}</span>
        <el-badge
          v-if="item.key === 'notifications' && unreadCount > 0"
          :value="unreadCount"
          :max="99"
          class="menu-badge"
        />
      </el-menu-item>
    </el-menu>
    <div class="logout-zone">
      <el-button type="danger" plain class="logout-btn" @click="onLogout">退出登录</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { getUnreadNotificationCount } from '@/api/notifications'

const BUSINESS_MENUS = [{ key: 'dashboard', title: '项目工作台', path: '/workbench' }]
const SHARED_MENUS = [{ key: 'notifications', title: '消息中心', path: '/notifications' }]
const ADMIN_MENUS = [
  { key: 'accounts', title: '账号管理', path: '/accounts' },
  { key: 'termination-approvals', title: '终止/废止审核', path: '/termination-approvals' },
  { key: 'project-delete-approvals', title: '项目删除审核', path: '/project-delete-approvals' },
  { key: 'project-conflicts', title: '项目冲突提醒', path: '/project-conflicts' },
  { key: 'project-exports', title: '项目清单导出', path: '/project-exports' }
]

defineProps<{ compact?: boolean }>()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isAdmin = computed(() => (auth.user?.roles || []).includes('ADMIN'))
const visibleMenus = computed(() => (isAdmin.value ? [...SHARED_MENUS, ...ADMIN_MENUS] : [...BUSINESS_MENUS, ...SHARED_MENUS]))
const active = computed(() => route.path)
const unreadCount = ref(0)

async function loadUnreadCount() {
  try {
    unreadCount.value = await getUnreadNotificationCount()
  } catch {
    unreadCount.value = 0
  }
}

function onLogout() {
  auth.clearAuth()
  router.push('/login')
}

watch(() => route.fullPath, () => {
  void loadUnreadCount()
})

onMounted(() => {
  void loadUnreadCount()
})
</script>

<style scoped>
.menu-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.menu-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 76px;
  padding: 14px 12px;
  border-bottom: 1px solid var(--zq-border-soft);
}

.brand-badge {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 8px;
  color: #fff;
  background: var(--zq-primary);
  font-size: 13px;
  font-weight: 700;
}

.menu-brand strong,
.menu-brand span {
  display: block;
  line-height: 1.4;
}

.menu-brand strong {
  font-size: 14px;
  color: var(--zq-text);
}

.menu-brand span {
  font-size: 12px;
  color: var(--zq-muted);
}

.menu {
  flex: 1;
  overflow: auto;
  border-right: 0;
}

.menu :deep(.el-menu-item) {
  height: 44px;
  margin: 6px 10px;
  border-radius: 6px;
  color: #475569;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.menu :deep(.el-menu-item.is-active) {
  color: var(--zq-primary);
  background: var(--zq-primary-soft);
}

.menu :deep(.el-menu-item.is-active::before) {
  content: "";
  width: 3px;
  height: 20px;
  position: absolute;
  left: 0;
  border-radius: 999px;
  background: var(--zq-primary);
}

.logout-zone {
  padding: 12px;
  border-top: 1px solid var(--zq-border-soft);
}

.logout-btn {
  width: 100%;
}

.menu-badge {
  margin-left: 10px;
}
</style>

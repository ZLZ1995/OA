<template>
  <div class="menu-wrapper">
    <el-menu :default-active="active" class="menu" router>
      <el-menu-item v-for="item in APP_MENUS" :key="item.key" :index="item.path">{{ item.title }}</el-menu-item>
    </el-menu>
    <div class="logout-zone">
      <el-button type="danger" plain class="logout-btn" @click="onLogout">退出登录</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { APP_MENUS } from '@/constants/menus'
import { useAuthStore } from '@/store/auth'

defineProps<{ compact?: boolean }>()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const active = computed(() => route.path)

function onLogout() {
  auth.clearAuth()
  router.push('/login')
}
</script>

<style scoped>
.menu-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.menu {
  flex: 1;
  overflow: auto;
}

.logout-zone {
  padding: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.logout-btn {
  width: 100%;
}
</style>

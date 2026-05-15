<template>
  <div class="account-bar">
    <el-dropdown trigger="click" @command="handleCommand">
      <button class="account-trigger" type="button">
        <span class="account-name">{{ displayName }}</span>
        <el-icon class="account-arrow"><ArrowDown /></el-icon>
      </button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="switch">切换账号</el-dropdown-item>
          <el-dropdown-item command="logout">退出登录</el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
    <SwitchAccountDialog v-model="switchVisible" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { clearSession } from '@/api/authSession'
import SwitchAccountDialog from '@/components/auth/SwitchAccountDialog.vue'

const router = useRouter()
const auth = useAuthStore()
const switchVisible = ref(false)

const displayName = computed(() => auth.user?.real_name || auth.user?.username || '当前账号')

onMounted(() => {
  auth.ensureUserLoaded()
})

async function handleCommand(command: string) {
  if (command === 'switch') {
    switchVisible.value = true
    return
  }

  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('退出后将返回登录页，是否继续？', '退出登录', {
        type: 'warning',
        confirmButtonText: '退出登录',
        cancelButtonText: '取消',
      })
    } catch {
      return
    }

    await clearSession({ silent: true })
    await router.push('/login')
  }
}
</script>

<style scoped>
.account-bar {
  display: flex;
  align-items: center;
}

.account-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--zq-border);
  border-radius: 999px;
  color: var(--zq-text);
  background: rgba(255, 255, 255, 0.92);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.account-trigger:hover {
  border-color: rgba(31, 78, 121, 0.35);
  box-shadow: 0 8px 18px rgba(31, 78, 121, 0.08);
  transform: translateY(-1px);
}

.account-name {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
}

.account-arrow {
  font-size: 12px;
  color: var(--zq-muted);
}
</style>

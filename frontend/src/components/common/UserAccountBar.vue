<template>
  <div class="account-bar">
    <el-dropdown trigger="click" @command="handleCommand">
      <button class="account-trigger" type="button">
        <span class="account-name">{{ displayName }}</span>
        <el-icon class="account-arrow"><ArrowDown /></el-icon>
      </button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item v-if="canSwitchWorkspace" command="workspace">
            切换工作区
          </el-dropdown-item>
          <el-dropdown-item command="switch">切换账号</el-dropdown-item>
          <el-dropdown-item command="logout">退出登录</el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
    <SwitchAccountDialog v-model="switchVisible" />
    <el-dialog
      v-model="workspaceVisible"
      title="切换工作区"
      width="420px"
      :close-on-click-modal="false"
    >
      <p class="workspace-tip">请选择进入管理员工作区或业务工作区。</p>
      <template #footer>
        <el-button type="primary" :disabled="workspace.currentWorkspace === 'admin'" @click="switchWorkspace('admin')">
          进入管理员工作区
        </el-button>
        <el-button :disabled="workspace.currentWorkspace === 'business'" @click="switchWorkspace('business')">
          进入业务工作区
        </el-button>
      </template>
    </el-dialog>
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
import { type WorkspaceMode, useWorkspaceStore } from '@/store/workspace'

const router = useRouter()
const auth = useAuthStore()
const workspace = useWorkspaceStore()
const switchVisible = ref(false)
const workspaceVisible = ref(false)

const displayName = computed(() => auth.user?.real_name || auth.user?.username || '当前账号')
const canSwitchWorkspace = computed(() => workspace.supportsWorkspaceChoice(auth.user?.roles || []))

onMounted(() => {
  auth.ensureUserLoaded()
})

async function switchWorkspace(mode: WorkspaceMode) {
  workspace.setWorkspace(mode)
  workspaceVisible.value = false
  await router.replace(mode === 'admin' ? '/accounts' : '/workbench')
}

async function handleCommand(command: string) {
  if (command === 'workspace') {
    workspaceVisible.value = true
    return
  }

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

.workspace-tip {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}
</style>

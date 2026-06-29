<template>
  <header class="desktop-shell-bar">
    <div class="desktop-shell-bar__brand">
      <span class="desktop-shell-bar__title">中勤评估业务OA系统</span>
      <span class="desktop-shell-bar__meta" v-if="session.activeAccount">
        当前账号：{{ session.activeAccount.displayName || session.activeAccount.username }}
      </span>
    </div>

    <div class="desktop-shell-bar__actions">
      <el-select
        v-model="activeAccountId"
        class="desktop-shell-bar__select"
        placeholder="选择账号"
        :disabled="loading || session.accounts.length === 0"
        @change="onAccountChange"
      >
        <el-option
          v-for="account in session.accounts"
          :key="account.accountId"
          :label="`${account.displayName || account.username} (${account.username})`"
          :value="account.accountId"
        />
      </el-select>

      <el-segmented
        v-if="workspaceOptions.length > 0"
        v-model="workspaceKey"
        :options="workspaceOptions"
        @change="onWorkspaceChange"
      />

      <el-button class="desktop-shell-bar__button" @click="navigateHome">
        返回首页
      </el-button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

type DesktopAccount = {
  accountId: string
  userId: number
  username: string
  displayName: string
  roles: string[]
  accessToken: string
  workspaceKey: 'admin' | 'business' | ''
  lastRoute: string
}

type SessionState = {
  accounts: DesktopAccount[]
  activeAccountId: string
  activeAccount: DesktopAccount | null
  currentRoute: string
  workspaceKey: 'admin' | 'business' | ''
  currentUserId: number | null
}

const loading = ref(false)
const activeAccountId = ref('')
const workspaceKey = ref<'admin' | 'business' | ''>('')
const session = reactive<SessionState>({
  accounts: [],
  activeAccountId: '',
  activeAccount: null,
  currentRoute: '',
  workspaceKey: '',
  currentUserId: null,
})

const workspaceOptions = computed(() => {
  const roles = session.activeAccount?.roles || []
  const hasAdminRole = roles.includes('ADMIN')
  const hasBusinessRole = roles.some(role => role !== 'ADMIN')
  const options: Array<{ label: string; value: 'admin' | 'business' }> = []

  if (hasBusinessRole) {
    options.push({ label: '业务工作区', value: 'business' })
  }
  if (hasAdminRole) {
    options.push({ label: '管理员工作区', value: 'admin' })
  }

  return options
})

function applySnapshot(snapshot: SessionState | null | undefined) {
  if (!snapshot) {
    return
  }

  session.accounts = snapshot.accounts || []
  session.activeAccountId = snapshot.activeAccountId || ''
  session.activeAccount = snapshot.activeAccount || null
  session.currentRoute = snapshot.currentRoute || ''
  session.workspaceKey = snapshot.workspaceKey || ''
  session.currentUserId = snapshot.currentUserId ?? null

  activeAccountId.value = session.activeAccountId
  workspaceKey.value = session.workspaceKey
}

async function refreshSessionState() {
  const snapshot = await window.desktopApp?.getSessionState?.()
  applySnapshot(snapshot as SessionState)
}

async function onAccountChange(accountId: string) {
  if (!accountId) {
    return
  }

  loading.value = true
  try {
    const snapshot = await window.desktopApp?.activateAccount?.(accountId)
    applySnapshot(snapshot as SessionState)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '切换账号失败')
    await refreshSessionState()
  } finally {
    loading.value = false
  }
}

async function onWorkspaceChange(value: 'admin' | 'business') {
  loading.value = true
  try {
    const snapshot = await window.desktopApp?.setWorkspace?.(value)
    applySnapshot(snapshot as SessionState)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '切换工作区失败')
    await refreshSessionState()
  } finally {
    loading.value = false
  }
}

async function navigateHome() {
  const fallbackPath = workspaceKey.value === 'admin' ? '/accounts' : '/workbench'
  loading.value = true
  try {
    const snapshot = await window.desktopApp?.navigateRoute?.(fallbackPath)
    applySnapshot(snapshot as SessionState)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '跳转失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void refreshSessionState()
})
</script>

<style scoped>
.desktop-shell-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 18px;
  border-bottom: 1px solid rgba(212, 221, 231, 0.92);
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(8px);
}

.desktop-shell-bar__brand {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.desktop-shell-bar__title {
  color: #102a43;
  font-size: 16px;
  font-weight: 700;
}

.desktop-shell-bar__meta {
  color: #5b6b7f;
  font-size: 12px;
}

.desktop-shell-bar__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.desktop-shell-bar__select {
  width: 240px;
}

.desktop-shell-bar__button {
  min-width: 96px;
}

@media (max-width: 1100px) {
  .desktop-shell-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .desktop-shell-bar__actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>

import { ElMessage } from 'element-plus'
import { logout } from '@/api/auth'
import { clearAgentSession, clearLocalAgentSessionId } from '@/api/oaAgent'
import { useNotificationStore } from '@/store/notification'
import { useAuthStore } from '@/store/auth'

export async function clearSession(options?: { silent?: boolean }) {
  const auth = useAuthStore()
  const notifications = useNotificationStore()

  try {
    await clearAgentSession()
    await logout()
  } catch {
    if (!options?.silent) {
      ElMessage.warning('退出接口调用失败，已清理本地登录状态')
    }
  } finally {
    clearLocalAgentSessionId()
    notifications.disconnectSocket()
    notifications.stopPolling()
    auth.clearAuth()
  }
}

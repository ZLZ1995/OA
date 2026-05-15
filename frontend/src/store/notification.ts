import { defineStore } from 'pinia'
import { getNotificationStats } from '@/api/notifications'

const ACTIVE_POLL_INTERVAL_MS = 15000
const IDLE_POLL_INTERVAL_MS = 30000
const SOCKET_FALLBACK_POLL_INTERVAL_MS = 60000
const SOCKET_RECONNECT_BASE_MS = 3000
const SOCKET_RECONNECT_MAX_MS = 30000

type NotificationStats = {
  today_new_count: number
  unread_count: number
  today_reminder_count: number
  read_rate: number
  avg_process_duration_seconds: number
  latest_notification_id: number | null
  server_time: string
}

type RealtimePayload =
  | {
      event: 'hello'
      user_id: number
      connected_at: string
    }
  | {
      event: 'notification_created'
      notification_id: number
      user_id: number
      message_type: string
      biz_type: string
      project_id: number | null
      work_order_id: number | null
      created_at: string
    }
  | {
      event: 'notification_read'
      notification_ids: number[]
      user_id: number
      read_at: string
    }

function buildDefaultStats(): NotificationStats {
  return {
    today_new_count: 0,
    unread_count: 0,
    today_reminder_count: 0,
    read_rate: 0,
    avg_process_duration_seconds: 0,
    latest_notification_id: null,
    server_time: '',
  }
}

function buildWebSocketUrl() {
  const configuredApiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim()
  const normalizedApiBaseUrl = configuredApiBaseUrl
    ? configuredApiBaseUrl.replace(/\/+$/, '')
    : `${window.location.origin}/api/v1`
  return `${normalizedApiBaseUrl.replace(/^http/i, 'ws')}/ws/notifications`
}

let pollTimer: number | null = null
let reconnectTimer: number | null = null
let socket: WebSocket | null = null
let reconnectAttempts = 0

export const useNotificationStore = defineStore('notification', {
  state: () => ({
    stats: buildDefaultStats(),
    unreadCount: 0,
    latestNotificationId: null as number | null,
    listRefreshToken: 0,
    pollingEnabled: false,
    socketEnabled: false,
    socketStatus: 'disconnected' as 'disconnected' | 'connecting' | 'connected',
  }),
  actions: {
    async refreshStats() {
      const stats = await getNotificationStats()
      this.stats = stats
      this.unreadCount = stats.unread_count
      this.latestNotificationId = stats.latest_notification_id
      return stats
    },
    markListDirty() {
      this.listRefreshToken += 1
    },
    getPollInterval() {
      if (this.socketStatus === 'connected') {
        return SOCKET_FALLBACK_POLL_INTERVAL_MS
      }
      return document.hidden ? IDLE_POLL_INTERVAL_MS : ACTIVE_POLL_INTERVAL_MS
    },
    scheduleNextPoll(delayMs?: number) {
      if (!this.pollingEnabled) return
      if (pollTimer) {
        window.clearTimeout(pollTimer)
      }
      const interval = typeof delayMs === 'number' ? delayMs : this.getPollInterval()
      pollTimer = window.setTimeout(() => {
        void this.pollOnce()
      }, interval)
    },
    async pollOnce() {
      if (!this.pollingEnabled) return
      const previousLatestId = this.latestNotificationId
      try {
        const stats = await this.refreshStats()
        if (stats.latest_notification_id !== previousLatestId) {
          this.markListDirty()
        }
      } finally {
        this.scheduleNextPoll()
      }
    },
    handleVisibilityChange() {
      if (!this.pollingEnabled) return
      this.scheduleNextPoll(document.hidden ? IDLE_POLL_INTERVAL_MS : 0)
    },
    startPolling() {
      if (this.pollingEnabled) return
      this.pollingEnabled = true
      document.addEventListener('visibilitychange', this.handleVisibilityChange)
      void this.refreshStats()
      this.scheduleNextPoll(0)
    },
    stopPolling() {
      this.pollingEnabled = false
      document.removeEventListener('visibilitychange', this.handleVisibilityChange)
      if (pollTimer) {
        window.clearTimeout(pollTimer)
        pollTimer = null
      }
    },
    connectSocket() {
      if (this.socketEnabled) return
      this.socketEnabled = true
      reconnectAttempts = 0
      this.openSocket()
    },
    disconnectSocket() {
      this.socketEnabled = false
      this.socketStatus = 'disconnected'
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
      if (socket) {
        socket.close()
        socket = null
      }
    },
    openSocket() {
      const token = localStorage.getItem('access_token')
      if (!this.socketEnabled || !token) return
      this.socketStatus = 'connecting'
      const url = new URL(buildWebSocketUrl())
      url.searchParams.set('token', token)
      socket = new WebSocket(url.toString())
      socket.onopen = () => {
        reconnectAttempts = 0
        this.socketStatus = 'connected'
        void this.refreshStats()
      }
      socket.onmessage = (event) => {
        this.handleSocketMessage(event.data)
      }
      socket.onclose = () => {
        socket = null
        this.socketStatus = 'disconnected'
        if (this.socketEnabled) {
          this.scheduleReconnect()
        }
      }
      socket.onerror = () => {
        socket?.close()
      }
    },
    scheduleReconnect() {
      if (!this.socketEnabled) return
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer)
      }
      const delayMs = Math.min(SOCKET_RECONNECT_BASE_MS * 2 ** reconnectAttempts, SOCKET_RECONNECT_MAX_MS)
      reconnectAttempts += 1
      reconnectTimer = window.setTimeout(() => {
        this.openSocket()
      }, delayMs)
    },
    handleSocketMessage(rawData: string) {
      try {
        const payload = JSON.parse(rawData) as RealtimePayload
        if (payload.event === 'hello') {
          return
        }
        this.markListDirty()
        void this.refreshStats()
      } catch {
        // Ignore malformed payloads and rely on polling fallback.
      }
    },
    applyReadState(notificationIds: number[]) {
      if (!notificationIds.length) return
      this.unreadCount = Math.max(0, this.unreadCount - notificationIds.length)
      this.stats = {
        ...this.stats,
        unread_count: this.unreadCount,
      }
      this.markListDirty()
    },
  },
})

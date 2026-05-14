import http from './http'

export interface NotificationItem {
  id: number
  biz_type: string
  biz_id: number
  title: string
  content: string
  message_type: string
  priority: string
  sender_user_id?: number | null
  sender_user_name?: string | null
  project_id?: number | null
  project_code?: string | null
  project_name?: string | null
  client_name?: string | null
  work_order_id?: number | null
  work_order_no?: string | null
  work_order_title?: string | null
  current_status?: string | null
  current_handler_user_id?: number | null
  current_handler_user_name?: string | null
  process_status: string
  cc_flag: boolean
  receiver_user_name?: string | null
  group_key?: string | null
  link_type?: string | null
  link_target_id?: number | null
  is_read: boolean
  popup_flag: boolean
  created_at: string
}

export interface NotificationTimelineItem {
  event_type: string
  title: string
  operator_user_name?: string | null
  status?: string | null
  created_at: string
  remark?: string | null
}

export interface NotificationListParams {
  tab?: 'all' | 'unread' | 'read' | 'initiated' | 'cc'
  keyword?: string
  message_type?: string
  priority?: string
  read_status?: 'READ' | 'UNREAD'
  project_id?: number
  work_order_id?: number
  page?: number
  page_size?: number
}

export async function listMyNotifications(params: NotificationListParams = {}) {
  const { data } = await http.get('/notifications/mine', { params })
  return data as { items: NotificationItem[]; total: number; page: number; page_size: number }
}

export async function markNotificationRead(id: number) {
  const { data } = await http.post(`/notifications/${id}/read`)
  return data as { message: string }
}

export async function batchMarkNotificationRead(notificationIds: number[]) {
  const { data } = await http.post('/notifications/read/batch', { notification_ids: notificationIds })
  return data as { message: string }
}

export async function getNotificationStats() {
  const { data } = await http.get('/notifications/stats')
  return data as {
    today_new_count: number
    unread_count: number
    today_reminder_count: number
    read_rate: number
    avg_process_duration_seconds: number
  }
}

export async function getNotificationDetail(id: number) {
  const { data } = await http.get(`/notifications/${id}`)
  return data as NotificationItem
}

export async function getNotificationTimeline(id: number) {
  const { data } = await http.get(`/notifications/${id}/timeline`)
  return data as {
    items: NotificationTimelineItem[]
  }
}

export async function getUnreadNotificationCount() {
  const result = await listMyNotifications()
  return result.items.filter(item => !item.is_read).length
}

import http from './http'

export interface NotificationItem {
  id: number
  biz_type: string
  biz_id: number
  title: string
  content: string
  link_type?: string | null
  link_target_id?: number | null
  is_read: boolean
  popup_flag: boolean
  created_at: string
}

export async function listMyNotifications() {
  const { data } = await http.get('/notifications/mine')
  return data as { items: NotificationItem[] }
}

export async function markNotificationRead(id: number) {
  const { data } = await http.post(`/notifications/${id}/read`)
  return data as { message: string }
}

export async function getUnreadNotificationCount() {
  const result = await listMyNotifications()
  return result.items.filter(item => !item.is_read).length
}

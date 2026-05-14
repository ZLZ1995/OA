import http from './http'

export interface ReminderEligibilityData {
  can_remind: boolean
  reason_code?: string | null
  reason_message?: string | null
  current_handler_user_id?: number | null
  current_handler_name?: string | null
  elapsed_seconds: number
  remaining_seconds_to_48h: number
  today_remind_count: number
  remaining_seconds_to_next_remind: number
  current_status?: string | null
}

export interface ReminderHistoryItem {
  reminder_event_id: number
  project_id: number
  work_order_id: number
  work_order_no?: string | null
  current_status: string
  initiator_user_id: number
  initiator_user_name?: string | null
  current_handler_user_id: number
  current_handler_user_name?: string | null
  overdue_seconds: number
  comment?: string | null
  day_remind_seq: number
  created_at: string
  primary_read_status: string
  primary_read_at?: string | null
  delivery_status: string
}

export async function getReminderEligibility(workOrderId: number) {
  const { data } = await http.get('/reminders/eligibility', { params: { work_order_id: workOrderId } })
  return data as ReminderEligibilityData
}

export async function createReminder(payload: { work_order_id: number; comment?: string }) {
  const { data } = await http.post('/reminders', payload)
  return data as { reminder_event_id: number; today_remind_count: number; message: string }
}

export async function listWorkOrderReminders(workOrderId: number) {
  const { data } = await http.get(`/reminders/work-orders/${workOrderId}`)
  return data as { items: ReminderHistoryItem[] }
}

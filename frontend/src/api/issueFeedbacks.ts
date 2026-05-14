import http from './http'

export type IssueFeedbackStatus = 'PENDING' | 'RESOLVED' | 'TECH_SUPPORT'

export interface IssueFeedbackItem {
  id: number
  project_no: string
  process_step: string
  detail: string
  status: IssueFeedbackStatus
  submitter_user_id: number
  submitter_user_name: string
  submitter_username: string
  created_at: string
  handled_by_name?: string | null
  handled_at?: string | null
  suspended_by_name?: string | null
  suspended_at?: string | null
  suspend_note?: string | null
}

export async function createIssueFeedback(payload: {
  project_no: string
  process_step: string
  detail: string
}) {
  const { data } = await http.post('/issue-feedbacks', payload)
  return data as IssueFeedbackItem
}

export async function listIssueFeedbacks() {
  const { data } = await http.get('/issue-feedbacks')
  return data as { items: IssueFeedbackItem[] }
}

export async function getIssueFeedback(id: number) {
  const { data } = await http.get(`/issue-feedbacks/${id}`)
  return data as IssueFeedbackItem
}

export async function resolveIssueFeedback(id: number) {
  const { data } = await http.post(`/issue-feedbacks/${id}/resolve`)
  return data as IssueFeedbackItem
}

export async function suspendIssueFeedback(id: number, suspendNote?: string) {
  const { data } = await http.post(`/issue-feedbacks/${id}/suspend`, { suspend_note: suspendNote || undefined })
  return data as IssueFeedbackItem
}

export async function exportTechSupportFeedbacksExcel() {
  const { data } = await http.get('/issue-feedbacks/tech-support/excel', { responseType: 'blob' })
  const url = window.URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = `需技术支持问题反馈-${new Date().toISOString().slice(0, 10)}.xlsx`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

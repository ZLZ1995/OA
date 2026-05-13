import http from './http'

export interface ReportMailingRecordItem {
  id: number
  work_order_id: number
  project_id: number
  action_type: string
  operator_user_id: number
  operator_user_name?: string | null
  receiver_name?: string | null
  receiver_phone?: string | null
  receiver_address?: string | null
  receiver_remark?: string | null
  express_no?: string | null
  status: string
  invalidated_express_no?: string | null
  created_at: string
}

export async function listReportMailingRecords(workOrderId: number) {
  const { data } = await http.get(`/report-mailing/work-orders/${workOrderId}`)
  return data as { items: ReportMailingRecordItem[] }
}

export async function startReportMailing(workOrderId: number) {
  const { data } = await http.post(`/report-mailing/work-orders/${workOrderId}/start`)
  return data as { message: string }
}

export async function submitReportMailing(workOrderId: number, payload: {
  receiver_name: string
  receiver_phone: string
  receiver_address: string
  receiver_remark?: string
}) {
  const { data } = await http.post(`/report-mailing/work-orders/${workOrderId}/submit`, payload)
  return data as ReportMailingRecordItem
}

export async function submitReportMailingExpress(workOrderId: number, payload: { express_no: string }) {
  const { data } = await http.post(`/report-mailing/work-orders/${workOrderId}/print-room`, payload)
  return data as ReportMailingRecordItem
}

export async function confirmReportMailing(workOrderId: number, payload?: { remark?: string }) {
  const { data } = await http.post(`/report-mailing/work-orders/${workOrderId}/confirm`, payload || {})
  return data as { message: string }
}

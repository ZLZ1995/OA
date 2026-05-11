import http from './http'

export interface ReportVersionItem {
  id: number
  work_order_id: number
  version_no: number
  file_id: number
  submitted_by: number
  submit_stage: string
  created_at: string
}

export async function listReportVersions(workOrderId: number) {
  const { data } = await http.get('/report-versions', { params: { work_order_id: workOrderId } })
  return data as { items: ReportVersionItem[] }
}

export async function createReportVersion(payload: { work_order_id: number; file_id: number; submit_stage: string }) {
  const { data } = await http.post('/report-versions', payload)
  return data as ReportVersionItem
}

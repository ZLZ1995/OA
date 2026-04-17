import http from './http'

export async function issueOfficialContract(payload: {
  work_order_id: number
  contract_no: string
  remark?: string
}) {
  const { data } = await http.post('/print-room/issue-official-contract', payload)
  return data as { message: string }
}

export interface PrintRoomRecordItem {
  id: number
  work_order_id: number
  handled_by: number
  paper_report_no: string
  copy_count: number
  printed_at?: string
  remark?: string
}

export async function issuePaperReport(payload: {
  work_order_id: number
  paper_report_no: string
  copy_count: number
  remark?: string
}) {
  const { data } = await http.post('/print-room/issue-paper-report', payload)
  return data as PrintRoomRecordItem
}

import http from './http'

export async function issueOfficialContract(payload: {
  work_order_id: number
  contract_no: string
  remark?: string
}) {
  const { data } = await http.post('/print-room/issue-official-contract', payload)
  return data as { message: string }
}

export interface PrintRoomInfoItem {
  work_order_id: number
  contract_no?: string | null
  paper_report_no?: string | null
  copy_count?: number | null
  formal_report_count?: number | null
  remark?: string | null
}

export async function getPrintRoomInfo(workOrderId: number) {
  const { data } = await http.get(`/print-room/work-orders/${workOrderId}`)
  return data as PrintRoomInfoItem
}

export async function transferPrintRoom(payload: { work_order_id: number; handler_user_id: number; remark?: string }) {
  const { data } = await http.post('/print-room/transfer-print-room', payload)
  return data as { message: string }
}

export async function rollbackThird(payload: { work_order_id: number; remark?: string }) {
  const { data } = await http.post('/print-room/rollback-third', payload)
  return data as { message: string }
}

export async function markContractError(payload: { work_order_id: number; remark?: string }) {
  const { data } = await http.post('/print-room/contract-error', payload)
  return data as { message: string }
}

export async function reportError(payload: { work_order_id: number; remark?: string }) {
  const { data } = await http.post('/print-room/report-error', payload)
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

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
  current_status?: string | null
  current_status_display?: string | null
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

export interface PrintRoomContractParticipant {
  user_id?: number | null
  user_name?: string | null
}

export interface PrintRoomContractFileItem {
  id: number
  origin_file_name: string
  file_size?: number | null
  uploaded_at?: string | null
  uploaded_by_user_id?: number | null
  uploaded_by_user_name?: string | null
  is_current: boolean
}

export interface ContractPrintRoomInfoItem {
  work_order_id: number
  current_status?: string | null
  current_status_display?: string | null
  project_leader: PrintRoomContractParticipant
  contract_reviewer: PrintRoomContractParticipant
  print_room_handler: PrintRoomContractParticipant
  original_contract_files: PrintRoomContractFileItem[]
  stamped_contract_scan_files: PrintRoomContractFileItem[]
  can_upload_scan: boolean
  can_send_to_project_leader: boolean
  can_return_to_print_room: boolean
  can_confirm_complete: boolean
}

export async function getContractPrintRoomInfo(workOrderId: number) {
  const { data } = await http.get(`/print-room/contracts/work-orders/${workOrderId}`)
  return data as ContractPrintRoomInfoItem
}

export async function sendContractToProjectLeader(payload: { work_order_id: number; remark?: string }) {
  const { data } = await http.post('/print-room/contracts/send-to-project-leader', payload)
  return data as { message: string }
}

export async function returnContractToPrintRoom(payload: { work_order_id: number; remark: string }) {
  const { data } = await http.post('/print-room/contracts/return-to-print-room', payload)
  return data as { message: string }
}

export async function confirmContractComplete(payload: { work_order_id: number; remark?: string }) {
  const { data } = await http.post('/print-room/contracts/confirm-complete', payload)
  return data as { message: string }
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

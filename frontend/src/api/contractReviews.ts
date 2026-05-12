import http from './http'
import type { WorkOrderFileItem } from './files'

export interface ContractReviewRecordItem {
  id: number
  work_order_id: number
  project_id: number
  action_type: 'SUBMIT_CONTRACT' | 'APPROVE_CONTRACT' | 'REJECT_CONTRACT'
  operator_user_id: number
  operator_user_name?: string | null
  reviewer_user_id: number
  reviewer_user_name?: string | null
  comment?: string | null
  contract_file_id?: number | null
  review_attachment_file_id?: number | null
  contract_file?: Pick<WorkOrderFileItem, 'id' | 'origin_file_name' | 'file_size' | 'uploaded_at'> | null
  review_attachment_file?: Pick<WorkOrderFileItem, 'id' | 'origin_file_name' | 'file_size' | 'uploaded_at'> | null
  created_at: string
}

export async function listContractReviewRecords(workOrderId: number) {
  const { data } = await http.get('/contract-reviews', { params: { work_order_id: workOrderId } })
  return data as { items: ContractReviewRecordItem[] }
}

export async function submitContractReview(payload: {
  work_order_id: number
  reviewer_user_id: number
  comment?: string
}) {
  const { data } = await http.post('/contract-reviews/submit', payload)
  return data as ContractReviewRecordItem
}

export async function approveContractReview(recordId: number, payload: { comment?: string; review_attachment_file_id?: number }) {
  const { data } = await http.post(`/contract-reviews/${recordId}/approve`, payload)
  return data as ContractReviewRecordItem
}

export async function rejectContractReview(recordId: number, payload: { comment?: string; review_attachment_file_id?: number }) {
  const { data } = await http.post(`/contract-reviews/${recordId}/reject`, payload)
  return data as ContractReviewRecordItem
}

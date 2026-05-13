import http from './http'
import type { ContractReviewRecordItem } from './contractReviews'

export interface ProjectUpdateLogItem {
  id: number
  operator_user_id: number
  operator_user_name?: string | null
  changed_fields: string
  created_at: string
}

export interface ProjectFlowData {
  project: {
    id: number
    project_no: string
    project_name: string
    client_name: string
    undertaking_unit: string
    report_type?: string | null
    valuation_base_date?: string | null
    business_salesman?: string | null
    project_amount?: number | null
    project_source: 'INTERNAL' | 'EXTERNAL'
    project_source_display: string
    external_project_leader_name?: string | null
    project_leader_display_name?: string | null
    contract_no?: string | null
    report_no?: string | null
    first_reviewer_name?: string | null
    second_reviewer_name?: string | null
    third_reviewer_name?: string | null
    print_room_handler_name?: string | null
    invoice_handler_name?: string | null
    archive_reviewer_name?: string | null
    mailing_handler_name?: string | null
    current_step: string
    status_display: string
  }
  current_work_order_id?: number
  current_work_order_status?: string | null
  current_handler_user_id?: number | null
  contract_reviewer_id?: number | null
  contract_reviewer_name?: string | null
  contract_review_status?: string | null
  contract_review_status_display?: string | null
  first_reviewer_id?: number | null
  second_reviewer_id?: number | null
  third_reviewer_id?: number | null
  signer_one?: string | null
  signer_two?: string | null
  formal_report_count?: number | null
  print_room_handler_id?: number | null
  archive_reviewer_id?: number | null
  archive_submitter_id?: number | null
  archive_submission_type?: string | null
  mailing_handler_user_id?: number | null
  mailing_status?: string | null
  user_role_in_project: string
  available_action: string
  can_operate: boolean
  flow_steps: string[]
  contract_review_records: ContractReviewRecordItem[]
  project_update_logs: ProjectUpdateLogItem[]
  review_submit_locked?: boolean
  review_submit_lock_reason?: string | null
  duplicate_delete_required?: boolean
}

export async function getProjectFlow(projectId: number | string) {
  const { data } = await http.get(`/projects/${projectId}/flow`)
  return data as ProjectFlowData
}

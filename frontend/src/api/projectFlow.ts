import http from './http'

export interface ProjectFlowData {
  project: {
    id: number
    project_no: string
    project_name: string
    client_name: string
    undertaking_unit: string
    current_step: string
    status_display: string
  }
  current_work_order_id?: number
  current_work_order_status?: string | null
  current_handler_user_id?: number | null
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
  user_role_in_project: string
  available_action: string
  can_operate: boolean
  flow_steps: string[]
}

export async function getProjectFlow(projectId: number | string) {
  const { data } = await http.get(`/projects/${projectId}/flow`)
  return data as ProjectFlowData
}

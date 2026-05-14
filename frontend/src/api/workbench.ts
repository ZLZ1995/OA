import http from './http'

export interface WorkbenchProjectItem {
  id: number
  project_no: string
  project_name: string
  client_name: string
  project_leader_name?: string | null
  transfer_user_name?: string | null
  current_step: string
  status_display: string
  todo_action?: string | null
  termination_status?: string | null
  termination_reason?: string | null
  delete_request_status?: string | null
  delete_request_id?: number | null
  delete_request_reason?: string | null
  delete_approver_user_id?: number | null
  delete_approver_user_name?: string | null
  delete_requester_user_name?: string | null
  delete_requested_at?: string | null
  can_edit: boolean
  can_delete: boolean
  can_archive: boolean
  can_request_termination: boolean
  can_approve_termination: boolean
  can_approve_delete?: boolean
  can_enter: boolean
  is_reminded?: boolean
  remind_count_today?: number
  latest_remind_at?: string | null
}

export async function getWorkbench() {
  const { data } = await http.get('/workbench')
  return data as { my_projects: WorkbenchProjectItem[]; todo_projects: WorkbenchProjectItem[] }
}

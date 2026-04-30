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
  user_role_in_project: string
  available_action: string
  can_operate: boolean
  flow_steps: string[]
}

export async function getProjectFlow(projectId: number | string) {
  const { data } = await http.get(`/projects/${projectId}/flow`)
  return data as ProjectFlowData
}

import http from './http'

export interface ProjectItem {
  id: number
  project_code: string
  undertaking_unit: '中勤' | '中立国际' | '中众' | '其他'
  project_name: string
  client_name: string
  business_user_id: number
  project_leader_id: number
  status: string
  status_display: string
  archived_at?: string | null
  deleted_at?: string | null
}

export async function listProjects() {
  const { data } = await http.get('/projects')
  return data as { items: ProjectItem[] }
}

export async function createProject(payload: {
  project_code?: string
  undertaking_unit: '中勤' | '中立国际' | '中众' | '其他'
  project_name: string
  client_name: string
  business_user_id: number
  project_leader_id: number
}) {
  const { data } = await http.post('/projects', payload)
  return data as ProjectItem
}

export async function deleteProject(projectId: number) {
  await http.delete(`/projects/${projectId}`)
}

export async function archiveProject(projectId: number) {
  const { data } = await http.patch(`/projects/${projectId}/archive`)
  return data as ProjectItem
}

export async function listProjectOptions() {
  const { data } = await http.get('/projects/options')
  return data as { items: ProjectItem[] }
}


export async function generateProjectCode(undertakingUnit: '中勤' | '中立国际' | '中众' | '其他') {
  const { data } = await http.get('/projects/generate-code', { params: { undertaking_unit: undertakingUnit } })
  return data as { project_code: string }
}

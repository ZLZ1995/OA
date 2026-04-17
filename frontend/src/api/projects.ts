import http from './http'

export interface ProjectItem {
  id: number
  project_code: string
  project_name: string
  client_name: string
  business_user_id: number
  project_leader_id: number
  status: string
}

export async function listProjects() {
  const { data } = await http.get('/projects')
  return data as { items: ProjectItem[] }
}

export async function createProject(payload: {
  project_code: string
  project_name: string
  client_name: string
  business_user_id: number
  project_leader_id: number
}) {
  const { data } = await http.post('/projects', payload)
  return data as ProjectItem
}

export async function updateProject(
  projectId: number,
  payload: Partial<Pick<ProjectItem, 'project_name' | 'client_name' | 'status'>>
) {
  const { data } = await http.patch(`/projects/${projectId}`, payload)
  return data as ProjectItem
}

export async function deleteProject(projectId: number) {
  await http.delete(`/projects/${projectId}`)
}

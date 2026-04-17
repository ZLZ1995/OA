import http from './http'

export interface ProjectMemberItem {
  id: number
  project_id: number
  user_id: number
  member_role: string
  created_at: string
}

export async function listProjectMembers(projectId: number) {
  const { data } = await http.get('/project-members', { params: { project_id: projectId } })
  return data as { items: ProjectMemberItem[] }
}

export async function createProjectMember(payload: { project_id: number; user_id: number; member_role: string }) {
  const { data } = await http.post('/project-members', payload)
  return data as ProjectMemberItem
}

export async function deleteProjectMember(memberId: number) {
  await http.delete(`/project-members/${memberId}`)
}

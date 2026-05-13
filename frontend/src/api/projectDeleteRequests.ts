import http from './http'

export interface ProjectDeleteRequestItem {
  id: number
  project_id: number | null
  project_no: string
  project_name: string
  client_name: string
  current_step: string
  requester_user_id: number
  requester_user_name?: string | null
  approver_user_id: number
  approver_user_name?: string | null
  reason?: string | null
  status: string
  requested_at: string
  reviewed_at?: string | null
}

export async function listProjectDeleteRequests(status_filter?: string) {
  const { data } = await http.get('/project-delete-requests', { params: status_filter ? { status_filter } : {} })
  return data as { items: ProjectDeleteRequestItem[] }
}

export async function createProjectDeleteRequest(projectId: number, payload: { approver_user_id: number; reason?: string }) {
  const { data } = await http.post(`/project-delete-requests/projects/${projectId}`, payload)
  return data as ProjectDeleteRequestItem
}

export async function approveProjectDeleteRequest(requestId: number) {
  const { data } = await http.post(`/project-delete-requests/${requestId}/approve`)
  return data as { message: string }
}

export async function rejectProjectDeleteRequest(requestId: number) {
  const { data } = await http.post(`/project-delete-requests/${requestId}/reject`)
  return data as { message: string }
}

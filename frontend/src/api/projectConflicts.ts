import http from './http'

export interface ConflictProjectSnapshot {
  project_id: number
  project_no: string
  project_name: string
  client_name: string
  project_amount: number
  valuation_base_date: string
  project_leader_display_name: string
  creator_username?: string | null
  contract_uploaded_at: string
}

export interface ProjectConflictItem {
  id: number
  status: 'PENDING' | 'CONFIRMED' | 'RESOLVED'
  decision?: string | null
  kept_project_id?: number | null
  delete_project_id?: number | null
  resolve_comment?: string | null
  created_at: string
  decided_at?: string | null
  resolved_at?: string | null
  project_a: ConflictProjectSnapshot
  project_b: ConflictProjectSnapshot
}

export async function listProjectConflicts(status?: string) {
  const { data } = await http.get('/project-conflicts', { params: status ? { status } : {} })
  return data as { items: ProjectConflictItem[] }
}

export async function markProjectConflictNotConflict(id: number) {
  const { data } = await http.post(`/project-conflicts/${id}/not-conflict`)
  return data as ProjectConflictItem
}

export async function confirmProjectConflict(id: number, payload: { kept_project_id: number; comment: string }) {
  const { data } = await http.post(`/project-conflicts/${id}/confirm`, payload)
  return data as ProjectConflictItem
}

export async function exportProjectConflictsExcel(status?: string) {
  const { data } = await http.get('/project-conflicts/excel', {
    params: status ? { status } : {},
    responseType: 'blob'
  })
  const url = window.URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = `项目冲突提醒-${new Date().toISOString().slice(0, 10)}.xlsx`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

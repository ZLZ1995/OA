import http from './http'

export type ProjectUndertakingUnit = '中勤' | '中立国际' | '中众' | '其他'
export type EvaluationBusinessNature =
  | '国有资产评估业务'
  | '境外资产评估业务'
  | '证券期货评估业务'
  | '司法评估业务'
  | '金融资产评估业务'
  | '珠宝首饰评估业务'
  | '其他'
export type ReportType = '评估报告' | '估值报告' | '咨询报告' | '复核报告' | '追溯性报告'
export type ProjectSource = 'INTERNAL' | 'EXTERNAL'

export interface ProjectItem {
  id: number
  project_code: string
  undertaking_unit: ProjectUndertakingUnit
  project_name: string
  client_name: string
  evaluation_business_nature?: EvaluationBusinessNature | null
  report_type: ReportType
  valuation_base_date?: string | null
  business_salesman: string
  project_source: ProjectSource
  project_source_display: string
  external_project_leader_name?: string | null
  business_user_id: number
  project_leader_id: number
  project_leader_display_name?: string | null
  display_project_leader_name?: string | null
  status: string
  status_display: string
  contract_review_status?: string | null
  contract_review_status_display?: string | null
  termination_status?: string | null
  termination_reason?: string | null
  archived_at?: string | null
  deleted_at?: string | null
}

export interface ProjectUpdatePayload {
  project_name?: string
  client_name?: string
  undertaking_unit?: ProjectUndertakingUnit
  evaluation_business_nature?: EvaluationBusinessNature | null
  report_type?: ReportType
  valuation_base_date?: string | null
  business_salesman?: string
  project_amount?: number | null
  project_source?: ProjectSource
  external_project_leader_name?: string | null
}

export interface ProjectCreatePayload {
  project_code?: string
  undertaking_unit: ProjectUndertakingUnit
  project_name: string
  client_name: string
  evaluation_business_nature?: EvaluationBusinessNature | null
  report_type: ReportType
  valuation_base_date?: string | null
  business_salesman: string
  project_source: ProjectSource
  external_project_leader_name?: string | null
  business_user_id: number
  project_leader_id: number
}

export async function listProjects() {
  const { data } = await http.get('/projects')
  return data as { items: ProjectItem[] }
}

export async function getProject(projectId: number | string) {
  const { data } = await http.get(`/projects/${projectId}`)
  return data as ProjectItem
}

export async function createProject(payload: ProjectCreatePayload) {
  const { data } = await http.post('/projects', payload)
  return data as ProjectItem
}

export async function deleteProject(projectId: number) {
  await http.delete(`/projects/${projectId}`)
}

export async function deleteDuplicateProject(projectId: number) {
  await http.post(`/projects/${projectId}/duplicate-delete`)
}

export async function archiveProject(projectId: number) {
  const { data } = await http.patch(`/projects/${projectId}/archive`)
  return data as ProjectItem
}

export async function requestProjectTermination(projectId: number, reason: string) {
  const { data } = await http.post(`/projects/${projectId}/termination-request`, { reason })
  return data as ProjectItem
}

export async function approveProjectTermination(projectId: number) {
  const { data } = await http.post(`/projects/${projectId}/termination-approve`)
  return data as ProjectItem
}

export async function updateProject(projectId: number | string, payload: ProjectUpdatePayload) {
  const { data } = await http.patch(`/projects/${projectId}`, payload)
  return data as ProjectItem
}

export async function listProjectOptions() {
  const { data } = await http.get('/projects/options')
  return data as { items: ProjectItem[] }
}

export async function generateProjectCode(undertakingUnit: ProjectUndertakingUnit) {
  const { data } = await http.get('/projects/generate-code', { params: { undertaking_unit: undertakingUnit } })
  return data as { project_code: string }
}

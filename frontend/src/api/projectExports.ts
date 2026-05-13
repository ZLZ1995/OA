import http from './http'

export interface ProjectExportFilters {
  project_no?: string
  project_name?: string
  report_no?: string
  project_leader_name?: string
  undertaking_unit?: string
  signer_name?: string
  amount_min?: number
  amount_max?: number
  project_date_from?: string
  project_date_to?: string
  report_type?: string
  valuation_base_date_from?: string
  valuation_base_date_to?: string
  business_salesman?: string
  project_source?: 'INTERNAL' | 'EXTERNAL'
  external_project_leader_name?: string
}

export interface ProjectExportItem {
  project_id: number
  project_no: string
  project_name: string
  project_created_date: string
  project_progress: '进行中' | '已归档' | '已作废'
  report_no: string
  project_leader_name: string
  undertaking_unit: string
  report_type: string
  valuation_base_date: string
  business_salesman: string
  project_source: 'INTERNAL' | 'EXTERNAL'
  project_source_display: string
  external_project_leader_name: string
  amount: number | string
  signer_names: string
  first_reviewer_name: string
  second_reviewer_name: string
  third_reviewer_name: string
  archive_date: string
  delete_request_status?: string
  can_admin_delete?: boolean
}

function cleanFilters(filters: ProjectExportFilters) {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== undefined && value !== null && value !== '')
  )
}

export async function listProjectExportRows(filters: ProjectExportFilters) {
  const { data } = await http.get('/project-exports', { params: cleanFilters(filters) })
  return data as { items: ProjectExportItem[] }
}

export async function exportProjectRowsExcel(filters: ProjectExportFilters) {
  const { data } = await http.get('/project-exports/excel', {
    params: cleanFilters(filters),
    responseType: 'blob'
  })
  const url = window.URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = `项目清单-${new Date().toISOString().slice(0, 10)}.xlsx`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

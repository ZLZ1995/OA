import type { WorkbenchProjectItem } from '../api/workbench'

export interface WorkpaperTask {
  project_id: number
  project_code: string
  project_name: string
  client_name?: string
  status: string
  panel: string
}
export function mergeWorkpaperTodos(rows: WorkbenchProjectItem[], tasks: WorkpaperTask[], searching: boolean) {
  const result = rows.map(row => ({ ...row }))
  for (const task of tasks) {
    let row = result.find(item => item.id === task.project_id)
    if (!row && searching) continue
    const label = task.panel === 'operationWorkpaperReview' ? '审核操作类底稿' : task.status === 'REJECTED' ? '补充操作类底稿' : '提交操作类底稿'
    if (!row) {
      row = { id: task.project_id, project_no: task.project_code, project_name: task.project_name,
        client_name: task.client_name || '', current_step: '操作类底稿', status_display: label,
        can_enter: true, can_edit: false, can_delete: false, can_archive: false,
        can_request_termination: false, can_approve_termination: false }
      result.push(row)
    }
    row.workpaper_panel = task.panel
    row.workpaper_action = label
    row.todo_action = [row.todo_action === '无待办' ? '' : row.todo_action, label].filter(Boolean).join('；')
  }
  return result
}

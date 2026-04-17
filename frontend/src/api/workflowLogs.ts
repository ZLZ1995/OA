import http from './http'

export interface WorkflowLogItem {
  id: number
  work_order_id: number
  from_status: string
  to_status: string
  action_type: string
  operator_user_id: number
  remark?: string
  created_at: string
}

export async function listWorkflowLogs(workOrderId: number) {
  const { data } = await http.get(`/workflow-logs/work-orders/${workOrderId}`)
  return data as { items: WorkflowLogItem[] }
}

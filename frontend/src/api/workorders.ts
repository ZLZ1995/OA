import http from './http'

export interface WorkOrderItem {
  id: number
  work_order_no: string
  project_id: number
  title: string
  current_status: string
}

export async function listWorkOrders() {
  const { data } = await http.get('/work-orders')
  return data as { items: WorkOrderItem[] }
}

export async function createWorkOrder(payload: {
  work_order_no: string
  project_id: number
  title: string
  description?: string
}) {
  const { data } = await http.post('/work-orders', payload)
  return data as WorkOrderItem
}

export async function updateWorkOrder(
  workOrderId: number,
  payload: { title?: string; current_handler_user_id?: number | null }
) {
  const { data } = await http.patch(`/work-orders/${workOrderId}`, payload)
  return data as WorkOrderItem
}

export async function deleteWorkOrder(workOrderId: number) {
  await http.delete(`/work-orders/${workOrderId}`)
}

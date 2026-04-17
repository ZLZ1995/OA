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

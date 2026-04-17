import http from './http'

export async function getWorkOrders() {
  const { data } = await http.get('/work-orders')
  return data as Array<{ id: number; work_order_no: string; title: string; current_status: string }>
}

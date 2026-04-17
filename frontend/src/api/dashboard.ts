import http from './http'

export async function getMyDashboard() {
  const { data } = await http.get('/dashboard/mine')
  return data as {
    todo_items: { id: number }[]
    created_items: { id: number }[]
  }
}

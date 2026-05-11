import http from './http'

export interface RoleItem {
  id: number
  code: string
  name: string
  description: string
}

export async function listRoles() {
  const { data } = await http.get('/roles')
  return data as { items: RoleItem[] }
}

import http from './http'

export interface UserItem {
  id: number
  username: string
  real_name: string
  email?: string
  phone?: string
  is_active: boolean
  roles: string[]
}

export async function listUsers() {
  const { data } = await http.get('/users')
  return data as { items: UserItem[] }
}

export async function createUser(payload: {
  username: string
  real_name: string
  password: string
  role_codes: string[]
}) {
  const { data } = await http.post('/users', payload)
  return data as UserItem
}

export async function bindUserRoles(userId: number, roleCodes: string[]) {
  const { data } = await http.put(`/users/${userId}/roles`, { role_codes: roleCodes })
  return data as UserItem
}

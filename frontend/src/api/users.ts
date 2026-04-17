import http from './http'

export async function getUsers() {
  const { data } = await http.get('/users')
  return data as Array<{ id: number; username: string; real_name: string; roles: string[]; is_active: boolean }>
}

export async function getRoles() {
  const { data } = await http.get('/roles')
  return data as Array<{ id: number; code: string; name: string }>
}

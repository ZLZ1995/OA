import http from './http'

export interface LoginPayload {
  username: string
  password: string
}

export async function login(payload: LoginPayload) {
  const { data } = await http.post('/auth/login', payload)
  return data as { access_token: string; token_type: string }
}

export async function me() {
  const { data } = await http.get('/auth/me')
  return data as { id: number; username: string; real_name: string; roles: string[] }
}

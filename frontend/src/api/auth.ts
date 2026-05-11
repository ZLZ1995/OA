import http from './http'

export interface LoginPayload {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface CurrentUserResponse {
  id: number
  username: string
  real_name: string
  roles: string[]
}

export interface PasswordResetPayload {
  username: string
  old_password: string
  new_password: string
}

function ensureTokenResponse(data: unknown): TokenResponse {
  if (!data || typeof data !== 'object') {
    throw new Error('登录接口返回格式错误')
  }

  const candidate = data as Partial<TokenResponse>
  if (typeof candidate.access_token !== 'string' || candidate.access_token.trim() === '') {
    throw new Error('登录接口未返回有效 access_token')
  }

  return {
    access_token: candidate.access_token,
    token_type: typeof candidate.token_type === 'string' ? candidate.token_type : 'bearer'
  }
}

function ensureCurrentUserResponse(data: unknown): CurrentUserResponse {
  if (!data || typeof data !== 'object') {
    throw new Error('用户信息接口返回格式错误')
  }

  const candidate = data as Partial<CurrentUserResponse>
  if (typeof candidate.id !== 'number' || typeof candidate.username !== 'string') {
    throw new Error('用户信息接口未返回有效用户')
  }

  return {
    id: candidate.id,
    username: candidate.username,
    real_name: typeof candidate.real_name === 'string' ? candidate.real_name : '',
    roles: Array.isArray(candidate.roles) ? candidate.roles.filter((item): item is string => typeof item === 'string') : []
  }
}

export async function login(payload: LoginPayload) {
  const { data } = await http.post('/auth/login', payload)
  return ensureTokenResponse(data)
}

export async function me() {
  const { data } = await http.get('/auth/me')
  return ensureCurrentUserResponse(data)
}

export async function resetPassword(payload: PasswordResetPayload) {
  const { data } = await http.post('/auth/password/reset', payload)
  return data as { message: string }
}

import http from './http'

export interface OaAgentProjectCandidate {
  id: number
  project_code: string
  project_name: string
  client_name: string
  current_step?: string | null
  status_display?: string | null
}

export interface OaAgentMessage {
  role: string
  content: string
  created_at: string
}

export interface OaAgentResponse {
  session_id: string
  response_type: 'answer' | 'candidates' | 'permission_denied'
  answer?: string | null
  project_id?: number | null
  candidates: OaAgentProjectCandidate[]
}

export interface OaAgentSessionResponse {
  session_id: string
  project_id?: number | null
  messages: OaAgentMessage[]
}

export async function sendAgentMessage(payload: { message: string; session_id?: string; project_id?: number }) {
  const { data } = await http.post('/oa-agent/messages', payload)
  return data as OaAgentResponse
}

export async function setAgentProjectContext(payload: { project_id: number; session_id?: string }) {
  const { data } = await http.post('/oa-agent/context', payload)
  return data as OaAgentSessionResponse
}

export async function getAgentSession(sessionId?: string) {
  const { data } = await http.get('/oa-agent/session', {
    params: sessionId ? { session_id: sessionId } : undefined,
  })
  return data as OaAgentSessionResponse
}

export async function clearAgentSession() {
  await http.delete('/oa-agent/session')
}

const AGENT_SESSION_STORAGE_KEY = 'oa_agent_session_id'

export function readLocalAgentSessionId() {
  return sessionStorage.getItem(AGENT_SESSION_STORAGE_KEY) || undefined
}

export function saveLocalAgentSessionId(sessionId: string) {
  sessionStorage.setItem(AGENT_SESSION_STORAGE_KEY, sessionId)
}

export function clearLocalAgentSessionId() {
  sessionStorage.removeItem(AGENT_SESSION_STORAGE_KEY)
}

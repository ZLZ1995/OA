import http from './http'

export async function getProjects() {
  const { data } = await http.get('/projects')
  return data as Array<{ id: number; project_code: string; project_name: string; client_name: string }>
}

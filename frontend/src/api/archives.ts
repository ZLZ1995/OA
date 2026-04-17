import http from './http'

export interface ArchiveItem {
  id: number
  work_order_id: number
  archived_by: number
  archive_no: string
  archive_location?: string
  archive_at: string
  remark?: string
}

export async function listArchives() {
  const { data } = await http.get('/archives')
  return data as { items: ArchiveItem[] }
}

export async function createArchive(payload: {
  work_order_id: number
  archive_no: string
  archive_location?: string
  archive_at: string
  remark?: string
}) {
  const { data } = await http.post('/archives', payload)
  return data as ArchiveItem
}

export async function updateArchive(archiveId: number, payload: Partial<ArchiveItem>) {
  const { data } = await http.patch(`/archives/${archiveId}`, payload)
  return data as ArchiveItem
}

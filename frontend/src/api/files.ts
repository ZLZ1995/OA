import http from './http'

export interface WorkOrderFileItem {
  id: number
  work_order_id: number
  file_category: string
  business_stage: string
  version_no: number
  is_current: boolean
  origin_file_name: string
  storage_key: string
  file_size?: number | null
  uploaded_by: number
  uploaded_by_name?: string | null
  uploaded_at: string
}

export async function uploadWorkOrderFile(payload: {
  work_order_id: number
  file_category: string
  business_stage: string
  file: File
}) {
  const formData = new FormData()
  formData.append('work_order_id', String(payload.work_order_id))
  formData.append('file_category', payload.file_category)
  formData.append('business_stage', payload.business_stage)
  formData.append('upload', payload.file)
  const { data } = await http.post('/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return data as WorkOrderFileItem
}

export async function replaceWorkOrderFile(fileId: number, file: File) {
  const formData = new FormData()
  formData.append('upload', file)
  const { data } = await http.post(`/files/${fileId}/replace`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return data as WorkOrderFileItem
}

export async function listWorkOrderFiles(workOrderId: number) {
  const { data } = await http.get(`/files/work-orders/${workOrderId}`)
  return data as { items: WorkOrderFileItem[] }
}

export async function completeContractUpload(workOrderId: number) {
  const { data } = await http.post(`/files/work-orders/${workOrderId}/complete-contract`)
  return data as { status: string }
}

export async function downloadWorkOrderFile(fileId: number, filename?: string) {
  const { data } = await http.get(`/files/${fileId}/download`, {
    responseType: 'blob'
  })
  const url = window.URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename || `file-${fileId}`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

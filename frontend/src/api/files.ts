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
  uploaded_by: number
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

export async function listWorkOrderFiles(workOrderId: number) {
  const { data } = await http.get(`/files/work-orders/${workOrderId}`)
  return data as { items: WorkOrderFileItem[] }
}

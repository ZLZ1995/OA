import http from './http'
import type { UploadProgressState } from '@/types/upload'

const FILE_UPLOAD_TIMEOUT_MS = 120000

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
  source_type: string
  source_file_id?: number | null
  locked: boolean
  display_label?: string | null
}

type UploadProgressCallback = (progress: UploadProgressState) => void

function emitUploadProgress(
  callback: UploadProgressCallback | undefined,
  partial: Partial<UploadProgressState> & Pick<UploadProgressState, 'status'>
) {
  if (!callback) return
  callback({
    loaded: partial.loaded ?? 0,
    total: partial.total ?? 0,
    percentage: partial.percentage ?? 0,
    status: partial.status,
    fileName: partial.fileName,
    errorMessage: partial.errorMessage,
  })
}

export async function uploadWorkOrderFile(payload: {
  work_order_id: number
  file_category: string
  business_stage: string
  file: File
  onProgress?: UploadProgressCallback
}) {
  const formData = new FormData()
  formData.append('work_order_id', String(payload.work_order_id))
  formData.append('file_category', payload.file_category)
  formData.append('business_stage', payload.business_stage)
  formData.append('upload', payload.file)
  emitUploadProgress(payload.onProgress, {
    status: 'uploading',
    fileName: payload.file.name,
    loaded: 0,
    total: payload.file.size,
    percentage: 0,
  })
  try {
    const { data } = await http.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: FILE_UPLOAD_TIMEOUT_MS,
      onUploadProgress: (event) => {
        const total = event.total ?? payload.file.size ?? 0
        const loaded = event.loaded ?? 0
        const percentage = total > 0 ? Math.min(100, Math.round((loaded / total) * 100)) : 0
        emitUploadProgress(payload.onProgress, {
          status: 'uploading',
          fileName: payload.file.name,
          loaded,
          total,
          percentage,
        })
      }
    })
    emitUploadProgress(payload.onProgress, {
      status: 'success',
      fileName: payload.file.name,
      loaded: payload.file.size,
      total: payload.file.size,
      percentage: 100,
    })
    return data as WorkOrderFileItem
  } catch (error: any) {
    emitUploadProgress(payload.onProgress, {
      status: 'error',
      fileName: payload.file.name,
      loaded: 0,
      total: payload.file.size,
      percentage: 0,
      errorMessage: error?.response?.data?.detail || error?.message || '上传失败',
    })
    throw error
  }
}

export async function replaceWorkOrderFile(fileId: number, file: File, onProgress?: UploadProgressCallback) {
  const formData = new FormData()
  formData.append('upload', file)
  emitUploadProgress(onProgress, {
    status: 'uploading',
    fileName: file.name,
    loaded: 0,
    total: file.size,
    percentage: 0,
  })
  try {
    const { data } = await http.post(`/files/${fileId}/replace`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: FILE_UPLOAD_TIMEOUT_MS,
      onUploadProgress: (event) => {
        const total = event.total ?? file.size ?? 0
        const loaded = event.loaded ?? 0
        const percentage = total > 0 ? Math.min(100, Math.round((loaded / total) * 100)) : 0
        emitUploadProgress(onProgress, {
          status: 'uploading',
          fileName: file.name,
          loaded,
          total,
          percentage,
        })
      }
    })
    emitUploadProgress(onProgress, {
      status: 'success',
      fileName: file.name,
      loaded: file.size,
      total: file.size,
      percentage: 100,
    })
    return data as WorkOrderFileItem
  } catch (error: any) {
    emitUploadProgress(onProgress, {
      status: 'error',
      fileName: file.name,
      loaded: 0,
      total: file.size,
      percentage: 0,
      errorMessage: error?.response?.data?.detail || error?.message || '上传失败',
    })
    throw error
  }
}

export async function listWorkOrderFiles(workOrderId: number) {
  const { data } = await http.get(`/files/work-orders/${workOrderId}`)
  return data as { items: WorkOrderFileItem[] }
}

export async function deleteWorkOrderFile(fileId: number) {
  await http.delete(`/files/${fileId}`)
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

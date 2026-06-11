export type UploadProgressStatus = 'idle' | 'uploading' | 'success' | 'error'

export interface UploadProgressState {
  loaded: number
  total: number
  percentage: number
  status: UploadProgressStatus
  fileName?: string
  errorMessage?: string
}

export function buildIdleUploadProgress(fileName?: string): UploadProgressState {
  return {
    loaded: 0,
    total: 0,
    percentage: 0,
    status: 'idle',
    fileName,
  }
}

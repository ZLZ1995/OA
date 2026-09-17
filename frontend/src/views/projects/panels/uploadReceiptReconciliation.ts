export interface UploadReceiptCandidate {
  id: number
  file_category: string
  business_stage: string
  origin_file_name: string
  file_size?: number | null
  is_current: boolean
}

export interface ExpectedUploadReceipt {
  fileCategory: string
  businessStage: string
  fileName: string
  fileSize: number
}

export function isAmbiguousUploadError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  const candidate = error as { code?: string; response?: unknown }
  return !candidate.response && candidate.code !== 'ECONNABORTED'
}

export function findNewUploadReceipt(
  items: UploadReceiptCandidate[],
  knownFileIds: ReadonlySet<number>,
  expected: ExpectedUploadReceipt,
): UploadReceiptCandidate | undefined {
  return items.find(item => (
    !knownFileIds.has(item.id)
    && item.is_current
    && item.file_category === expected.fileCategory
    && item.business_stage === expected.businessStage
    && item.origin_file_name === expected.fileName
    && Number(item.file_size ?? -1) === expected.fileSize
  ))
}

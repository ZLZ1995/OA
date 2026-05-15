import http from './http'

export async function requestOwnerExternalAuditConfirm(workOrderId: number) {
  const { data } = await http.post(`/signoff/work-orders/${workOrderId}/request-owner-confirm`)
  return data as { message: string }
}

export async function markNoExternalAudit(workOrderId: number) {
  const { data } = await http.post(`/signoff/work-orders/${workOrderId}/mark-no-external`)
  return data as { message: string }
}

export async function markHasExternalAudit(workOrderId: number) {
  const { data } = await http.post(`/signoff/work-orders/${workOrderId}/mark-has-external`)
  return data as { message: string }
}

export async function enterSignoffReview(workOrderId: number) {
  const { data } = await http.post(`/signoff/work-orders/${workOrderId}/enter-review`)
  return data as { message: string }
}

export async function approveSignoff(workOrderId: number) {
  const { data } = await http.post(`/signoff/work-orders/${workOrderId}/approve`)
  return data as { message: string }
}

export async function returnSignoffToThird(workOrderId: number) {
  const { data } = await http.post(`/signoff/work-orders/${workOrderId}/return-third`)
  return data as { message: string }
}

export async function returnSignoffToOwnerUpload(workOrderId: number) {
  const { data } = await http.post(`/signoff/work-orders/${workOrderId}/return-owner-upload`)
  return data as { message: string }
}

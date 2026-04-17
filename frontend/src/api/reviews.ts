import http from './http'

export interface ReviewRecordItem {
  id: number
  work_order_id: number
  review_round: 'FIRST' | 'SECOND' | 'THIRD'
  reviewer_user_id: number
  action: 'SUBMIT' | 'APPROVE' | 'REJECT_RETURN'
  comment?: string
  acted_at: string
}

export async function submitReview(payload: {
  work_order_id: number
  review_round: 'FIRST' | 'SECOND' | 'THIRD'
  reviewer_user_id: number
  comment?: string
}) {
  const { data } = await http.post('/reviews/submit', payload)
  return data as ReviewRecordItem
}

export async function decideReview(payload: {
  work_order_id: number
  review_round: 'FIRST' | 'SECOND' | 'THIRD'
  action: 'APPROVE' | 'REJECT_RETURN'
  comment?: string
}) {
  const { data } = await http.post('/reviews/decision', payload)
  return data as ReviewRecordItem
}

export async function listReviews(workOrderId: number) {
  const { data } = await http.get(`/reviews/work-orders/${workOrderId}`)
  return data as { items: ReviewRecordItem[] }
}

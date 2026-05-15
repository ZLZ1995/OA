import http from './http'

export interface ReviewRecordItem {
  id: number
  work_order_id: number
  review_round: 'FIRST' | 'SECOND' | 'THIRD' | 'EXTERNAL_FIRST' | 'EXTERNAL_SECOND' | 'EXTERNAL_THIRD'
  reviewer_user_id: number
  reviewer_name?: string
  action: 'SUBMIT' | 'APPROVE' | 'REJECT_RETURN' | 'CHANGE_REVIEWER'
  comment?: string
  acted_at: string
  source_record_id?: number | null
  source_round_comment?: string | null
  source_round_reviewer_name?: string | null
  auto_carried_from_previous?: boolean
  transferred_to_next?: boolean
  transferred_to_round?: 'FIRST' | 'SECOND' | 'THIRD' | 'EXTERNAL_FIRST' | 'EXTERNAL_SECOND' | 'EXTERNAL_THIRD' | null
}

export async function submitReview(payload: {
  work_order_id: number
  review_round: 'FIRST' | 'SECOND' | 'THIRD' | 'EXTERNAL_FIRST' | 'EXTERNAL_SECOND' | 'EXTERNAL_THIRD'
  reviewer_user_id: number
  comment?: string
}) {
  const { data } = await http.post('/reviews/submit', payload)
  return data as ReviewRecordItem
}

export async function decideReview(payload: {
  work_order_id: number
  review_round: 'FIRST' | 'SECOND' | 'THIRD' | 'EXTERNAL_FIRST' | 'EXTERNAL_SECOND' | 'EXTERNAL_THIRD'
  action: 'APPROVE' | 'REJECT_RETURN'
  comment?: string
}) {
  const { data } = await http.post('/reviews/decision', payload)
  return data as ReviewRecordItem
}

export async function changeReviewAssignee(payload: {
  work_order_id: number
  review_round: 'FIRST' | 'SECOND' | 'THIRD' | 'EXTERNAL_FIRST' | 'EXTERNAL_SECOND' | 'EXTERNAL_THIRD'
  reviewer_user_id: number
  comment?: string
}) {
  const { data } = await http.post('/reviews/change-reviewer', payload)
  return data as ReviewRecordItem
}

export async function withdrawLatestReview(workOrderId: number) {
  const { data } = await http.post(`/reviews/work-orders/${workOrderId}/withdraw-latest`)
  return data as { status: string }
}

export async function listReviews(workOrderId: number) {
  const { data } = await http.get(`/reviews/work-orders/${workOrderId}`)
  return data as { items: ReviewRecordItem[] }
}

export interface ReviewCandidateItem {
  user_id: number
  username: string
  real_name: string
}

export async function listReviewCandidates(workOrderId: number, reviewRound: "FIRST" | "SECOND" | "THIRD" | "EXTERNAL_FIRST" | "EXTERNAL_SECOND" | "EXTERNAL_THIRD") {
  const { data } = await http.get('/reviews/candidates', { params: { work_order_id: workOrderId, review_round: reviewRound } })
  return data as { items: ReviewCandidateItem[] }
}

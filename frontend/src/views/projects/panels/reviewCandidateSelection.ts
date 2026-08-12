import type { ReviewCandidateItem } from '@/api/reviews'

export function prepareReviewCandidateSelection(
  candidates: ReviewCandidateItem[],
  currentReviewerId: number | null | undefined,
  excludedReviewerIds: Array<number | null | undefined>,
  isReviewerChange: boolean,
) {
  const excludedIds = new Set(excludedReviewerIds.filter((id): id is number => Boolean(id)))
  const options = candidates.filter(candidate => {
    if (isReviewerChange && candidate.user_id === currentReviewerId) return false
    return !excludedIds.has(candidate.user_id)
  })

  const selectedReviewerId = !isReviewerChange && currentReviewerId && options.some(candidate => candidate.user_id === currentReviewerId)
    ? currentReviewerId
    : undefined

  return { options, selectedReviewerId }
}

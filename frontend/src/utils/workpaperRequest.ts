// A retry belongs to one editable round. Withdrawal/rejection creates a new intent.
export function workpaperDraftKey(orderId: number | undefined, submissionId: number | null, status: string): string | null {
  return ['DRAFT', 'WITHDRAWN', 'REJECTED'].includes(status)
    ? `${orderId}:${submissionId ?? 0}:${status}` : null
}

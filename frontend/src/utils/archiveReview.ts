export function canReviewArchive(status: string | null | undefined, submission: string | null | undefined,
  reviewerId: number | null | undefined, userId: number | undefined, roles: string[]): boolean {
  return status === 'ARCHIVE_REVIEWING' && ['ONLINE', 'OFFLINE'].includes(submission || '') &&
    (roles.includes('ADMIN') || (roles.includes('ARCHIVE_MANAGER') && !!userId && reviewerId === userId))
}

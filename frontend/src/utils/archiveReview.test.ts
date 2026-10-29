import test from 'node:test'
import assert from 'node:assert/strict'
import { canReviewArchive } from './archiveReview'

test('archive decision requires a pending archive submission and assigned reviewer', () => {
  const roles = ['ARCHIVE_MANAGER']
  assert.equal(canReviewArchive('THIRD_REVIEWING', null, null, 2, roles), false)
  assert.equal(canReviewArchive('ARCHIVE_REVIEWING', 'ONLINE', 2, 2, roles), true)
  assert.equal(canReviewArchive('ARCHIVE_REVIEWING', 'OFFLINE', 2, 3, roles), false)
  assert.equal(canReviewArchive('ARCHIVE_REVIEWING', 'OFFLINE', 2, 3, ['ADMIN']), true)
  assert.equal(canReviewArchive('WAIT_ARCHIVE_SUBMIT', 'APPROVED', 2, 2, roles), false)
  assert.equal(canReviewArchive('ARCHIVE_REJECTED', 'REJECTED', 2, 2, roles), false)
  assert.equal(canReviewArchive('ARCHIVED', 'APPROVED', 2, 2, roles), false)
})

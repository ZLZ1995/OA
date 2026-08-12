import test from 'node:test'
import assert from 'node:assert/strict'

import { prepareReviewCandidateSelection } from './reviewCandidateSelection'

const candidates = [
  { user_id: 14, username: 'shilinguang', real_name: '石林广' },
  { user_id: 21, username: 'reviewer2', real_name: '审核老师二' },
]

test('keeps and selects the saved reviewer during ordinary review submission', () => {
  const result = prepareReviewCandidateSelection(candidates, 14, [], false)

  assert.deepEqual(result.options, candidates)
  assert.equal(result.selectedReviewerId, 14)
})

test('excludes the current reviewer only while choosing a replacement', () => {
  const result = prepareReviewCandidateSelection(candidates, 14, [], true)

  assert.deepEqual(result.options, [candidates[1]])
  assert.equal(result.selectedReviewerId, undefined)
})

test('still excludes reviewers assigned to another review round', () => {
  const result = prepareReviewCandidateSelection(candidates, 14, [21], false)

  assert.deepEqual(result.options, [candidates[0]])
  assert.equal(result.selectedReviewerId, 14)
})

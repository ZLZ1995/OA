import test from 'node:test'
import assert from 'node:assert/strict'
import { workpaperDraftKey } from './workpaperRequest'

test('workpaper retries keep identity within a draft but withdrawal starts a new intent', () => {
  const initial = workpaperDraftKey(1, null, 'DRAFT')
  assert.equal(initial, workpaperDraftKey(1, null, 'DRAFT'))
  assert.equal(workpaperDraftKey(1, 10, 'SUBMITTED'), null)
  assert.notEqual(initial, workpaperDraftKey(1, 10, 'WITHDRAWN'))
  assert.notEqual(workpaperDraftKey(1, 10, 'WITHDRAWN'), workpaperDraftKey(1, 11, 'WITHDRAWN'))
  assert.notEqual(workpaperDraftKey(1, 10, 'REJECTED'), workpaperDraftKey(2, 10, 'REJECTED'))
})

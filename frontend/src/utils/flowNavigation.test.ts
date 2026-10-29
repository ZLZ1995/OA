import test from 'node:test'
import assert from 'node:assert/strict'
import { workflowPanel, entryPanel, currentTodoLabel } from './flowNavigation'

test('external confirmation advances to signoff and ignores stale entry links', () => {
  assert.equal(workflowPanel('WAIT_OWNER_EXTERNAL_AUDIT_CONFIRM'), 'externalAuditConfirm')
  for (const status of ['WAIT_OWNER_SIGNOFF_UPLOAD', 'SIGNOFF_REVIEWING']) {
    assert.equal(workflowPanel(status), 'signoff')
    assert.equal(entryPanel('externalAuditConfirm', status), 'signoff')
    assert.equal(entryPanel('externalReview', status), 'signoff')
  }
  assert.equal(currentTodoLabel('', '签发审核', '外部审核确认'), '签发审核')
})

test('pending workpapers retain the parallel gate and explicit reviewer entry', () => {
  assert.equal(entryPanel('externalAuditConfirm', 'WAIT_PARALLEL_WORKPAPER'), 'operationWorkpaper')
  assert.equal(entryPanel('operationWorkpaperReview', 'WAIT_PARALLEL_WORKPAPER'), 'operationWorkpaperReview')
  assert.equal(workflowPanel('WAIT_EXTERNAL_FIRST_REVIEW_SUBMIT'), 'externalReview')
  assert.equal(workflowPanel('EXTERNAL_THIRD_REVIEWING'), 'externalReview')
  assert.equal(entryPanel('operationWorkpaperReview', 'THIRD_REVIEWING'), 'operationWorkpaperReview')
})

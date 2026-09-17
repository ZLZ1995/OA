import test from 'node:test'
import assert from 'node:assert/strict'

import { findNewUploadReceipt, isAmbiguousUploadError } from './uploadReceiptReconciliation'

test('treats a response-less network failure as ambiguous but not a timeout or HTTP response', () => {
  assert.equal(isAmbiguousUploadError({ code: 'ERR_NETWORK', message: 'Network Error' }), true)
  assert.equal(isAmbiguousUploadError({ code: 'ECONNABORTED' }), false)
  assert.equal(isAmbiguousUploadError({ response: { status: 400 } }), false)
})

test('accepts only a new current receipt matching the attempted upload', () => {
  const receipt = findNewUploadReceipt([
    {
      id: 7,
      file_category: 'REPORT_ZIP',
      business_stage: 'FIRST_REVIEW',
      origin_file_name: 'result.zip',
      file_size: 183,
      is_current: false,
    },
    {
      id: 8,
      file_category: 'REPORT_ZIP',
      business_stage: 'FIRST_REVIEW',
      origin_file_name: 'result.zip',
      file_size: 183,
      is_current: true,
    },
  ], new Set([7]), {
    fileCategory: 'REPORT_ZIP',
    businessStage: 'FIRST_REVIEW',
    fileName: 'result.zip',
    fileSize: 183,
  })

  assert.equal(receipt?.id, 8)
})

test('does not mistake a prior file or mismatched payload for a new receipt', () => {
  const receipt = findNewUploadReceipt([
    {
      id: 8,
      file_category: 'REPORT_ZIP',
      business_stage: 'FIRST_REVIEW',
      origin_file_name: 'result.zip',
      file_size: 183,
      is_current: true,
    },
  ], new Set([8]), {
    fileCategory: 'REPORT_ZIP',
    businessStage: 'FIRST_REVIEW',
    fileName: 'result.zip',
    fileSize: 183,
  })

  assert.equal(receipt, undefined)
})

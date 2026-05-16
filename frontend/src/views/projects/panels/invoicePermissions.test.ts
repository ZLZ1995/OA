import test from 'node:test'
import assert from 'node:assert/strict'

import { isFinanceRoleInCurrentFlow } from './invoicePermissions'

test('treats current project finance role as finance processing mode', () => {
  assert.equal(isFinanceRoleInCurrentFlow('财务'), true)
})

test('does not force mixed-role admin account into finance mode when current project role is admin', () => {
  assert.equal(isFinanceRoleInCurrentFlow('管理员'), false)
})

test('does not force project party into finance mode even if account may also carry finance globally', () => {
  assert.equal(isFinanceRoleInCurrentFlow('项目负责人'), false)
})

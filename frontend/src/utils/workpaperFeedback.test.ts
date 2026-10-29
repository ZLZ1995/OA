import test from 'node:test'
import assert from 'node:assert/strict'
import { validWorkpaperUrl, workpaperError } from './workpaperFeedback'
import { mergeWorkpaperTodos } from './workpaperTodos'

test('cloud link validation and backend validation messages', () => {
  for (const url of ['111', 'javascript:alert(1)', 'https://user:pass@example.com', 'https://', 'https://exa mple.com']) assert.equal(validWorkpaperUrl(url), false)
  assert.equal(validWorkpaperUrl(' https://pan.baidu.com/s/abc?pwd=1234 '), true)
  assert.equal(workpaperError({ response: { data: { detail: [{ msg: 'Value error, 请填写有效的HTTP或HTTPS网盘链接' }] } } }), '请填写有效的HTTP或HTTPS网盘链接')
  assert.equal(workpaperError({ response: { data: { detail: '当前资料已更新' } } }), '当前资料已更新')
})

test('workpaper tasks join existing project rows and respect search results', () => {
  const task = { project_id: 1, project_code: 'P1', project_name: 'test', client_name: 'client', status: 'DRAFT', panel: 'operationWorkpaper' }
  const standalone = mergeWorkpaperTodos([], [task], false)
  assert.equal(standalone.length, 1)
  assert.equal(standalone[0].client_name, 'client')
  const original = { ...standalone[0], todo_action: '三审' }
  const merged = mergeWorkpaperTodos([original], [task], false)
  assert.equal(merged.length, 1)
  assert.equal(merged[0].todo_action, '三审；提交操作类底稿')
  assert.equal(original.todo_action, '三审')
  assert.equal(mergeWorkpaperTodos([], [task], true).length, 0)
  assert.equal(mergeWorkpaperTodos([original], [{ ...task, panel: 'operationWorkpaperReview' }], true)[0].workpaper_action, '审核操作类底稿')
})

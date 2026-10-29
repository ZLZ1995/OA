export function validWorkpaperUrl(value: string): boolean {
  const text = value.trim()
  if (!/^https?:\/\//i.test(text) || /\s/.test(text)) return false
  try {
    const url = new URL(text)
    return !!url.hostname && !url.username && !url.password
  } catch { return false }
}

export function workpaperError(error: any): string {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map(item => typeof item?.msg === 'string' ? item.msg.replace(/^Value error, /, '') : '').filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  return '操作失败，请稍后重试；如仍失败，请联系管理员'
}

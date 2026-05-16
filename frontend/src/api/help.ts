import http from './http'

export interface HelpMenuItem {
  key: string
  title: string
}

export interface HelpContentItem {
  key: string
  title: string
  image_url: string
  description: string
  sort_order: number
}

export async function getHelpMenu() {
  const { data } = await http.get('/help/menu')
  return data as { items: HelpMenuItem[] }
}

export async function getHelpSection(sectionKey: string) {
  const { data } = await http.get(`/help/sections/${sectionKey}`)
  return data as { section: string; title: string; items: HelpContentItem[] }
}

export async function getHelpItem(itemKey: string) {
  const { data } = await http.get(`/help/items/${itemKey}`)
  return data as HelpContentItem & { section: string }
}

export function getHelpManualDownloadUrl() {
  return `${http.defaults.baseURL}/help/manual/download`
}

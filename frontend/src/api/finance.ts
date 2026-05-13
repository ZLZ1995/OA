import http from './http'

export interface InvoiceItem {
  id: number
  work_order_id: number
  invoice_no: string
  invoice_info?: string | null
  invoice_type?: string | null
  amount: number
  issued_at?: string
  status: string
  finance_handler_id?: number | null
  handled_by?: number
}

export async function listInvoices() {
  const { data } = await http.get('/finance/invoices')
  return data as { items: InvoiceItem[] }
}

export async function createInvoice(payload: {
  work_order_id: number
  invoice_no?: string
  invoice_info?: string
  invoice_type?: string
  amount: number
  finance_handler_id?: number
  issued_at?: string
  status?: string
}) {
  const { data } = await http.post('/finance/invoices', payload)
  return data as InvoiceItem
}

export async function updateInvoice(invoiceId: number, payload: Partial<InvoiceItem>) {
  const { data } = await http.patch(`/finance/invoices/${invoiceId}`, payload)
  return data as InvoiceItem
}

export async function rejectInvoice(invoiceId: number, remark?: string) {
  const { data } = await http.post(`/finance/invoices/${invoiceId}/reject`, { status: remark })
  return data as InvoiceItem
}

export async function completeInvoice(invoiceId: number) {
  const { data } = await http.post(`/finance/invoices/${invoiceId}/complete`)
  return data as InvoiceItem
}

export async function confirmInvoice(invoiceId: number) {
  const { data } = await http.post(`/finance/invoices/${invoiceId}/confirm`)
  return data as InvoiceItem
}

export async function returnInvoice(invoiceId: number, remark?: string) {
  const { data } = await http.post(`/finance/invoices/${invoiceId}/return`, { status: remark })
  return data as InvoiceItem
}

export async function withdrawInvoice(invoiceId: number) {
  const { data } = await http.post(`/finance/invoices/${invoiceId}/withdraw`)
  return data as InvoiceItem
}

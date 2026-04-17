import http from './http'

export interface InvoiceItem {
  id: number
  work_order_id: number
  invoice_no: string
  amount: number
  issued_at?: string
  status: string
  handled_by?: number
}

export async function listInvoices() {
  const { data } = await http.get('/finance/invoices')
  return data as { items: InvoiceItem[] }
}

export async function createInvoice(payload: {
  work_order_id: number
  invoice_no: string
  amount: number
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

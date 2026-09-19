import { apiClient } from './client'
import type { Invoice, InvoiceListItem, ItemInput, Payment } from '../types'

export interface InvoicePayload {
  client_id: number
  issue_date: string | null
  due_date: string | null
  items: ItemInput[]
  remarks: string | null
  // 通常のPUTはproject_id省略で案件なしに更新されるため、編集時は現在値を必ず送る(詳細設計書4.9.5・4.13.2)
  project_id: number | null
}

export interface InvoiceListFilters {
  client_id?: number
  payment_status?: string
}

export const invoicesApi = {
  list: async (filters: InvoiceListFilters = {}): Promise<InvoiceListItem[]> =>
    (await apiClient.get('/invoices', { params: filters })).data,
  get: async (id: number): Promise<Invoice> => (await apiClient.get(`/invoices/${id}`)).data,
  create: async (payload: InvoicePayload): Promise<Invoice> => (await apiClient.post('/invoices', payload)).data,
  update: async (id: number, payload: InvoicePayload): Promise<Invoice> =>
    (await apiClient.put(`/invoices/${id}`, payload)).data,
  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/invoices/${id}`)
  },
  linkProject: async (id: number, projectId: number | null): Promise<Invoice> =>
    (await apiClient.put(`/invoices/${id}/project`, { project_id: projectId })).data,
  pdfUrl: (id: number): string => `/api/invoices/${id}/pdf`,
  listPayments: async (invoiceId: number): Promise<Payment[]> =>
    (await apiClient.get(`/invoices/${invoiceId}/payments`)).data,
  addPayment: async (
    invoiceId: number,
    payload: { payment_date: string; amount: number; remarks: string | null; force?: boolean }
  ): Promise<Payment> => (await apiClient.post(`/invoices/${invoiceId}/payments`, payload)).data,
  removePayment: async (paymentId: number): Promise<void> => {
    await apiClient.delete(`/payments/${paymentId}`)
  },
}

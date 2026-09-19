import { apiClient } from './client'
import type { Invoice, ItemInput, Quote, QuoteListItem, QuoteStatus } from '../types'

export interface QuotePayload {
  client_id: number
  issue_date: string | null
  expiry_date: string | null
  status: QuoteStatus
  items: ItemInput[]
  remarks: string | null
  // 通常のPUTはproject_id省略で案件なしに更新されるため、編集時は現在値を必ず送る(詳細設計書4.9.5・4.13.2)
  project_id: number | null
}

export interface QuoteListFilters {
  client_id?: number
  status?: string
}

export const quotesApi = {
  list: async (filters: QuoteListFilters = {}): Promise<QuoteListItem[]> =>
    (await apiClient.get('/quotes', { params: filters })).data,
  get: async (id: number): Promise<Quote> => (await apiClient.get(`/quotes/${id}`)).data,
  create: async (payload: QuotePayload): Promise<Quote> => (await apiClient.post('/quotes', payload)).data,
  update: async (id: number, payload: QuotePayload): Promise<Quote> =>
    (await apiClient.put(`/quotes/${id}`, payload)).data,
  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/quotes/${id}`)
  },
  linkProject: async (id: number, projectId: number | null): Promise<Quote> =>
    (await apiClient.put(`/quotes/${id}/project`, { project_id: projectId })).data,
  pdfUrl: (id: number): string => `/api/quotes/${id}/pdf`,
  convertToInvoice: async (id: number): Promise<Invoice> =>
    (await apiClient.post(`/quotes/${id}/convert-to-invoice`)).data,
}

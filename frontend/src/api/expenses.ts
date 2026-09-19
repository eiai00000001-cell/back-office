import { apiClient } from './client'
import type { Expense, ExpenseSummary, ExpenseTaxCategory, PaymentMethod } from '../types'

export interface ExpensePayload {
  expense_date: string
  account_category: string
  amount: number
  tax_category: ExpenseTaxCategory
  payee: string | null
  payment_method: PaymentMethod | null
  memo: string | null
  // 通常のPUTはproject_id省略で案件なしに更新されるため、編集時は現在値を必ず送る(詳細設計書4.9.5・4.13.2)
  project_id: number | null
}

export interface ExpenseListFilters {
  account_category?: string
  payment_method?: string
  date_from?: string
  date_to?: string
}

export const expensesApi = {
  list: async (filters: ExpenseListFilters = {}): Promise<Expense[]> =>
    (await apiClient.get('/expenses', { params: filters })).data,
  get: async (id: number): Promise<Expense> => (await apiClient.get(`/expenses/${id}`)).data,
  create: async (payload: ExpensePayload): Promise<Expense> => (await apiClient.post('/expenses', payload)).data,
  update: async (id: number, payload: ExpensePayload): Promise<Expense> =>
    (await apiClient.put(`/expenses/${id}`, payload)).data,
  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/expenses/${id}`)
  },
  linkProject: async (id: number, projectId: number | null): Promise<Expense> =>
    (await apiClient.put(`/expenses/${id}/project`, { project_id: projectId })).data,
  uploadAttachment: async (id: number, file: File): Promise<Expense> => {
    const formData = new FormData()
    formData.append('file', file)
    return (
      await apiClient.post(`/expenses/${id}/attachment`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    ).data
  },
  attachmentUrl: (id: number): string => `/api/expenses/${id}/attachment`,
  summary: async (periodFrom?: string, periodTo?: string): Promise<ExpenseSummary> =>
    (
      await apiClient.get('/expenses/summary', {
        params: { period_from: periodFrom, period_to: periodTo },
      })
    ).data,
}

import { apiClient } from './client'
import type { Deadline, DeadlineCategory } from '../types'

export interface DeadlinePayload {
  name: string
  due_date: string
  category: DeadlineCategory
  memo: string | null
  is_recurring: boolean
}

export const deadlinesApi = {
  list: async (): Promise<Deadline[]> => (await apiClient.get('/deadlines')).data,
  create: async (payload: DeadlinePayload): Promise<Deadline> => (await apiClient.post('/deadlines', payload)).data,
  update: async (id: number, payload: DeadlinePayload): Promise<Deadline> =>
    (await apiClient.put(`/deadlines/${id}`, payload)).data,
  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/deadlines/${id}`)
  },
}

import { apiClient } from './client'
import type { HomeSummary } from '../types'

export const homeApi = {
  summary: async (): Promise<HomeSummary> => (await apiClient.get('/home/summary')).data,
}

import { apiClient } from './client'
import type { NotificationList, NotificationSourceType, NotificationSummary } from '../types'

export interface NotificationTarget {
  source_type: NotificationSourceType
  source_id: number
}

export const notificationsApi = {
  list: async (includeAcknowledged: boolean): Promise<NotificationList> =>
    (await apiClient.get('/notifications', { params: { include_acknowledged: includeAcknowledged } })).data,
  summary: async (): Promise<NotificationSummary> => (await apiClient.get('/notifications/summary')).data,
  acknowledge: async (target: NotificationTarget): Promise<void> => {
    await apiClient.post('/notifications/acknowledge', target)
  },
  unacknowledge: async (target: NotificationTarget): Promise<void> => {
    await apiClient.delete('/notifications/acknowledge', { data: target })
  },
}

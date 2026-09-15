import { apiClient } from './client'
import type { Client } from '../types'

export interface ClientPayload {
  name: string
  postal_code?: string | null
  address?: string | null
  contact_person?: string | null
  contact_info?: string | null
}

export const clientsApi = {
  list: async (): Promise<Client[]> => (await apiClient.get('/clients')).data,
  get: async (id: number): Promise<Client> => (await apiClient.get(`/clients/${id}`)).data,
  create: async (payload: ClientPayload): Promise<Client> => (await apiClient.post('/clients', payload)).data,
  update: async (id: number, payload: ClientPayload): Promise<Client> =>
    (await apiClient.put(`/clients/${id}`, payload)).data,
}

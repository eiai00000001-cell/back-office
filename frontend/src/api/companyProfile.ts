import { apiClient } from './client'
import type { CompanyProfile } from '../types'

export interface CompanyProfilePayload {
  name: string
  business_name?: string | null
  address?: string | null
  contact_info?: string | null
  invoice_registration_number?: string | null
}

export const companyProfileApi = {
  get: async (): Promise<CompanyProfile> => (await apiClient.get('/company-profile')).data,
  update: async (payload: CompanyProfilePayload): Promise<CompanyProfile> =>
    (await apiClient.put('/company-profile', payload)).data,
}

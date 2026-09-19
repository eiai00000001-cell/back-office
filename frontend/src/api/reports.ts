import { apiClient } from './client'
import type { ReportFormat, ReportType } from '../types'

export interface ReportDownload {
  blob: Blob
  filename: string
  recordCount: number
}

function parseFilename(disposition: string | undefined, fallback: string): string {
  const match = disposition?.match(/filename\*=UTF-8''([^;]+)/i)
  if (!match) return fallback
  try {
    return decodeURIComponent(match[1])
  } catch {
    return fallback
  }
}

export const reportsApi = {
  download: async (
    type: ReportType,
    periodFrom: string,
    periodTo: string,
    format: ReportFormat
  ): Promise<ReportDownload> => {
    const response = await apiClient.get(`/reports/${type}`, {
      params: { period_from: periodFrom, period_to: periodTo, format },
      responseType: 'blob',
    })
    return {
      blob: response.data,
      filename: parseFilename(response.headers['content-disposition'], `report.${format}`),
      recordCount: Number(response.headers['x-record-count'] ?? 0),
    }
  },
}

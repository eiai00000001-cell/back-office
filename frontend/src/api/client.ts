import axios, { type AxiosError } from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
})

export interface ApiErrorBody {
  detail?: string
}

export function extractErrorMessage(error: unknown, fallback = '処理に失敗しました。しばらくしてから再度お試しください'): string {
  const axiosError = error as AxiosError<ApiErrorBody>
  if (axiosError?.response?.data?.detail) {
    return axiosError.response.data.detail
  }
  return fallback
}

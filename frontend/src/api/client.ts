import axios, { type AxiosError } from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
})

interface ApiValidationErrorItem {
  msg?: string
  [key: string]: unknown
}

export interface ApiErrorBody {
  // バックエンド(main.py)は通常detail: stringを返す。ただし、万一FastAPIの標準422応答
  // (配列形式)がそのまま返ってきた場合でも画面描画が壊れないよう、型・実装の両面で
  // 防御的に扱う(レビュー指摘1対応)。
  detail?: string | ApiValidationErrorItem[]
}

export function extractErrorMessage(error: unknown, fallback = '処理に失敗しました。しばらくしてから再度お試しください'): string {
  const axiosError = error as AxiosError<ApiErrorBody>
  const detail = axiosError?.response?.data?.detail
  if (typeof detail === 'string' && detail) {
    return detail
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const firstMessage = detail[0]?.msg
    if (typeof firstMessage === 'string' && firstMessage) {
      return firstMessage
    }
    return fallback
  }
  return fallback
}

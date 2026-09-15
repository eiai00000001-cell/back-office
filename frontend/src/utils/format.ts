// 表示フォーマット共通処理。金額は3桁カンマ区切り、日付はYYYY-MM-DD形式(詳細設計書3章)。

export function formatCurrency(amount: number): string {
  return `${amount.toLocaleString('en-US')}円`
}

export function isOverdueDate(dateString: string | null): boolean {
  if (!dateString) return false
  const today = new Date().toISOString().slice(0, 10)
  return today > dateString
}

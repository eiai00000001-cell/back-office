// 表示フォーマット共通処理。金額は3桁カンマ区切り、日付はYYYY-MM-DD形式(詳細設計書3章)。

export function formatCurrency(amount: number): string {
  return `${amount.toLocaleString('en-US')}円`
}

export function isOverdueDate(dateString: string | null): boolean {
  if (!dateString) return false
  const today = new Date().toISOString().slice(0, 10)
  return today > dateString
}

// 財務ダッシュボード(SC-12)のグラフ軸ラベル用。"2025-10" -> "25/10"(詳細設計書3.12章、mockups準拠)。
export function formatMonthLabel(monthKey: string): string {
  const [year, month] = monthKey.split('-')
  return `${year.slice(2)}/${Number(month)}`
}

// 財務ダッシュボード(SC-12)ヘッダーの対象期間固定表示用(基本設計書4.13章、詳細設計書4.8.1章と同一算出方法)。
export function formatLast12MonthsRangeLabel(baseDate: Date = new Date()): string {
  const endYear = baseDate.getFullYear()
  const endMonth = baseDate.getMonth() + 1
  let startYear = endYear
  let startMonth = endMonth - 11
  if (startMonth <= 0) {
    startMonth += 12
    startYear -= 1
  }
  return `直近12ヶ月(${startYear}年${startMonth}月〜${endYear}年${endMonth}月)`
}

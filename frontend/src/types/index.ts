export type TaxCategory = 'STANDARD_10' | 'NON_TAXABLE' | 'OUT_OF_SCOPE'
export type ExpenseTaxCategory = TaxCategory | 'NOT_APPLICABLE'
export type QuoteStatus = 'DRAFT' | 'CONFIRMED'
export type PaymentStatus = 'UNPAID' | 'PARTIALLY_PAID' | 'PAID'
export type PaymentMethod = 'CASH' | 'CREDIT_CARD' | 'BANK_TRANSFER' | 'OTHER'

export type ProjectStatus = 'NOT_STARTED' | 'IN_PROGRESS' | 'WAITING_REVIEW' | 'DONE'
export type DueState = 'OVERDUE' | 'UPCOMING'

export const TAX_CATEGORY_LABELS: Record<TaxCategory, string> = {
  STANDARD_10: '標準10%',
  NON_TAXABLE: '非課税',
  OUT_OF_SCOPE: '不課税',
}

export const EXPENSE_TAX_CATEGORY_LABELS: Record<ExpenseTaxCategory, string> = {
  ...TAX_CATEGORY_LABELS,
  NOT_APPLICABLE: '対象外',
}

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  UNPAID: '未入金',
  PARTIALLY_PAID: '一部入金',
  PAID: '入金済み',
}

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  CASH: '現金',
  CREDIT_CARD: 'クレジットカード',
  BANK_TRANSFER: '銀行振込',
  OTHER: 'その他',
}

export const QUOTE_STATUS_LABELS: Record<QuoteStatus, string> = {
  DRAFT: '作成中',
  CONFIRMED: '確定',
}

// カンバンの列順は宣言順(詳細設計書4.9.1)
export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  NOT_STARTED: '未着手',
  IN_PROGRESS: '進行中',
  WAITING_REVIEW: '確認待ち',
  DONE: '完了',
}

export const PROJECT_STATUSES = Object.keys(PROJECT_STATUS_LABELS) as ProjectStatus[]

export const DUE_STATE_LABELS: Record<DueState, string> = {
  OVERDUE: '超過',
  UPCOMING: '接近',
}

export const ACCOUNT_CATEGORIES = [
  '旅費交通費',
  '通信費',
  '消耗品費',
  '水道光熱費',
  '地代家賃',
  '外注工賃',
  '接待交際費',
  '会議費',
  '新聞図書費',
  '支払手数料',
  '租税公課',
  '雑費',
  'その他',
] as const

export interface ItemInput {
  id?: number
  item_name: string
  quantity: number
  unit_price: number
  tax_category: TaxCategory
  // フロントエンドのみで使用する一時的な安定ID(React keyの安定化用、レビュー指摘9対応)。
  // バックエンドへの送信時は未知のフィールドとして無視される。
  clientKey?: string
}

// APIレスポンスの品目明細。quantityはDecimal型のためJSONでは文字列("1.00")で返る。
// フォームへ取り込む際は utils/items.ts の toItemInputs で数値へ正規化する。
export interface ItemResponse extends Omit<ItemInput, 'quantity' | 'unit_price'> {
  id: number
  quantity: number | string
  unit_price: number | string
  amount: number
  sort_order: number
}

export interface Client {
  id: number
  name: string
  postal_code: string | null
  address: string | null
  contact_person: string | null
  contact_info: string | null
}

export interface CompanyProfile {
  name: string
  business_name: string | null
  address: string | null
  contact_info: string | null
  invoice_registration_number: string | null
}

export interface Payment {
  id: number
  invoice_id: number
  payment_date: string
  amount: number
  remarks: string | null
}

export interface Invoice {
  id: number
  invoice_number: string
  client_id: number
  client_name: string
  issue_date: string | null
  due_date: string | null
  source_quote_id: number | null
  project_id: number | null
  project_name: string | null
  items: ItemResponse[]
  subtotal_amount: number
  tax_amount: number
  total_amount: number
  remarks: string | null
  payments: Payment[]
  payment_status: PaymentStatus
  is_overdue: boolean
}

export interface InvoiceListItem {
  id: number
  invoice_number: string
  client_id: number
  client_name: string
  issue_date: string | null
  due_date: string | null
  total_amount: number
  paid_amount: number
  project_id: number | null
  project_name: string | null
  payment_status: PaymentStatus
  is_overdue: boolean
}

export interface Quote {
  id: number
  quote_number: string
  client_id: number
  client_name: string
  issue_date: string | null
  expiry_date: string | null
  status: QuoteStatus
  items: ItemResponse[]
  subtotal_amount: number
  tax_amount: number
  total_amount: number
  remarks: string | null
  project_id: number | null
  project_name: string | null
  converted_invoice_id: number | null
  converted_invoice_number: string | null
}

export interface QuoteListItem {
  id: number
  quote_number: string
  client_id: number
  client_name: string
  issue_date: string | null
  expiry_date: string | null
  total_amount: number
  status: QuoteStatus
  project_id: number | null
  project_name: string | null
}

export interface Expense {
  id: number
  expense_date: string
  account_category: string
  amount: number
  tax_category: ExpenseTaxCategory
  payee: string | null
  payment_method: PaymentMethod | null
  memo: string | null
  attachment_path: string | null
  attachment_original_name: string | null
  project_id: number | null
  project_name: string | null
}

export interface ExpenseSummary {
  by_category: { account_category: string; count: number; total_amount: number }[]
  by_month: { year_month: string; total_amount: number }[]
}

export interface HomeSummary {
  unpaid_count: number
  overdue_count: number
}

// 財務ダッシュボード(F-07、SC-12、イテレーション2)向け型定義

export interface DashboardMonthlyAmount {
  month: string
  amount: number
}

export interface DashboardQuoteMonthlySummary {
  month: string
  count: number
  total_amount: number
}

export interface DashboardCategorySummary {
  account_category: string
  count: number
  total_amount: number
}

export interface SalesAndPaymentsSummary {
  sales: DashboardMonthlyAmount[]
  payments: DashboardMonthlyAmount[]
}

export interface DashboardExpenseSummary {
  monthly: DashboardMonthlyAmount[]
  by_category: DashboardCategorySummary[]
}

export interface ProfitLossSummary {
  monthly: DashboardMonthlyAmount[]
}

export interface QuoteStatusSummary {
  monthly: DashboardQuoteMonthlySummary[]
  conversion_rate: number | null
}

// 案件・プロジェクト管理(F-08、SC-13〜15、イテレーション3・段階1)向け型定義

export interface Project {
  id: number
  name: string
  client_id: number | null
  client_name: string | null
  status: ProjectStatus
  due_date: string | null
  description: string | null
}

export interface ProjectListItem extends Project {
  quote_count: number
  invoice_count: number
  due_state: DueState | null
}

export interface ProjectDetail extends ProjectListItem {
  quotes: {
    id: number
    quote_number: string
    issue_date: string | null
    expiry_date: string | null
    total_amount: number
    status: QuoteStatus
  }[]
  invoices: {
    id: number
    invoice_number: string
    issue_date: string | null
    due_date: string | null
    total_amount: number
    payment_status: PaymentStatus
  }[]
  summary: {
    quote_count: number
    quote_total: number
    invoice_count: number
    invoice_total: number
    paid_total: number
    unpaid_total: number
  }
}

// リマインダー/通知(F-09、SC-16・17、イテレーション3・段階2)向け型定義

export type NotificationSourceType = 'INVOICE_DUE' | 'QUOTE_EXPIRY' | 'PROJECT_DUE' | 'DEADLINE'
export type DeadlineCategory = 'TAX_FILING' | 'CONTRACT_RENEWAL' | 'OTHER'

// 通知の種類の表示名(mockups SC-01・SC-16)
export const NOTIFICATION_KIND_LABELS: Record<NotificationSourceType, string> = {
  INVOICE_DUE: '請求書の支払期限',
  QUOTE_EXPIRY: '見積書の有効期限',
  PROJECT_DUE: '案件の納期',
  DEADLINE: '登録した期限',
}

export const DEADLINE_CATEGORY_LABELS: Record<DeadlineCategory, string> = {
  TAX_FILING: '確定申告',
  CONTRACT_RENEWAL: '契約更新',
  OTHER: 'その他',
}

export interface NotificationItem {
  source_type: NotificationSourceType
  source_id: number
  title: string
  due_date: string
  state: DueState
  days_diff: number
  link: string
  category: DeadlineCategory | null
  acknowledged: boolean
}

export interface NotificationList {
  items: NotificationItem[]
  errors: NotificationSourceType[]
}

export interface NotificationSummary {
  unacknowledged_count: number
  overdue_count: number
  items: NotificationItem[]
  errors: NotificationSourceType[]
}

export interface Deadline {
  id: number
  name: string
  due_date: string
  category: DeadlineCategory
  memo: string | null
  is_recurring: boolean
  due_state: DueState | null
}

// レポート出力(F-10、SC-18)向け型定義

export type ReportType =
  | 'invoices'
  | 'payments'
  | 'quotes'
  | 'expenses'
  | 'monthly-pl'
  | 'projects'
  | 'accounting-export'
export type ReportFormat = 'csv' | 'pdf'

export const REPORT_TYPES: { value: ReportType; name: string; formats: string; basis: string }[] = [
  { value: 'invoices', name: '請求書一覧', formats: 'CSV', basis: '発行日' },
  { value: 'payments', name: '入金記録', formats: 'CSV', basis: '入金日' },
  { value: 'quotes', name: '見積書一覧', formats: 'CSV', basis: '発行日' },
  { value: 'expenses', name: '経費一覧', formats: 'CSV', basis: '発生日' },
  { value: 'monthly-pl', name: '月次損益集計レポート', formats: 'PDF または CSV', basis: '請求書の発行日・経費の発生日' },
  { value: 'projects', name: '案件別サマリー', formats: 'CSV', basis: '案件の納期または紐付き請求書の発行日' },
  {
    value: 'accounting-export',
    name: '会計ソフト連携用エクスポート(汎用CSV)',
    formats: 'CSV',
    basis: '売上は発行日・経費は発生日',
  },
]

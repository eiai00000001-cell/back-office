import { Box, Card, Container, Grid, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import AppHeader from '../components/AppHeader'
import { dashboardApi } from '../api/dashboard'
import { formatCurrency, formatLast12MonthsRangeLabel, formatMonthLabel } from '../utils/format'
import type {
  DashboardExpenseSummary,
  ProfitLossSummary,
  QuoteStatusSummary,
  SalesAndPaymentsSummary,
} from '../types'

// 財務ダッシュボード(F-07、SC-12、イテレーション2)。詳細設計書3.12章・4.8章。
// 4区画はそれぞれ独立したAPIからデータを取得し、いずれか1区画が失敗しても他区画には影響させない
// (機能仕様書F-07例外仕様、4.8.6章)。

const COLOR_PRIMARY = '#2c5f7c'
const COLOR_SERIES2 = '#9fc3d6'
const COLOR_EXPENSE = '#c97b3d'
const COLOR_POSITIVE = '#2f8f5b'
const COLOR_NEGATIVE = '#c0392b'
const CATEGORY_COLORS = ['#2c5f7c', '#4f8fb0', '#7fb3d1', '#c0392b', '#e08e45', '#8e6fc7']

const sectionTitleSx = {
  fontWeight: 600,
  mb: 0.5,
  pb: 1,
  borderBottom: '1px solid #dde1e6',
}

const yAxisTickFormatter = (value: number) => value.toLocaleString('en-US')
// Recharts v3のTooltip formatter/labelFormatterはvalue: ValueType | undefined、label: ReactNodeを
// 受け取る型のため、unknownで受けてから変換する(呼び出し側の型に反変で適合させる)。
const currencyTooltipFormatter = (value: unknown): string => formatCurrency(Number(value) || 0)
const monthLabelTooltipFormatter = (label: unknown): string => formatMonthLabel(String(label ?? ''))

function DashboardErrorMessage() {
  return (
    <Box sx={{ py: 4, textAlign: 'center', color: 'text.secondary', fontSize: 13 }}>
      情報を取得できませんでした
    </Box>
  )
}

function DashboardLoading() {
  return (
    <Box sx={{ py: 4, textAlign: 'center', color: 'text.secondary', fontSize: 13 }}>
      読み込み中です…
    </Box>
  )
}

function SalesAndPaymentsSection({ data }: { data: SalesAndPaymentsSummary }) {
  const chartData = data.sales.map((item, index) => ({
    month: item.month,
    sales: item.amount,
    payments: data.payments[index]?.amount ?? 0,
  }))
  const totalSales = data.sales.reduce((sum, item) => sum + item.amount, 0)
  const totalPayments = data.payments.reduce((sum, item) => sum + item.amount, 0)

  return (
    <Box sx={{ mt: 1.5 }}>
      <Typography sx={{ fontSize: 12, color: 'text.secondary', mb: 1 }}>
        直近12ヶ月合計 売上: <strong>{formatCurrency(totalSales)}</strong>
        <Box component="span" sx={{ mx: 1.5, color: '#dde1e6' }}>
          |
        </Box>
        入金: <strong>{formatCurrency(totalPayments)}</strong>
      </Typography>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData}>
          <XAxis dataKey="month" tickFormatter={formatMonthLabel} fontSize={11} />
          <YAxis fontSize={11} width={70} tickFormatter={yAxisTickFormatter} />
          <Tooltip formatter={currencyTooltipFormatter} labelFormatter={monthLabelTooltipFormatter} />
          <Legend />
          <Bar dataKey="sales" name="売上(発行日基準)" fill={COLOR_PRIMARY} />
          <Bar dataKey="payments" name="入金額(入金日基準・参考指標)" fill={COLOR_SERIES2} />
        </BarChart>
      </ResponsiveContainer>
    </Box>
  )
}

function ExpenseSection({ data }: { data: DashboardExpenseSummary }) {
  const totalExpense = data.monthly.reduce((sum, item) => sum + item.amount, 0)
  const totalCategoryAmount = data.by_category.reduce((sum, item) => sum + item.total_amount, 0)

  return (
    <Box sx={{ mt: 1.5 }}>
      <Typography sx={{ fontSize: 12, color: 'text.secondary', mb: 1 }}>
        直近12ヶ月合計経費: <strong>{formatCurrency(totalExpense)}</strong>
      </Typography>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data.monthly}>
          <XAxis dataKey="month" tickFormatter={formatMonthLabel} fontSize={11} />
          <YAxis fontSize={11} width={70} tickFormatter={yAxisTickFormatter} />
          <Tooltip formatter={currencyTooltipFormatter} labelFormatter={monthLabelTooltipFormatter} />
          <Bar dataKey="amount" name="月次経費合計(発生日基準)" fill={COLOR_EXPENSE} />
        </BarChart>
      </ResponsiveContainer>

      <Typography sx={{ fontSize: 12, color: 'text.secondary', mt: 2.5, mb: 1 }}>
        勘定科目別内訳(直近12ヶ月)
      </Typography>
      {data.by_category.length === 0 ? (
        <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>該当する経費データがありません</Typography>
      ) : (
        <Stack direction="row" spacing={3} alignItems="center" flexWrap="wrap">
          <Box sx={{ width: 160, height: 160, flexShrink: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.by_category} dataKey="total_amount" nameKey="account_category" outerRadius={70}>
                  {data.by_category.map((entry, index) => (
                    <Cell key={entry.account_category} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={currencyTooltipFormatter} />
              </PieChart>
            </ResponsiveContainer>
          </Box>
          <Box sx={{ fontSize: 12, color: 'text.secondary', flex: 1, minWidth: 180 }}>
            {data.by_category.map((item, index) => (
              <Stack
                key={item.account_category}
                direction="row"
                justifyContent="space-between"
                spacing={1.5}
                sx={{ py: 0.375 }}
              >
                <Stack direction="row" alignItems="center" spacing={0.75}>
                  <Box
                    sx={{
                      width: 9,
                      height: 9,
                      borderRadius: '2px',
                      backgroundColor: CATEGORY_COLORS[index % CATEGORY_COLORS.length],
                      flexShrink: 0,
                    }}
                  />
                  <span>{item.account_category}</span>
                </Stack>
                <Box sx={{ color: 'text.primary', whiteSpace: 'nowrap' }}>
                  {formatCurrency(item.total_amount)}
                  {totalCategoryAmount > 0 && ` (${Math.round((item.total_amount / totalCategoryAmount) * 100)}%)`}
                </Box>
              </Stack>
            ))}
          </Box>
        </Stack>
      )}
    </Box>
  )
}

function ProfitLossSection({ data }: { data: ProfitLossSummary }) {
  const totalProfit = data.monthly.reduce((sum, item) => sum + item.amount, 0)

  return (
    <Box sx={{ mt: 1.5 }}>
      <Typography sx={{ fontSize: 12, color: 'text.secondary', mb: 1 }}>
        直近12ヶ月合計損益:{' '}
        <strong style={{ color: totalProfit >= 0 ? COLOR_POSITIVE : COLOR_NEGATIVE }}>
          {totalProfit >= 0 ? '+' : ''}
          {formatCurrency(totalProfit)}
        </strong>
      </Typography>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data.monthly}>
          <XAxis dataKey="month" tickFormatter={formatMonthLabel} fontSize={11} />
          <YAxis fontSize={11} width={70} tickFormatter={yAxisTickFormatter} />
          <Tooltip formatter={currencyTooltipFormatter} labelFormatter={monthLabelTooltipFormatter} />
          <Bar dataKey="amount" name="月次損益">
            {data.monthly.map((item) => (
              <Cell key={item.month} fill={item.amount >= 0 ? COLOR_POSITIVE : COLOR_NEGATIVE} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <Stack direction="row" spacing={2} sx={{ mt: 1.25, fontSize: 12, color: 'text.secondary' }}>
        <Stack direction="row" alignItems="center" spacing={0.75}>
          <Box sx={{ width: 9, height: 9, borderRadius: '2px', backgroundColor: COLOR_POSITIVE }} />
          <span>黒字月(売上-経費 ≧ 0円)</span>
        </Stack>
        <Stack direction="row" alignItems="center" spacing={0.75}>
          <Box sx={{ width: 9, height: 9, borderRadius: '2px', backgroundColor: COLOR_NEGATIVE }} />
          <span>赤字月(売上-経費 &lt; 0円)</span>
        </Stack>
      </Stack>
    </Box>
  )
}

function QuoteStatusSection({ data }: { data: QuoteStatusSummary }) {
  const totalCount = data.monthly.reduce((sum, item) => sum + item.count, 0)
  const totalAmount = data.monthly.reduce((sum, item) => sum + item.total_amount, 0)
  const conversionRateLabel =
    data.conversion_rate === null ? '-' : `${Math.round(data.conversion_rate * 100)}%`

  return (
    <Stack direction="row" spacing={3} sx={{ mt: 1.5 }} flexWrap="wrap" alignItems="stretch">
      <Box sx={{ flex: 1, minWidth: 220 }}>
        <Typography sx={{ fontSize: 12, color: 'text.secondary', mb: 1 }}>
          月次見積件数(合計{totalCount}件)
        </Typography>
        <ResponsiveContainer width="100%" height={110}>
          <BarChart data={data.monthly}>
            <XAxis dataKey="month" tickFormatter={formatMonthLabel} fontSize={11} />
            <YAxis fontSize={11} width={40} allowDecimals={false} />
            <Tooltip labelFormatter={monthLabelTooltipFormatter} />
            <Bar dataKey="count" name="月次見積件数" fill={COLOR_PRIMARY} />
          </BarChart>
        </ResponsiveContainer>

        <Typography sx={{ fontSize: 12, color: 'text.secondary', mt: 2, mb: 1 }}>
          月次見積金額合計(合計{formatCurrency(totalAmount)})
        </Typography>
        <ResponsiveContainer width="100%" height={110}>
          <BarChart data={data.monthly}>
            <XAxis dataKey="month" tickFormatter={formatMonthLabel} fontSize={11} />
            <YAxis fontSize={11} width={40} tickFormatter={yAxisTickFormatter} />
            <Tooltip formatter={currencyTooltipFormatter} labelFormatter={monthLabelTooltipFormatter} />
            <Bar dataKey="total_amount" name="月次見積金額合計" fill={COLOR_SERIES2} />
          </BarChart>
        </ResponsiveContainer>
      </Box>
      <Box
        sx={{
          backgroundColor: '#eef4f7',
          borderRadius: 1,
          px: 3,
          py: 2,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minWidth: 150,
        }}
      >
        <Typography sx={{ fontSize: 32, fontWeight: 700, color: 'primary.main' }}>{conversionRateLabel}</Typography>
        <Typography sx={{ fontSize: 12, color: 'text.secondary', mt: 0.5, textAlign: 'center' }}>
          見積成約率
          <br />
          (見積→請求書変換件数
          <br />
          ÷見積作成件数)
        </Typography>
      </Box>
    </Stack>
  )
}

export default function DashboardPage() {
  const salesQuery = useQuery({
    queryKey: ['dashboard-sales-and-payments'],
    queryFn: dashboardApi.salesAndPayments,
  })
  const expenseQuery = useQuery({ queryKey: ['dashboard-expenses'], queryFn: dashboardApi.expenses })
  const profitLossQuery = useQuery({ queryKey: ['dashboard-profit-loss'], queryFn: dashboardApi.profitLoss })
  const quotesQuery = useQuery({ queryKey: ['dashboard-quotes'], queryFn: dashboardApi.quotes })

  return (
    <Box>
      <AppHeader backTo="/" backLabel="← ホームへ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 0.5 }}>
          財務ダッシュボード
        </Typography>
        <Typography sx={{ fontSize: 13, color: 'text.secondary', mb: 2.5 }}>
          対象期間: {formatLast12MonthsRangeLabel()} ※期間の絞り込みはできません
        </Typography>

        <Grid container spacing={2.5}>
          <Grid item xs={12}>
            <Card variant="outlined" sx={{ p: 2.5 }}>
              <Typography sx={sectionTitleSx}>売上・入金状況</Typography>
              {salesQuery.isError ? (
                <DashboardErrorMessage />
              ) : !salesQuery.data ? (
                <DashboardLoading />
              ) : (
                <SalesAndPaymentsSection data={salesQuery.data} />
              )}
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card variant="outlined" sx={{ p: 2.5 }}>
              <Typography sx={sectionTitleSx}>経費</Typography>
              {expenseQuery.isError ? (
                <DashboardErrorMessage />
              ) : !expenseQuery.data ? (
                <DashboardLoading />
              ) : (
                <ExpenseSection data={expenseQuery.data} />
              )}
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card variant="outlined" sx={{ p: 2.5, height: '100%' }}>
              <Typography sx={sectionTitleSx}>損益(収支)</Typography>
              {profitLossQuery.isError ? (
                <DashboardErrorMessage />
              ) : !profitLossQuery.data ? (
                <DashboardLoading />
              ) : (
                <ProfitLossSection data={profitLossQuery.data} />
              )}
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card variant="outlined" sx={{ p: 2.5, height: '100%' }}>
              <Typography sx={sectionTitleSx}>見積状況</Typography>
              {quotesQuery.isError ? (
                <DashboardErrorMessage />
              ) : !quotesQuery.data ? (
                <DashboardLoading />
              ) : (
                <QuoteStatusSection data={quotesQuery.data} />
              )}
            </Card>
          </Grid>
        </Grid>
      </Container>
    </Box>
  )
}

import { useState } from 'react'
import { Box, Card, Container, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { expensesApi } from '../api/expenses'
import { formatCurrency } from '../utils/format'

function defaultPeriod() {
  const today = new Date()
  const to = today.toISOString().slice(0, 7)
  const fromDate = new Date(today.getFullYear(), today.getMonth() - 11, 1)
  const from = fromDate.toISOString().slice(0, 7)
  return { from, to }
}

export default function ExpenseSummaryPage() {
  const [{ from, to }] = useState(defaultPeriod)
  const [periodFrom, setPeriodFrom] = useState(from)
  const [periodTo, setPeriodTo] = useState(to)

  const { data } = useQuery({
    queryKey: ['expense-summary', periodFrom, periodTo],
    queryFn: () => expensesApi.summary(periodFrom, periodTo),
  })

  const categoryTotal = data?.by_category.reduce((sum, c) => sum + c.total_amount, 0) ?? 0
  const categoryCount = data?.by_category.reduce((sum, c) => sum + c.count, 0) ?? 0

  return (
    <Box>
      <AppHeader backTo="/expenses" backLabel="← 経費一覧へ" />
      <Container maxWidth="md" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          経費集計
        </Typography>

        <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
          <Typography sx={{ fontWeight: 600, mb: 1.5, pb: 1, borderBottom: '1px solid #dde1e6' }}>集計期間</Typography>
          <Stack direction="row" spacing={2}>
            <TextField
              label="集計対象年月(From)"
              type="month"
              InputLabelProps={{ shrink: true }}
              value={periodFrom}
              onChange={(e) => setPeriodFrom(e.target.value)}
            />
            <TextField
              label="集計対象年月(To)"
              type="month"
              InputLabelProps={{ shrink: true }}
              value={periodTo}
              onChange={(e) => setPeriodTo(e.target.value)}
            />
          </Stack>
        </Card>

        <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
          <Typography sx={{ fontWeight: 600, mb: 1.5, pb: 1, borderBottom: '1px solid #dde1e6' }}>勘定科目別集計</Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>勘定科目</TableCell>
                <TableCell align="right">件数</TableCell>
                <TableCell align="right">合計金額</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data?.by_category.map((c) => (
                <TableRow key={c.account_category}>
                  <TableCell>{c.account_category}</TableCell>
                  <TableCell align="right">{c.count}</TableCell>
                  <TableCell align="right">{formatCurrency(c.total_amount)}</TableCell>
                </TableRow>
              ))}
              <TableRow>
                <TableCell sx={{ fontWeight: 700, borderTop: '2px solid #dde1e6' }}>合計</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700, borderTop: '2px solid #dde1e6' }}>
                  {categoryCount}
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 700, borderTop: '2px solid #dde1e6' }}>
                  {formatCurrency(categoryTotal)}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Card>

        <Card variant="outlined" sx={{ p: 2.5 }}>
          <Typography sx={{ fontWeight: 600, mb: 1.5, pb: 1, borderBottom: '1px solid #dde1e6' }}>期間別(月単位)集計</Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>年月</TableCell>
                <TableCell align="right">合計金額</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {[...(data?.by_month ?? [])]
                .sort((a, b) => (a.year_month < b.year_month ? 1 : -1))
                .map((m) => (
                  <TableRow key={m.year_month}>
                    <TableCell>{m.year_month}</TableCell>
                    <TableCell align="right">{formatCurrency(m.total_amount)}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </Card>
      </Container>
    </Box>
  )
}

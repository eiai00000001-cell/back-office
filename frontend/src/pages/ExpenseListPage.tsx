import { useMemo, useState } from 'react'
import {
  Box,
  Button,
  Card,
  Container,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { expensesApi } from '../api/expenses'
import { ACCOUNT_CATEGORIES, EXPENSE_TAX_CATEGORY_LABELS, PAYMENT_METHOD_LABELS, type PaymentMethod } from '../types'
import { formatCurrency } from '../utils/format'

export default function ExpenseListPage() {
  const navigate = useNavigate()
  const [accountCategory, setAccountCategory] = useState('')
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | ''>('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const filters = useMemo(
    () => ({
      account_category: accountCategory || undefined,
      payment_method: paymentMethod || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
    [accountCategory, paymentMethod, dateFrom, dateTo]
  )
  const { data: expenses } = useQuery({ queryKey: ['expenses', filters], queryFn: () => expensesApi.list(filters) })

  return (
    <Box>
      <AppHeader backTo="/" backLabel="← ホームへ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          経費一覧・検索
        </Typography>
        <Card variant="outlined" sx={{ p: 2.5 }}>
          <Toolbar disableGutters sx={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 1.5, mb: 2 }}>
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'flex-end' }}>
              <TextField select size="small" label="勘定科目" sx={{ minWidth: 150 }} value={accountCategory} onChange={(e) => setAccountCategory(e.target.value)}>
                <MenuItem value="">すべて</MenuItem>
                {ACCOUNT_CATEGORIES.map((c) => (
                  <MenuItem key={c} value={c}>
                    {c}
                  </MenuItem>
                ))}
              </TextField>
              <TextField select size="small" label="支払方法" sx={{ minWidth: 150 }} value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod | '')}>
                <MenuItem value="">すべて</MenuItem>
                {Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                ))}
              </TextField>
              <TextField label="期間(From)" type="date" size="small" InputLabelProps={{ shrink: true }} value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
              <TextField label="期間(To)" type="date" size="small" InputLabelProps={{ shrink: true }} value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button variant="outlined" onClick={() => navigate('/expenses/summary')}>
                集計を見る
              </Button>
              <Button variant="contained" onClick={() => navigate('/expenses/new')}>
                新規登録
              </Button>
            </Box>
          </Toolbar>

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>発生日</TableCell>
                <TableCell>勘定科目</TableCell>
                <TableCell align="right">金額</TableCell>
                <TableCell>税区分</TableCell>
                <TableCell>支払先</TableCell>
                <TableCell>支払方法</TableCell>
                <TableCell>領収書</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {expenses?.map((expense) => (
                <TableRow key={expense.id} hover onClick={() => navigate(`/expenses/${expense.id}`)} sx={{ cursor: 'pointer' }}>
                  <TableCell>{expense.expense_date}</TableCell>
                  <TableCell>{expense.account_category}</TableCell>
                  <TableCell align="right">{formatCurrency(expense.amount)}</TableCell>
                  <TableCell>{EXPENSE_TAX_CATEGORY_LABELS[expense.tax_category]}</TableCell>
                  <TableCell>{expense.payee ?? ''}</TableCell>
                  <TableCell>{expense.payment_method ? PAYMENT_METHOD_LABELS[expense.payment_method] : ''}</TableCell>
                  <TableCell>
                    {expense.attachment_path ? (
                      <Box
                        component="a"
                        href={expensesApi.attachmentUrl(expense.id)}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        sx={{
                          color: 'primary.main',
                          fontWeight: 600,
                          fontSize: 12,
                          border: '1px solid',
                          borderColor: 'primary.main',
                          borderRadius: '3px',
                          px: 0.75,
                          py: 0.25,
                        }}
                      >
                        表示
                      </Box>
                    ) : (
                      <Typography sx={{ color: '#c9ced3', fontSize: 12 }}>なし</Typography>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </Container>
    </Box>
  )
}

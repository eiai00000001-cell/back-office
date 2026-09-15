import { useMemo, useState } from 'react'
import {
  Box,
  Button,
  Card,
  Chip,
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
import { invoicesApi } from '../api/invoices'
import { clientsApi } from '../api/clients'
import { PAYMENT_STATUS_LABELS, type PaymentStatus } from '../types'
import { formatCurrency } from '../utils/format'
import { PAYMENT_STATUS_COLORS, OVERDUE_BACKGROUND } from '../theme'

export default function InvoiceListPage() {
  const navigate = useNavigate()
  const [clientId, setClientId] = useState<number | ''>('')
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus | ''>('')

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientsApi.list })
  const filters = useMemo(
    () => ({
      client_id: clientId === '' ? undefined : clientId,
      payment_status: paymentStatus === '' ? undefined : paymentStatus,
    }),
    [clientId, paymentStatus]
  )
  const { data: invoices } = useQuery({
    queryKey: ['invoices', filters],
    queryFn: () => invoicesApi.list(filters),
  })

  return (
    <Box>
      <AppHeader backTo="/" backLabel="← ホームへ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          請求書一覧
        </Typography>
        <Card variant="outlined" sx={{ p: 2.5 }}>
          <Toolbar disableGutters sx={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 1.5, mb: 2 }}>
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
              <TextField
                select
                size="small"
                label="取引先"
                sx={{ minWidth: 180 }}
                value={clientId}
                onChange={(e) => setClientId(e.target.value === '' ? '' : Number(e.target.value))}
              >
                <MenuItem value="">すべて</MenuItem>
                {clients?.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                size="small"
                label="入金ステータス"
                sx={{ minWidth: 180 }}
                value={paymentStatus}
                onChange={(e) => setPaymentStatus(e.target.value as PaymentStatus | '')}
              >
                <MenuItem value="">すべて</MenuItem>
                {Object.entries(PAYMENT_STATUS_LABELS).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                ))}
              </TextField>
            </Box>
            <Button variant="contained" onClick={() => navigate('/invoices/new')}>
              新規作成
            </Button>
          </Toolbar>

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>請求書番号</TableCell>
                <TableCell>取引先名</TableCell>
                <TableCell>発行日</TableCell>
                <TableCell>支払期限</TableCell>
                <TableCell align="right">合計金額</TableCell>
                <TableCell>入金ステータス</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {invoices?.map((invoice) => (
                <TableRow
                  key={invoice.id}
                  hover
                  onClick={() => navigate(`/invoices/${invoice.id}`)}
                  sx={{ cursor: 'pointer', backgroundColor: invoice.is_overdue ? OVERDUE_BACKGROUND : undefined }}
                >
                  <TableCell>{invoice.invoice_number}</TableCell>
                  <TableCell>{invoice.client_name}</TableCell>
                  <TableCell>{invoice.issue_date ?? '-'}</TableCell>
                  <TableCell>
                    {invoice.due_date ?? '-'}
                    {invoice.is_overdue && (
                      <Typography component="span" sx={{ color: 'error.main', fontSize: 12, fontWeight: 600, ml: 0.75 }}>
                        期限超過
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell align="right">{formatCurrency(invoice.total_amount)}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={PAYMENT_STATUS_LABELS[invoice.payment_status]}
                      sx={{ backgroundColor: PAYMENT_STATUS_COLORS[invoice.payment_status], color: '#fff' }}
                    />
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

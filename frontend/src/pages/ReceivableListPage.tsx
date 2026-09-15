import { Box, Card, Chip, Container, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { invoicesApi } from '../api/invoices'
import { PAYMENT_STATUS_LABELS } from '../types'
import { formatCurrency } from '../utils/format'
import { PAYMENT_STATUS_COLORS, OVERDUE_BACKGROUND } from '../theme'

export default function ReceivableListPage() {
  const navigate = useNavigate()
  const { data: invoices } = useQuery({ queryKey: ['invoices', {}], queryFn: () => invoicesApi.list() })
  const receivables = invoices?.filter((i) => i.payment_status !== 'PAID') ?? []

  return (
    <Box>
      <AppHeader backTo="/" backLabel="← ホームへ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          売掛金一覧
        </Typography>
        <Card variant="outlined" sx={{ p: 2.5 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>取引先</TableCell>
                <TableCell>請求書番号</TableCell>
                <TableCell align="right">請求金額</TableCell>
                <TableCell align="right">入金済み金額</TableCell>
                <TableCell>入金ステータス</TableCell>
                <TableCell>支払期限超過</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {receivables.map((invoice) => (
                <TableRow
                  key={invoice.id}
                  hover
                  onClick={() => navigate(`/invoices/${invoice.id}`)}
                  sx={{ cursor: 'pointer', backgroundColor: invoice.is_overdue ? OVERDUE_BACKGROUND : undefined }}
                >
                  <TableCell>{invoice.client_name}</TableCell>
                  <TableCell>{invoice.invoice_number}</TableCell>
                  <TableCell align="right">{formatCurrency(invoice.total_amount)}</TableCell>
                  <TableCell align="right">{formatCurrency(invoice.paid_amount)}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={PAYMENT_STATUS_LABELS[invoice.payment_status]}
                      sx={{ backgroundColor: PAYMENT_STATUS_COLORS[invoice.payment_status], color: '#fff' }}
                    />
                  </TableCell>
                  <TableCell>
                    {invoice.is_overdue ? (
                      <Typography component="span" sx={{ color: 'error.main', fontSize: 12, fontWeight: 600 }}>
                        超過
                      </Typography>
                    ) : (
                      '-'
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

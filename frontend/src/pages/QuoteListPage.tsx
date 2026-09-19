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
import { quotesApi } from '../api/quotes'
import { clientsApi } from '../api/clients'
import { QUOTE_STATUS_LABELS, type QuoteStatus } from '../types'
import { formatCurrency } from '../utils/format'
import { QUOTE_STATUS_COLORS } from '../theme'

export default function QuoteListPage() {
  const navigate = useNavigate()
  const [clientId, setClientId] = useState<number | ''>('')
  const [status, setStatus] = useState<QuoteStatus | ''>('')

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientsApi.list })
  const filters = useMemo(
    () => ({
      client_id: clientId === '' ? undefined : clientId,
      status: status === '' ? undefined : status,
    }),
    [clientId, status]
  )
  const { data: quotes } = useQuery({ queryKey: ['quotes', filters], queryFn: () => quotesApi.list(filters) })

  return (
    <Box>
      <AppHeader backTo="/" backLabel="← ホームへ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          見積書一覧
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
                label="ステータス"
                sx={{ minWidth: 180 }}
                value={status}
                onChange={(e) => setStatus(e.target.value as QuoteStatus | '')}
              >
                <MenuItem value="">すべて</MenuItem>
                {Object.entries(QUOTE_STATUS_LABELS).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                ))}
              </TextField>
            </Box>
            <Button variant="contained" onClick={() => navigate('/quotes/new')}>
              新規作成
            </Button>
          </Toolbar>

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>見積書番号</TableCell>
                <TableCell>取引先名</TableCell>
                <TableCell>案件</TableCell>
                <TableCell>発行日</TableCell>
                <TableCell>有効期限</TableCell>
                <TableCell align="right">合計金額</TableCell>
                <TableCell>ステータス</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {quotes?.map((quote) => (
                <TableRow key={quote.id} hover onClick={() => navigate(`/quotes/${quote.id}`)} sx={{ cursor: 'pointer' }}>
                  <TableCell>{quote.quote_number}</TableCell>
                  <TableCell>{quote.client_name}</TableCell>
                  <TableCell>{quote.project_name ?? ''}</TableCell>
                  <TableCell>{quote.issue_date ?? '-'}</TableCell>
                  <TableCell>{quote.expiry_date ?? '-'}</TableCell>
                  <TableCell align="right">{formatCurrency(quote.total_amount)}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={QUOTE_STATUS_LABELS[quote.status]}
                      sx={{ backgroundColor: QUOTE_STATUS_COLORS[quote.status], color: '#fff' }}
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

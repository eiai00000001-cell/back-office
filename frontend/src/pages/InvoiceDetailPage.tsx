import { useEffect, useState } from 'react'
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  Container,
  Link as MuiLink,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useNavigate, useParams, Link as RouterLink } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import ItemsEditor, { createEmptyItem, validateItems } from '../components/ItemsEditor'
import { clientsApi } from '../api/clients'
import { invoicesApi, type InvoicePayload } from '../api/invoices'
import { extractErrorMessage } from '../api/client'
import type { ItemInput } from '../types'
import { formatCurrency } from '../utils/format'

export default function InvoiceDetailPage() {
  const { id } = useParams()
  const isNew = id === undefined || id === 'new'
  const invoiceId = isNew ? undefined : Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientsApi.list })
  const { data: invoice } = useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: () => invoicesApi.get(invoiceId as number),
    enabled: !isNew,
  })

  const [clientId, setClientId] = useState<number | null>(null)
  const [issueDate, setIssueDate] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [items, setItems] = useState<ItemInput[]>([createEmptyItem()])
  const [remarks, setRemarks] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10))
  const [paymentAmount, setPaymentAmount] = useState<number | ''>('')
  const [paymentRemarks, setPaymentRemarks] = useState('')

  useEffect(() => {
    if (invoice) {
      setClientId(invoice.client_id)
      setIssueDate(invoice.issue_date ?? '')
      setDueDate(invoice.due_date ?? '')
      setItems(invoice.items.map((i) => ({ ...i, clientKey: String(i.id) })))
      setRemarks(invoice.remarks ?? '')
    }
  }, [invoice])

  const saveMutation = useMutation({
    mutationFn: (payload: InvoicePayload) =>
      isNew ? invoicesApi.create(payload) : invoicesApi.update(invoiceId as number, payload),
    onSuccess: (saved) => {
      setErrorMessage(null)
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
      if (isNew) {
        navigate(`/invoices/${saved.id}`, { replace: true })
      } else {
        queryClient.invalidateQueries({ queryKey: ['invoice', invoiceId] })
      }
    },
    onError: (error) => setErrorMessage(extractErrorMessage(error)),
  })

  const paymentMutation = useMutation({
    mutationFn: (force: boolean) =>
      invoicesApi.addPayment(invoiceId as number, {
        payment_date: paymentDate,
        amount: Number(paymentAmount),
        remarks: paymentRemarks || null,
        force,
      }),
    onSuccess: () => {
      setErrorMessage(null)
      setPaymentAmount('')
      setPaymentRemarks('')
      queryClient.invalidateQueries({ queryKey: ['invoice', invoiceId] })
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
    onError: (error: unknown) => {
      const message = extractErrorMessage(error, '')
      if (message.includes('超過')) {
        if (window.confirm(message + ' 登録しますか?')) {
          paymentMutation.mutate(true)
          return
        }
        return
      }
      setErrorMessage(extractErrorMessage(error))
    },
  })

  const itemsErrorMessage = validateItems(items)

  const handleSave = () => {
    if (clientId === null) {
      setErrorMessage('取引先を選択してください')
      return
    }
    if (itemsErrorMessage) {
      setErrorMessage(itemsErrorMessage)
      return
    }
    saveMutation.mutate({
      client_id: clientId,
      issue_date: issueDate || null,
      due_date: dueDate || null,
      items,
      remarks: remarks || null,
    })
  }

  const showDatesMissingNotice = !isNew && invoice && !invoice.issue_date && !invoice.due_date

  return (
    <Box>
      <AppHeader backTo="/invoices" backLabel="← 請求書一覧へ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5">請求書詳細・編集</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          請求書番号: {invoice?.invoice_number ?? '(保存後に自動採番されます)'}
        </Typography>

        {invoice?.source_quote_id && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            変換元見積書:{' '}
            <MuiLink component={RouterLink} to={`/quotes/${invoice.source_quote_id}`}>
              詳細を見る
            </MuiLink>
          </Typography>
        )}

        {showDatesMissingNotice && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            発行日・支払期限が未設定です
          </Alert>
        )}
        {errorMessage && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorMessage}
          </Alert>
        )}

        <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
          <Typography sx={{ fontWeight: 600, mb: 1.5, pb: 1, borderBottom: '1px solid #dde1e6' }}>基本情報</Typography>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <Autocomplete
              sx={{ flex: 1 }}
              options={clients ?? []}
              getOptionLabel={(option) => option.name}
              value={clients?.find((c) => c.id === clientId) ?? null}
              onChange={(_, value) => setClientId(value ? value.id : null)}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              renderInput={(params) => <TextField {...params} label="取引先" />}
            />
            <TextField label="発行日" type="date" InputLabelProps={{ shrink: true }} sx={{ flex: 1 }} value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
            <TextField label="支払期限" type="date" InputLabelProps={{ shrink: true }} sx={{ flex: 1 }} value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </Stack>
        </Card>

        <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
          <Typography sx={{ fontWeight: 600, mb: 1.5, pb: 1, borderBottom: '1px solid #dde1e6' }}>品目明細</Typography>
          <ItemsEditor items={items} onChange={setItems} />
        </Card>

        <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
          <Typography sx={{ fontWeight: 600, mb: 1.5, pb: 1, borderBottom: '1px solid #dde1e6' }}>備考</Typography>
          <TextField
            fullWidth
            multiline
            minRows={3}
            placeholder="備考を入力してください"
            inputProps={{ maxLength: 1000 }}
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
        </Card>

        {!isNew && invoice && (
          <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
            <Typography sx={{ fontWeight: 600, mb: 1.5, pb: 1, borderBottom: '1px solid #dde1e6' }}>入金記録</Typography>
            {invoice.payments.length === 0 ? (
              <Typography color="text.secondary" sx={{ fontSize: 13 }}>
                入金記録はまだありません。
              </Typography>
            ) : (
              <Box>
                {invoice.payments.map((p) => (
                  <Stack key={p.id} direction="row" justifyContent="space-between" sx={{ fontSize: 13, py: 0.5, borderBottom: '1px solid #eef1f4' }}>
                    <span>{p.payment_date}</span>
                    <span>{formatCurrency(p.amount)}</span>
                    <span>{p.remarks ?? ''}</span>
                  </Stack>
                ))}
              </Box>
            )}
            <Stack direction="row" spacing={1.5} sx={{ mt: 1.75 }} flexWrap="wrap" alignItems="flex-end">
              <TextField label="入金日" type="date" size="small" InputLabelProps={{ shrink: true }} value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} />
              <TextField
                label="入金額"
                type="number"
                size="small"
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value === '' ? '' : Number(e.target.value))}
              />
              <TextField label="備考" size="small" value={paymentRemarks} onChange={(e) => setPaymentRemarks(e.target.value)} sx={{ flex: 1, minWidth: 160 }} />
              <Button
                variant="outlined"
                disabled={paymentAmount === '' || Number(paymentAmount) <= 0}
                onClick={() => paymentMutation.mutate(false)}
              >
                追加
              </Button>
            </Stack>
          </Card>
        )}

        <Stack direction="row" spacing={1.5} justifyContent="flex-end">
          {!isNew && (
            <Button variant="outlined" component="a" href={invoicesApi.pdfUrl(invoiceId as number)} target="_blank" rel="noreferrer">
              PDF出力
            </Button>
          )}
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={saveMutation.isPending || clientId === null || !!itemsErrorMessage}
          >
            保存
          </Button>
        </Stack>
      </Container>
    </Box>
  )
}

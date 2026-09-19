import { useEffect, useState } from 'react'
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  Chip,
  Container,
  Link as MuiLink,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useLocation, useNavigate, useParams, useSearchParams, Link as RouterLink } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import ProjectSelect from '../components/ProjectSelect'
import ItemsEditor, { createEmptyItem, validateItems } from '../components/ItemsEditor'
import { clientsApi } from '../api/clients'
import { quotesApi, type QuotePayload } from '../api/quotes'
import { extractErrorMessage } from '../api/client'
import { QUOTE_STATUS_LABELS, type ItemInput, type QuoteStatus } from '../types'
import { QUOTE_STATUS_COLORS } from '../theme'

export default function QuoteDetailPage() {
  const { id } = useParams()
  const isNew = id === undefined || id === 'new'
  const quoteId = isNew ? undefined : Number(id)
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientsApi.list })
  const { data: quote } = useQuery({
    queryKey: ['quote', quoteId],
    queryFn: () => quotesApi.get(quoteId as number),
    enabled: !isNew,
  })

  const [clientId, setClientId] = useState<number | null>(null)
  const [issueDate, setIssueDate] = useState('')
  const [expiryDate, setExpiryDate] = useState('')
  const [status, setStatus] = useState<QuoteStatus>('DRAFT')
  const [items, setItems] = useState<ItemInput[]>([createEmptyItem()])
  const [remarks, setRemarks] = useState('')
  const [projectId, setProjectId] = useState<number | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    if (quote) {
      setClientId(quote.client_id)
      setIssueDate(quote.issue_date ?? '')
      setExpiryDate(quote.expiry_date ?? '')
      setStatus(quote.status)
      setItems(quote.items.map((i) => ({ ...i, clientKey: String(i.id) })))
      setRemarks(quote.remarks ?? '')
      setProjectId(quote.project_id)
    }
  }, [quote])

  // 取引先マスタ画面(SC-10)で新規登録し、呼び出し元へ戻ってきた場合に選択状態を復元する
  useEffect(() => {
    const selectedClientId = searchParams.get('selectedClientId')
    if (selectedClientId) {
      setClientId(Number(selectedClientId))
      const next = new URLSearchParams(searchParams)
      next.delete('selectedClientId')
      setSearchParams(next, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  const saveMutation = useMutation({
    mutationFn: (payload: QuotePayload) => (isNew ? quotesApi.create(payload) : quotesApi.update(quoteId as number, payload)),
    onSuccess: (saved) => {
      setErrorMessage(null)
      queryClient.invalidateQueries({ queryKey: ['quotes'] })
      if (isNew) {
        navigate(`/quotes/${saved.id}`, { replace: true })
      } else {
        queryClient.invalidateQueries({ queryKey: ['quote', quoteId] })
      }
    },
    onError: (error) => setErrorMessage(extractErrorMessage(error)),
  })

  const convertMutation = useMutation({
    mutationFn: () => quotesApi.convertToInvoice(quoteId as number),
    onSuccess: (invoice) => {
      queryClient.invalidateQueries({ queryKey: ['quote', quoteId] })
      navigate(`/invoices/${invoice.id}`)
    },
    onError: (error) => {
      const message = extractErrorMessage(error)
      window.alert(message)
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
      expiry_date: expiryDate || null,
      status,
      items,
      remarks: remarks || null,
      project_id: projectId,
    })
  }

  return (
    <Box>
      <AppHeader backTo="/quotes" backLabel="← 見積書一覧へ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5">見積書詳細・編集</Typography>
        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            見積書番号: {quote?.quote_number ?? '(保存後に自動採番されます)'}
          </Typography>
          {quote && <Chip size="small" label={QUOTE_STATUS_LABELS[status]} sx={{ backgroundColor: QUOTE_STATUS_COLORS[status], color: '#fff' }} />}
        </Stack>

        {quote?.converted_invoice_id && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            変換後の請求書:{' '}
            <MuiLink component={RouterLink} to={`/invoices/${quote.converted_invoice_id}`}>
              {quote.converted_invoice_number}
            </MuiLink>
          </Typography>
        )}

        {errorMessage && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorMessage}
          </Alert>
        )}

        <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
          <Typography sx={{ fontWeight: 600, mb: 1.5, pb: 1, borderBottom: '1px solid #dde1e6' }}>基本情報</Typography>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
            <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
              <Autocomplete
                sx={{ flex: 1 }}
                options={clients ?? []}
                getOptionLabel={(option) => option.name}
                value={clients?.find((c) => c.id === clientId) ?? null}
                onChange={(_, value) => setClientId(value ? value.id : null)}
                isOptionEqualToValue={(option, value) => option.id === value.id}
                renderInput={(params) => <TextField {...params} label="取引先" />}
              />
              <MuiLink
                component={RouterLink}
                to={`/clients?returnTo=${encodeURIComponent(location.pathname)}`}
                sx={{ whiteSpace: 'nowrap', fontSize: 13 }}
              >
                新規登録
              </MuiLink>
            </Box>
            <TextField label="発行日" type="date" InputLabelProps={{ shrink: true }} sx={{ flex: 1 }} value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
            <TextField label="有効期限" type="date" InputLabelProps={{ shrink: true }} sx={{ flex: 1 }} value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
          </Stack>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, maxWidth: 480 }}>
            <ProjectSelect value={projectId} onChange={setProjectId} showDetailLink />
          </Box>
          <Stack direction="row" spacing={1}>
            <Button variant={status === 'DRAFT' ? 'contained' : 'outlined'} size="small" onClick={() => setStatus('DRAFT')}>
              作成中
            </Button>
            <Button variant={status === 'CONFIRMED' ? 'contained' : 'outlined'} size="small" onClick={() => setStatus('CONFIRMED')}>
              確定
            </Button>
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

        <Stack direction="row" spacing={1.5} justifyContent="flex-end">
          {!isNew && (
            <>
              <Button variant="outlined" component="a" href={quotesApi.pdfUrl(quoteId as number)} target="_blank" rel="noreferrer">
                PDF出力
              </Button>
              <Button variant="outlined" onClick={() => convertMutation.mutate()} disabled={convertMutation.isPending}>
                請求書へ変換
              </Button>
            </>
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

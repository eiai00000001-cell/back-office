import { useEffect, useRef, useState } from 'react'
import { Alert, Box, Button, Card, Container, MenuItem, Stack, TextField, Typography } from '@mui/material'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { expensesApi, type ExpensePayload } from '../api/expenses'
import { extractErrorMessage } from '../api/client'
import { ACCOUNT_CATEGORIES, EXPENSE_TAX_CATEGORY_LABELS, PAYMENT_METHOD_LABELS, type ExpenseTaxCategory, type PaymentMethod } from '../types'

const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.pdf']
const MAX_SIZE_BYTES = 10 * 1024 * 1024

export default function ExpenseFormPage() {
  const { id } = useParams()
  const isNew = id === undefined || id === 'new'
  const expenseId = isNew ? undefined : Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: expense } = useQuery({
    queryKey: ['expense', expenseId],
    queryFn: () => expensesApi.get(expenseId as number),
    enabled: !isNew,
  })

  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().slice(0, 10))
  const [categorySelect, setCategorySelect] = useState<string>(ACCOUNT_CATEGORIES[0])
  const [customCategory, setCustomCategory] = useState('')
  const [amount, setAmount] = useState<number | ''>('')
  const [taxCategory, setTaxCategory] = useState<ExpenseTaxCategory>('STANDARD_10')
  const [payee, setPayee] = useState('')
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | ''>('')
  const [memo, setMemo] = useState('')
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)

  useEffect(() => {
    if (expense) {
      setExpenseDate(expense.expense_date)
      const isKnownCategory = (ACCOUNT_CATEGORIES as readonly string[]).includes(expense.account_category)
      setCategorySelect(isKnownCategory ? expense.account_category : 'その他')
      setCustomCategory(isKnownCategory ? '' : expense.account_category)
      setAmount(expense.amount)
      setTaxCategory(expense.tax_category)
      setPayee(expense.payee ?? '')
      setPaymentMethod(expense.payment_method ?? '')
      setMemo(expense.memo ?? '')
    }
  }, [expense])

  const saveMutation = useMutation({
    mutationFn: async (payload: ExpensePayload) => {
      const saved = isNew ? await expensesApi.create(payload) : await expensesApi.update(expenseId as number, payload)
      if (pendingFile) {
        return expensesApi.uploadAttachment(saved.id, pendingFile)
      }
      return saved
    },
    onSuccess: (saved) => {
      setErrorMessage(null)
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      navigate(`/expenses/${saved.id}`, { replace: true })
    },
    onError: (error) => setErrorMessage(extractErrorMessage(error)),
  })

  const validateFile = (file: File): boolean => {
    const lowerName = file.name.toLowerCase()
    const hasAllowedExtension = ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext))
    if (!hasAllowedExtension || file.size > MAX_SIZE_BYTES) {
      setFileError('対応していないファイル形式、またはサイズが上限(10MB)を超えています')
      return false
    }
    setFileError(null)
    return true
  }

  const handleFileSelected = (file: File | undefined) => {
    if (!file) return
    if (validateFile(file)) {
      setPendingFile(file)
    }
  }

  const handleSave = () => {
    const finalCategory = categorySelect === 'その他' ? customCategory : categorySelect
    if (!finalCategory) {
      setErrorMessage('勘定科目を選択してください')
      return
    }
    if (amount === '' || Number(amount) <= 0) {
      setErrorMessage('金額は0より大きい数値で入力してください')
      return
    }
    saveMutation.mutate({
      expense_date: expenseDate,
      account_category: finalCategory,
      amount: Number(amount),
      tax_category: taxCategory,
      payee: payee || null,
      payment_method: paymentMethod || null,
      memo: memo || null,
    })
  }

  return (
    <Box>
      <AppHeader backTo="/expenses" backLabel="← 経費一覧へ" />
      <Container maxWidth="sm" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          経費登録・編集
        </Typography>

        {errorMessage && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorMessage}
          </Alert>
        )}
        {fileError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {fileError}
          </Alert>
        )}

        <Card variant="outlined" sx={{ p: 3 }}>
          <Stack spacing={2}>
            <TextField
              label="発生日"
              required
              type="date"
              InputLabelProps={{ shrink: true }}
              value={expenseDate}
              onChange={(e) => setExpenseDate(e.target.value)}
            />
            <TextField select label="勘定科目" required value={categorySelect} onChange={(e) => setCategorySelect(e.target.value)}>
              {ACCOUNT_CATEGORIES.map((c) => (
                <MenuItem key={c} value={c}>
                  {c}
                </MenuItem>
              ))}
            </TextField>
            {categorySelect === 'その他' && (
              <TextField
                label="科目名(その他)"
                placeholder="その他の場合、科目名を入力"
                value={customCategory}
                onChange={(e) => setCustomCategory(e.target.value)}
              />
            )}
            <TextField
              label="金額"
              required
              type="number"
              placeholder="0"
              value={amount}
              onChange={(e) => setAmount(e.target.value === '' ? '' : Number(e.target.value))}
            />
            <TextField select label="税区分" required value={taxCategory} onChange={(e) => setTaxCategory(e.target.value as ExpenseTaxCategory)}>
              {Object.entries(EXPENSE_TAX_CATEGORY_LABELS).map(([value, label]) => (
                <MenuItem key={value} value={value}>
                  {label}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="支払先" value={payee} onChange={(e) => setPayee(e.target.value)} inputProps={{ maxLength: 100 }} />
            <TextField select label="支払方法" value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod | '')}>
              <MenuItem value="">未選択</MenuItem>
              {Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => (
                <MenuItem key={value} value={value}>
                  {label}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="メモ" multiline minRows={3} value={memo} onChange={(e) => setMemo(e.target.value)} inputProps={{ maxLength: 500 }} />

            <Box>
              <Typography sx={{ fontSize: 13, color: 'text.secondary', mb: 0.5 }}>領収書ファイル</Typography>
              <Box
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault()
                  handleFileSelected(e.dataTransfer.files[0])
                }}
                sx={{ border: '2px dashed #dde1e6', borderRadius: '6px', p: 3, textAlign: 'center', color: 'text.secondary', fontSize: 13 }}
              >
                {pendingFile ? (
                  <Typography sx={{ fontSize: 13 }}>{pendingFile.name}</Typography>
                ) : expense?.attachment_original_name ? (
                  <Typography sx={{ fontSize: 13 }}>登録済み: {expense.attachment_original_name}</Typography>
                ) : (
                  <Typography sx={{ fontSize: 13 }}>ここにファイルをドラッグ&ドロップ、または</Typography>
                )}
                <Button sx={{ mt: 1.25 }} variant="outlined" onClick={() => fileInputRef.current?.click()}>
                  ファイルを選択
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".jpg,.jpeg,.png,.pdf"
                  hidden
                  onChange={(e) => handleFileSelected(e.target.files?.[0])}
                />
                <Typography sx={{ fontSize: 12, color: 'text.secondary', mt: 0.5 }}>対応形式: jpg / jpeg / png / pdf(最大10MB)</Typography>
              </Box>
            </Box>
          </Stack>
        </Card>

        <Stack direction="row" justifyContent="flex-end" sx={{ mt: 2 }}>
          <Button variant="contained" onClick={handleSave} disabled={saveMutation.isPending}>
            保存
          </Button>
        </Stack>
      </Container>
    </Box>
  )
}

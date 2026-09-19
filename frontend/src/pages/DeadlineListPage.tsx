import { useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  Checkbox,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { DueBadge, KindTag } from '../components/NotificationCommon'
import { extractErrorMessage } from '../api/client'
import { deadlinesApi, type DeadlinePayload } from '../api/deadlines'
import { DEADLINE_CATEGORY_LABELS, type Deadline, type DeadlineCategory } from '../types'

interface FormState {
  name: string
  due_date: string
  category: DeadlineCategory
  memo: string
  is_recurring: boolean
}

interface FormErrors {
  name?: string
  due_date?: string
}

const EMPTY_FORM: FormState = { name: '', due_date: '', category: 'OTHER', memo: '', is_recurring: false }

function toForm(deadline: Deadline): FormState {
  return {
    name: deadline.name,
    due_date: deadline.due_date,
    category: deadline.category,
    memo: deadline.memo ?? '',
    is_recurring: deadline.is_recurring,
  }
}

export default function DeadlineListPage() {
  const queryClient = useQueryClient()
  const { data: deadlines, isError } = useQuery({ queryKey: ['deadlines'], queryFn: deadlinesApi.list })

  // editing: null=閉じている / 'new'=新規登録 / 期限=編集
  const [editing, setEditing] = useState<Deadline | 'new' | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [errors, setErrors] = useState<FormErrors>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<Deadline | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  // 期限の変更は通知の内容に影響するため、通知の取得結果も無効化する
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['deadlines'] })
    queryClient.invalidateQueries({ queryKey: ['notifications'] })
    queryClient.invalidateQueries({ queryKey: ['notification-summary'] })
  }

  const save = useMutation({
    mutationFn: (payload: DeadlinePayload) =>
      editing !== null && editing !== 'new' ? deadlinesApi.update(editing.id, payload) : deadlinesApi.create(payload),
    onSuccess: () => {
      setEditing(null)
      refresh()
    },
    onError: (error) => setServerError(extractErrorMessage(error)),
  })

  const remove = useMutation({
    mutationFn: (id: number) => deadlinesApi.remove(id),
    onSuccess: () => {
      setDeleting(null)
      refresh()
    },
    onError: (error) => setDeleteError(extractErrorMessage(error)),
  })

  const openDialog = (target: Deadline | 'new') => {
    setEditing(target)
    setForm(target === 'new' ? EMPTY_FORM : toForm(target))
    setErrors({})
    setServerError(null)
  }

  const submit = () => {
    const name = form.name.trim()
    const next: FormErrors = {}
    if (name === '') next.name = '名称を入力してください'
    if (form.due_date === '') next.due_date = '期限日を入力してください'
    setErrors(next)
    setServerError(null)
    if (Object.keys(next).length > 0) return
    save.mutate({
      name,
      due_date: form.due_date,
      category: form.category,
      memo: form.memo.trim() === '' ? null : form.memo,
      is_recurring: form.is_recurring,
    })
  }

  return (
    <Box>
      <AppHeader backTo="/" backLabel="← ホームへ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          期限の登録・編集
        </Typography>
        <Card variant="outlined" sx={{ p: 2.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
            <Button variant="outlined" color="inherit" component={RouterLink} to="/notifications">
              ← 通知一覧へ
            </Button>
            <Button variant="contained" onClick={() => openDialog('new')}>
              新規登録
            </Button>
          </Box>
          <Alert severity="info" icon={false} sx={{ mb: 1.5, py: 0, fontSize: 12 }}>
            確定申告書類の作成や契約書の管理は行いません。期限の登録と通知のみです。
          </Alert>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: 12, mb: 1.25 }}>
            期限日の近い順で表示しています。
          </Typography>
          {isError && (
            <Typography color="error" sx={{ fontSize: 13, mb: 1 }}>
              期限を取得できませんでした。
            </Typography>
          )}
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>名称</TableCell>
                <TableCell>期限日</TableCell>
                <TableCell>種別</TableCell>
                <TableCell>毎年繰り返し</TableCell>
                <TableCell>メモ</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {deadlines?.map((d) => (
                <TableRow key={d.id}>
                  <TableCell>{d.name}</TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    <Box
                      component="span"
                      sx={{ fontWeight: d.due_state ? 700 : 400, color: d.due_state === 'OVERDUE' ? 'error.main' : d.due_state ? '#b45309' : undefined, mr: 0.75 }}
                    >
                      {d.due_date}
                    </Box>
                    <DueBadge state={d.due_state} />
                  </TableCell>
                  <TableCell>
                    <KindTag label={DEADLINE_CATEGORY_LABELS[d.category]} />
                  </TableCell>
                  <TableCell>{d.is_recurring ? '毎年' : 'なし'}</TableCell>
                  <TableCell sx={{ color: 'text.secondary' }}>{d.memo ?? '-'}</TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    <Button size="small" variant="outlined" color="inherit" onClick={() => openDialog(d)} sx={{ mr: 0.75 }}>
                      編集
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      onClick={() => {
                        setDeleteError(null)
                        setDeleting(d)
                      }}
                    >
                      削除
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {deadlines && deadlines.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} sx={{ color: 'text.secondary' }}>
                    登録された期限はありません。
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      </Container>

      <Dialog open={editing !== null} onClose={() => setEditing(null)} fullWidth maxWidth="sm">
        <DialogTitle>{editing === 'new' ? '期限の登録' : '期限の編集'}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '8px !important' }}>
          {serverError && <Alert severity="error">{serverError}</Alert>}
          <TextField
            label="名称"
            required
            size="small"
            placeholder="例: 契約更新(サンプル)"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            error={Boolean(errors.name)}
            helperText={errors.name}
            inputProps={{ maxLength: 100 }}
          />
          <TextField
            label="期限日"
            required
            size="small"
            type="date"
            InputLabelProps={{ shrink: true }}
            value={form.due_date}
            onChange={(e) => setForm({ ...form, due_date: e.target.value })}
            error={Boolean(errors.due_date)}
            helperText={errors.due_date}
          />
          <TextField
            select
            label="種別"
            required
            size="small"
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value as DeadlineCategory })}
          >
            {Object.entries(DEADLINE_CATEGORY_LABELS).map(([value, label]) => (
              <MenuItem key={value} value={value}>
                {label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="メモ(最大500文字)"
            size="small"
            multiline
            minRows={3}
            value={form.memo}
            onChange={(e) => setForm({ ...form, memo: e.target.value })}
            inputProps={{ maxLength: 500 }}
          />
          <FormControlLabel
            control={<Checkbox checked={form.is_recurring} onChange={(e) => setForm({ ...form, is_recurring: e.target.checked })} />}
            label="毎年繰り返す"
          />
        </DialogContent>
        <DialogActions>
          <Button color="inherit" onClick={() => setEditing(null)}>
            キャンセル
          </Button>
          <Button variant="contained" onClick={submit} disabled={save.isPending}>
            保存
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleting !== null} onClose={() => setDeleting(null)}>
        <DialogTitle>期限の削除</DialogTitle>
        <DialogContent>
          <DialogContentText>「{deleting?.name}」を削除します。よろしいですか?</DialogContentText>
          {deleteError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {deleteError}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button color="inherit" onClick={() => setDeleting(null)}>
            キャンセル
          </Button>
          <Button color="error" variant="contained" onClick={() => deleting && remove.mutate(deleting.id)} disabled={remove.isPending}>
            削除する
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

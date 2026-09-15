import { useEffect, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import {
  Alert,
  Box,
  Button,
  Card,
  Container,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import { clientsApi } from '../api/clients'
import { extractErrorMessage } from '../api/client'

const clientSchema = z.object({
  name: z.string().min(1, '名称を入力してください').max(100),
  postal_code: z
    .string()
    .max(8)
    .regex(/^[0-9-]*$/, '郵便番号は数字とハイフンで入力してください')
    .optional()
    .or(z.literal('')),
  address: z.string().max(200).optional().or(z.literal('')),
  contact_person: z.string().max(50).optional().or(z.literal('')),
  contact_info: z.string().max(200).optional().or(z.literal('')),
})

type ClientFormValues = z.infer<typeof clientSchema>

const emptyValues: ClientFormValues = { name: '', postal_code: '', address: '', contact_person: '', contact_info: '' }

export default function ClientMasterPage() {
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  // 請求書/見積書の編集画面から「新規登録」で遷移してきた場合、保存後に戻る先(例: /invoices/3)。
  const returnTo = searchParams.get('returnTo')
  const [editingId, setEditingId] = useState<number | null>(null)

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientsApi.list })
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ClientFormValues>({ resolver: zodResolver(clientSchema), defaultValues: emptyValues })

  useEffect(() => {
    if (editingId && clients) {
      const target = clients.find((c) => c.id === editingId)
      if (target) {
        reset({
          name: target.name,
          postal_code: target.postal_code ?? '',
          address: target.address ?? '',
          contact_person: target.contact_person ?? '',
          contact_info: target.contact_info ?? '',
        })
      }
    }
  }, [editingId, clients, reset])

  const saveMutation = useMutation({
    mutationFn: async (values: ClientFormValues) => {
      const payload = {
        name: values.name,
        postal_code: values.postal_code || null,
        address: values.address || null,
        contact_person: values.contact_person || null,
        contact_info: values.contact_info || null,
      }
      return editingId ? clientsApi.update(editingId, payload) : clientsApi.create(payload)
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      reset(emptyValues)
      setEditingId(null)
      if (returnTo) {
        window.location.href = `${returnTo}?selectedClientId=${saved.id}`
      }
    },
  })

  return (
    <Box>
      <AppHeader backTo="/" backLabel="← ホームへ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          取引先マスタ管理
        </Typography>

        <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
          <Typography sx={{ fontWeight: 600, mb: 1.5, pb: 1, borderBottom: '1px solid #dde1e6' }}>取引先一覧</Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>名称</TableCell>
                <TableCell>住所</TableCell>
                <TableCell>担当者名</TableCell>
                <TableCell>連絡先</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {clients?.map((client) => (
                <TableRow key={client.id}>
                  <TableCell>{client.name}</TableCell>
                  <TableCell>{client.address ?? ''}</TableCell>
                  <TableCell>{client.contact_person ?? ''}</TableCell>
                  <TableCell>{client.contact_info ?? ''}</TableCell>
                  <TableCell>
                    <Button size="small" variant="outlined" onClick={() => setEditingId(client.id)}>
                      編集
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Typography sx={{ fontSize: 12, color: 'text.secondary', mt: 2 }}>
            請求書・見積書の編集画面から「新規登録」を選択した場合も、下記フォームに入力・保存後、呼び出し元の画面へ戻り選択状態になります。
          </Typography>
        </Card>

        <Card variant="outlined" sx={{ p: 2.5 }}>
          <Typography sx={{ fontWeight: 600, mb: 1.5, pb: 1, borderBottom: '1px solid #dde1e6' }}>取引先登録・編集</Typography>
          {saveMutation.isError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {extractErrorMessage(saveMutation.error)}
            </Alert>
          )}
          <Stack spacing={2} component="form" onSubmit={handleSubmit((values) => saveMutation.mutate(values))}>
            <TextField label="名称" required {...register('name')} error={!!errors.name} helperText={errors.name?.message} />
            <TextField
              label="郵便番号"
              placeholder="100-0001"
              {...register('postal_code')}
              error={!!errors.postal_code}
              helperText={errors.postal_code?.message}
            />
            <TextField label="住所" {...register('address')} error={!!errors.address} helperText={errors.address?.message} />
            <TextField
              label="担当者名"
              {...register('contact_person')}
              error={!!errors.contact_person}
              helperText={errors.contact_person?.message}
            />
            <TextField
              label="連絡先"
              {...register('contact_info')}
              error={!!errors.contact_info}
              helperText={errors.contact_info?.message}
            />
            <Stack direction="row" justifyContent="flex-end">
              <Button type="submit" variant="contained" disabled={saveMutation.isPending}>
                保存
              </Button>
            </Stack>
          </Stack>
        </Card>
      </Container>
    </Box>
  )
}

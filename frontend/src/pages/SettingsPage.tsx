import { useEffect } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { Alert, Box, Button, Card, Container, Stack, TextField, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { companyProfileApi } from '../api/companyProfile'
import { extractErrorMessage } from '../api/client'

const profileSchema = z.object({
  name: z.string().min(1, '氏名を入力してください').max(50),
  business_name: z.string().max(100).optional().or(z.literal('')),
  address: z.string().max(200).optional().or(z.literal('')),
  contact_info: z.string().max(200).optional().or(z.literal('')),
  invoice_registration_number: z
    .string()
    .regex(/^T\d{13}$/, '登録番号は T + 数字13桁 で入力してください')
    .optional()
    .or(z.literal('')),
})

type ProfileFormValues = z.infer<typeof profileSchema>

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const { data: profile } = useQuery({ queryKey: ['company-profile'], queryFn: companyProfileApi.get })
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { name: '', business_name: '', address: '', contact_info: '', invoice_registration_number: '' },
  })

  useEffect(() => {
    if (profile) {
      reset({
        name: profile.name,
        business_name: profile.business_name ?? '',
        address: profile.address ?? '',
        contact_info: profile.contact_info ?? '',
        invoice_registration_number: profile.invoice_registration_number ?? '',
      })
    }
  }, [profile, reset])

  const saveMutation = useMutation({
    mutationFn: (values: ProfileFormValues) =>
      companyProfileApi.update({
        name: values.name,
        business_name: values.business_name || null,
        address: values.address || null,
        contact_info: values.contact_info || null,
        invoice_registration_number: values.invoice_registration_number || null,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['company-profile'] }),
  })

  return (
    <Box>
      <AppHeader backTo="/" backLabel="← ホームへ" />
      <Container maxWidth="sm" sx={{ py: 3 }}>
        <Typography variant="h5">システム設定(発行者情報)</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          請求書・見積書のPDF出力時に、ここで登録した内容が表示されます。
        </Typography>

        {saveMutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {extractErrorMessage(saveMutation.error)}
          </Alert>
        )}
        {saveMutation.isSuccess && (
          <Alert severity="success" sx={{ mb: 2 }}>
            保存しました
          </Alert>
        )}

        <Card variant="outlined" sx={{ p: 3 }}>
          <Stack spacing={2} component="form" onSubmit={handleSubmit((values) => saveMutation.mutate(values))}>
            <TextField label="氏名" required {...register('name')} error={!!errors.name} helperText={errors.name?.message} />
            <TextField label="屋号" {...register('business_name')} error={!!errors.business_name} helperText={errors.business_name?.message} />
            <TextField label="住所" {...register('address')} error={!!errors.address} helperText={errors.address?.message} />
            <TextField label="連絡先" {...register('contact_info')} error={!!errors.contact_info} helperText={errors.contact_info?.message} />
            <TextField
              label="登録番号"
              placeholder="T1234567890123"
              {...register('invoice_registration_number')}
              error={!!errors.invoice_registration_number}
              helperText={
                errors.invoice_registration_number?.message ??
                '記載は任意です。適格請求書発行事業者の登録番号をお持ちの場合のみご入力ください。'
              }
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

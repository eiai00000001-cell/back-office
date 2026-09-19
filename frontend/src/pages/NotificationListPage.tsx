import { useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  Container,
  FormControlLabel,
  Link as MuiLink,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { DueBadge, KindTag } from '../components/NotificationCommon'
import { extractErrorMessage } from '../api/client'
import { notificationsApi, type NotificationTarget } from '../api/notifications'
import { NOTIFICATION_KIND_LABELS } from '../types'
import { OVERDUE_BACKGROUND } from '../theme'

export default function NotificationListPage() {
  const queryClient = useQueryClient()
  const [includeAcknowledged, setIncludeAcknowledged] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const { data, isError } = useQuery({
    queryKey: ['notifications', includeAcknowledged],
    queryFn: () => notificationsApi.list(includeAcknowledged),
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] })
    queryClient.invalidateQueries({ queryKey: ['notification-summary'] })
  }

  const acknowledge = useMutation({
    mutationFn: (target: NotificationTarget) => notificationsApi.acknowledge(target),
    onSuccess: () => setActionError(null),
    // 解消済み(404)を含め、失敗時もメッセージを出したうえで一覧を再取得する(詳細設計書8章)
    onError: (error) => setActionError(extractErrorMessage(error, '確認済みにできませんでした')),
    onSettled: refresh,
  })
  const unacknowledge = useMutation({
    mutationFn: (target: NotificationTarget) => notificationsApi.unacknowledge(target),
    onSuccess: () => setActionError(null),
    onError: (error) => setActionError(extractErrorMessage(error, '未確認に戻せませんでした')),
    onSettled: refresh,
  })

  return (
    <Box>
      <AppHeader backTo="/" backLabel="← ホームへ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          通知一覧
        </Typography>
        <Card variant="outlined" sx={{ p: 2.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1.5, mb: 1.5 }}>
            <FormControlLabel
              control={
                <Switch checked={includeAcknowledged} onChange={(e) => setIncludeAcknowledged(e.target.checked)} />
              }
              label="確認済みも表示"
            />
            <Button variant="contained" component={RouterLink} to="/deadlines">
              期限を登録・編集
            </Button>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: 12, mb: 1.25 }}>
            超過が先頭、期限日の近い順で表示しています。
          </Typography>
          {isError && (
            <Typography color="error" sx={{ fontSize: 13, mb: 1 }}>
              通知を取得できませんでした。
            </Typography>
          )}
          {data && data.errors.length > 0 && (
            <Alert severity="warning" sx={{ mb: 1.5, py: 0 }}>
              一部の通知を取得できませんでした({data.errors.map((t) => NOTIFICATION_KIND_LABELS[t]).join('、')})
            </Alert>
          )}
          {actionError && (
            <Alert severity="error" sx={{ mb: 1.5, py: 0 }}>
              {actionError}
            </Alert>
          )}
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>種類</TableCell>
                <TableCell>内容</TableCell>
                <TableCell>期限日</TableCell>
                <TableCell>状態</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data?.items.map((item) => {
                const target = { source_type: item.source_type, source_id: item.source_id }
                return (
                  <TableRow
                    key={`${item.source_type}-${item.source_id}`}
                    sx={{
                      backgroundColor: item.state === 'OVERDUE' ? OVERDUE_BACKGROUND : undefined,
                      opacity: item.acknowledged ? 0.55 : 1,
                    }}
                  >
                    <TableCell>
                      <KindTag label={NOTIFICATION_KIND_LABELS[item.source_type]} />
                    </TableCell>
                    <TableCell>
                      <MuiLink component={RouterLink} to={item.link} color="inherit" underline="hover">
                        {item.title}
                      </MuiLink>
                    </TableCell>
                    <TableCell
                      sx={{ fontWeight: 700, color: item.state === 'OVERDUE' ? 'error.main' : '#b45309', whiteSpace: 'nowrap' }}
                    >
                      {item.due_date}
                    </TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      <DueBadge state={item.state} />
                      {item.acknowledged && (
                        <Typography component="span" color="text.secondary" sx={{ fontSize: 12, ml: 1 }}>
                          確認済み
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {item.acknowledged ? (
                        <Button size="small" variant="outlined" color="inherit" onClick={() => unacknowledge.mutate(target)}>
                          未確認に戻す
                        </Button>
                      ) : (
                        <Button size="small" variant="outlined" color="inherit" onClick={() => acknowledge.mutate(target)}>
                          確認済み
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
              {data && data.items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} sx={{ color: 'text.secondary' }}>
                    表示する通知はありません。
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: 12, mt: 1.5 }}>
            項目の内容をクリックすると、請求書はSC-03、見積書はSC-05、案件はSC-15、登録した期限はSC-17へ移動します。
          </Typography>
        </Card>
      </Container>
    </Box>
  )
}

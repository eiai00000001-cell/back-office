import { useState } from 'react'
import { Alert, Box, Button, Card, Container, Grid, Link as MuiLink, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { DueBadge } from '../components/NotificationCommon'
import { extractErrorMessage } from '../api/client'
import { homeApi } from '../api/home'
import { notificationsApi, type NotificationTarget } from '../api/notifications'
import { NOTIFICATION_KIND_LABELS } from '../types'
import { OVERDUE_BACKGROUND } from '../theme'

const NAV_CARDS = [
  { to: '/invoices', name: '請求書', desc: '請求書の発行・入金確認' },
  { to: '/expenses', name: '経費管理', desc: '経費の登録・集計' },
  { to: '/quotes', name: '見積書', desc: '見積書の作成・請求書への変換' },
  { to: '/receivables', name: '売掛金', desc: '入金状況・未入金の確認' },
  { to: '/dashboard', name: '財務ダッシュボード', desc: '売上・経費・損益・見積状況の可視化' },
  { to: '/projects/kanban', name: '案件管理', desc: '案件の進捗・納期の管理' },
  { to: '/notifications', name: '通知・期限', desc: '支払期限・納期などの通知確認' },
  { to: '/reports', name: 'レポート出力', desc: 'CSV・PDFでの帳票出力' },
]

export default function HomePage() {
  const queryClient = useQueryClient()
  const { data, isError } = useQuery({ queryKey: ['home-summary'], queryFn: homeApi.summary })
  // 通知エリアは既存サマリーと独立して取得する(失敗しても互いに影響させない。詳細設計書4.10.6)
  const { data: notices, isError: noticesError } = useQuery({
    queryKey: ['notification-summary'],
    queryFn: notificationsApi.summary,
  })
  const [ackError, setAckError] = useState<string | null>(null)
  const acknowledge = useMutation({
    mutationFn: (target: NotificationTarget) => notificationsApi.acknowledge(target),
    onSuccess: () => setAckError(null),
    onError: (error) => setAckError(extractErrorMessage(error, '確認済みにできませんでした')),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-summary'] })
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  return (
    <Box>
      <AppHeader backTo={undefined} />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          ホーム
        </Typography>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          サマリー
        </Typography>
        {isError ? (
          <Card variant="outlined" sx={{ p: 2, mb: 3.5, color: 'text.secondary', fontSize: 13 }}>
            サマリー情報を取得できませんでした。
          </Card>
        ) : (
          <Grid container spacing={2} sx={{ mb: 3.5 }}>
            <Grid item xs={6}>
              <Card variant="outlined" sx={{ p: 2.25 }}>
                <Typography sx={{ fontSize: 30, fontWeight: 700, color: 'primary.main' }}>
                  {data?.unpaid_count ?? '-'}
                </Typography>
                <Typography sx={{ fontSize: 13, color: 'text.secondary', mt: 0.5 }}>未入金件数</Typography>
              </Card>
            </Grid>
            <Grid item xs={6}>
              <Card variant="outlined" sx={{ p: 2.25 }}>
                <Typography sx={{ fontSize: 30, fontWeight: 700, color: 'error.main' }}>
                  {data?.overdue_count ?? '-'}
                </Typography>
                <Typography sx={{ fontSize: 13, color: 'text.secondary', mt: 0.5 }}>支払期限超過件数</Typography>
              </Card>
            </Grid>
          </Grid>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          通知
        </Typography>
        {noticesError ? (
          <Card variant="outlined" sx={{ p: 2, mb: 3.5, color: 'text.secondary', fontSize: 13 }}>
            通知を取得できませんでした。
          </Card>
        ) : (
          <Card variant="outlined" sx={{ p: 2, mb: 3.5 }} data-testid="notice-area">
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }} data-testid="notice-head">
              <Typography sx={{ fontSize: 14 }}>
                未確認 <b style={{ fontSize: 16 }}>{notices?.unacknowledged_count ?? '-'}</b> 件(うち期限超過{' '}
                <Box component="span" sx={{ color: 'error.main', fontWeight: 700 }}>
                  {notices?.overdue_count ?? '-'}
                </Box>{' '}
                件)
              </Typography>
              <MuiLink component={RouterLink} to="/notifications" underline="hover" sx={{ fontSize: 13 }}>
                すべての通知を見る →
              </MuiLink>
            </Box>
            {notices && notices.errors.length > 0 && (
              <Alert severity="warning" sx={{ mb: 1, py: 0 }}>
                一部の通知を取得できませんでした({notices.errors.map((t) => NOTIFICATION_KIND_LABELS[t]).join('、')})
              </Alert>
            )}
            {ackError && (
              <Alert severity="error" sx={{ mb: 1, py: 0 }}>
                {ackError}
              </Alert>
            )}
            {notices && notices.items.length === 0 && (
              <Typography sx={{ fontSize: 13, color: 'text.secondary', pt: 1, borderTop: '1px solid #dde1e6' }}>
                未確認の通知はありません。
              </Typography>
            )}
            {notices?.items.map((item) => (
              <Box
                key={`${item.source_type}-${item.source_id}`}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  py: 1,
                  borderTop: '1px solid #dde1e6',
                  fontSize: 13,
                  backgroundColor: item.state === 'OVERDUE' ? OVERDUE_BACKGROUND : undefined,
                }}
              >
                <Box sx={{ width: 130, color: 'text.secondary', flexShrink: 0 }}>{NOTIFICATION_KIND_LABELS[item.source_type]}</Box>
                <MuiLink component={RouterLink} to={item.link} color="text.primary" underline="hover" sx={{ flex: 1 }}>
                  {item.title}
                </MuiLink>
                <Box sx={{ width: 100, color: 'text.secondary' }}>{item.due_date}</Box>
                <Box sx={{ width: 56, textAlign: 'center' }}>
                  <DueBadge state={item.state} />
                </Box>
                <Button
                  size="small"
                  variant="outlined"
                  color="inherit"
                  onClick={() => acknowledge.mutate({ source_type: item.source_type, source_id: item.source_id })}
                >
                  確認済み
                </Button>
              </Box>
            ))}
          </Card>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          メニュー
        </Typography>
        <Grid container spacing={2}>
          {NAV_CARDS.map((card) => (
            <Grid item xs={6} md={3} key={card.to}>
              <MuiLink component={RouterLink} to={card.to} underline="none" sx={{ display: 'block' }}>
                <Card
                  variant="outlined"
                  sx={{
                    p: 3.5,
                    textAlign: 'center',
                    borderTop: '4px solid',
                    borderTopColor: 'primary.main',
                    color: 'text.primary',
                    '&:hover': { boxShadow: 2 },
                  }}
                >
                  <Typography sx={{ fontSize: 16, fontWeight: 600, mb: 0.75 }}>{card.name}</Typography>
                  <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>{card.desc}</Typography>
                </Card>
              </MuiLink>
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  )
}

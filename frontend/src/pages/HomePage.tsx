import { Box, Card, Container, Grid, Link as MuiLink, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { homeApi } from '../api/home'

const NAV_CARDS = [
  { to: '/invoices', name: '請求書', desc: '請求書の発行・入金確認' },
  { to: '/expenses', name: '経費管理', desc: '経費の登録・集計' },
  { to: '/quotes', name: '見積書', desc: '見積書の作成・請求書への変換' },
  { to: '/receivables', name: '売掛金', desc: '入金状況・未入金の確認' },
  { to: '/dashboard', name: '財務ダッシュボード', desc: '売上・経費・損益・見積状況の可視化' },
  { to: '/projects/kanban', name: '案件管理', desc: '案件の進捗・納期の管理' },
]

export default function HomePage() {
  const { data, isError } = useQuery({ queryKey: ['home-summary'], queryFn: homeApi.summary })

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

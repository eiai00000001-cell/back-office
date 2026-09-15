import { AppBar, Box, Link as MuiLink, Toolbar, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'

interface AppHeaderProps {
  backTo?: string
  backLabel?: string
}

export default function AppHeader({ backTo, backLabel }: AppHeaderProps) {
  return (
    <AppBar position="static" color="primary" elevation={0}>
      <Toolbar sx={{ justifyContent: 'space-between' }}>
        <Typography variant="h6" sx={{ fontSize: 18, fontWeight: 600 }}>
          EIAI TEC 事務管理システム
        </Typography>
        <Box>
          {backTo ? (
            <MuiLink component={RouterLink} to={backTo} sx={{ color: '#e6eef2', fontSize: 13 }} underline="hover">
              {backLabel ?? '← ホームへ'}
            </MuiLink>
          ) : (
            <MuiLink
              component={RouterLink}
              to="/settings"
              sx={{
                color: '#e6eef2',
                fontSize: 13,
                border: '1px solid rgba(255,255,255,.5)',
                padding: '5px 12px',
                borderRadius: '4px',
              }}
              underline="none"
            >
              システム設定
            </MuiLink>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  )
}

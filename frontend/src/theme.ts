import { createTheme } from '@mui/material/styles'

// mockups(docs/02_architect/mockups/)の配色トークンをそのまま反映する。
export const theme = createTheme({
  palette: {
    background: { default: '#f4f6f8', paper: '#ffffff' },
    primary: { main: '#2c5f7c', dark: '#1f4a61' },
    error: { main: '#c0392b' },
    text: { primary: '#222831', secondary: '#6b7280' },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Hiragino Kaku Gothic ProN"',
      '"Yu Gothic"',
      'Meiryo',
      'sans-serif',
    ].join(','),
    fontSize: 14,
  },
  shape: {
    borderRadius: 6,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none' },
      },
    },
  },
})

export const PAYMENT_STATUS_COLORS: Record<string, string> = {
  UNPAID: '#b91c1c',
  PARTIALLY_PAID: '#b45309',
  PAID: '#15803d',
}

export const QUOTE_STATUS_COLORS: Record<string, string> = {
  DRAFT: '#6b7280',
  CONFIRMED: '#1d4ed8',
}

export const OVERDUE_BACKGROUND = '#fdecea'

export const PROJECT_STATUS_COLORS: Record<string, string> = {
  NOT_STARTED: '#6b7280',
  IN_PROGRESS: '#1d4ed8',
  WAITING_REVIEW: '#b45309',
  DONE: '#15803d',
}

import { Box } from '@mui/material'
import { DUE_STATE_LABELS, type DueState } from '../types'

// 超過/接近の塗りつぶしバッジ(mockups SC-01・SC-16・SC-17の .state / .tag に準拠)
export function DueBadge({ state }: { state: DueState | null }) {
  if (!state) return null
  return (
    <Box
      component="span"
      sx={{
        display: 'inline-block',
        minWidth: 44,
        textAlign: 'center',
        px: 0.9,
        py: '1px',
        borderRadius: '3px',
        fontSize: 11,
        fontWeight: 700,
        color: '#fff',
        backgroundColor: state === 'OVERDUE' ? '#c0392b' : '#b45309',
      }}
    >
      {DUE_STATE_LABELS[state]}
    </Box>
  )
}

// 通知の種類などを示す薄いタグ(mockups .kind-tag)
export function KindTag({ label }: { label: string }) {
  return (
    <Box
      component="span"
      sx={{
        display: 'inline-block',
        px: 1,
        py: '1px',
        borderRadius: '3px',
        fontSize: 12,
        backgroundColor: '#eef1f4',
        color: 'text.secondary',
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </Box>
  )
}

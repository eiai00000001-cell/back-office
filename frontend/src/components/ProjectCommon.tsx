import { Box, Chip, Tab, Tabs, Typography } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { DUE_STATE_LABELS, PROJECT_STATUS_LABELS, type DueState, type ProjectStatus } from '../types'
import { PROJECT_STATUS_COLORS } from '../theme'

export function ProjectStatusChip({ status }: { status: ProjectStatus }) {
  return (
    <Chip
      size="small"
      label={PROJECT_STATUS_LABELS[status]}
      sx={{ backgroundColor: PROJECT_STATUS_COLORS[status], color: '#fff' }}
    />
  )
}

// 納期状態(超過/接近)の強調表示。表示対象外(null)は何も出さない
export function DueStateTag({ state }: { state: DueState | null }) {
  if (!state) return null
  return (
    <Typography
      component="span"
      sx={{
        ml: 0.75,
        fontSize: 12,
        fontWeight: 600,
        color: state === 'OVERDUE' ? 'error.main' : '#b45309',
      }}
    >
      {DUE_STATE_LABELS[state]}
    </Typography>
  )
}

export function ProjectTabs({ active }: { active: 'list' | 'kanban' }) {
  const navigate = useNavigate()
  return (
    <Box sx={{ mb: 2 }}>
      <Tabs value={active} onChange={(_, value) => navigate(value === 'list' ? '/projects' : '/projects/kanban')}>
        <Tab value="list" label="一覧" />
        <Tab value="kanban" label="カンバン" />
      </Tabs>
    </Box>
  )
}

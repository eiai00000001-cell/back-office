import { Link as MuiLink, MenuItem, TextField } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { projectsApi } from '../api/projects'
import { PROJECT_STATUS_LABELS } from '../types'

interface ProjectSelectProps {
  value: number | null
  onChange: (projectId: number | null) => void
  showDetailLink?: boolean
  helperText?: string
}

// SC-03・SC-05・SC-07の「案件」欄。全案件を表示し、完了済みも選択できる(詳細設計書3.21)。
export default function ProjectSelect({ value, onChange, showDetailLink, helperText }: ProjectSelectProps) {
  const { data: projects } = useQuery({ queryKey: ['projects', {}], queryFn: () => projectsApi.list() })
  const options = projects ?? []
  // 案件一覧の読込前でも現在値が消えて見えないよう、選択肢に無い値は空表示にする
  const selectValue = value !== null && options.some((p) => p.id === value) ? value : ''

  return (
    <>
      <TextField
        select
        label="案件"
        sx={{ flex: 1, minWidth: 200 }}
        value={selectValue}
        onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
        helperText={helperText}
      >
        <MenuItem value="">(案件なし)</MenuItem>
        {options.map((p) => (
          <MenuItem key={p.id} value={p.id}>
            {p.name}
            {p.status === 'DONE' ? `(${PROJECT_STATUS_LABELS.DONE})` : ''}
          </MenuItem>
        ))}
      </TextField>
      {showDetailLink && value !== null && (
        <MuiLink component={RouterLink} to={`/projects/${value}`} sx={{ whiteSpace: 'nowrap', fontSize: 13 }}>
          案件詳細へ
        </MuiLink>
      )}
    </>
  )
}

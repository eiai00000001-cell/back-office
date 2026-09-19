import { useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  Container,
  FormControlLabel,
  MenuItem,
  Radio,
  RadioGroup,
  TextField,
  Typography,
} from '@mui/material'
import { useMutation } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { reportsApi, type ReportDownload } from '../api/reports'
import { REPORT_TYPES, type ReportFormat, type ReportType } from '../types'
import { defaultReportPeriod } from '../utils/format'

const sectionTitleSx = { fontWeight: 600, mb: 1.75, pb: 1, borderBottom: '1px solid #dde1e6', fontSize: 15 }

const REPORT_MIN_YEAR = 2000
const REPORT_MAX_YEAR = 2099
const REPORT_MAX_MONTHS = 120

const isYearInRange = (ym: string) => {
  const year = Number(ym.slice(0, 4))
  return year >= REPORT_MIN_YEAR && year <= REPORT_MAX_YEAR
}
const monthCount = (from: string, to: string) =>
  (Number(to.slice(0, 4)) - Number(from.slice(0, 4))) * 12 + (Number(to.slice(5, 7)) - Number(from.slice(5, 7))) + 1

// 空データ時の通知文言は種類別(詳細設計書4.11.3)
const emptyMessage = (type: ReportType | '') =>
  type === 'monthly-pl'
    ? '対象期間にデータがありませんでした。全月0円のレポートを出力しました'
    : '対象期間にデータがありませんでした。項目名のみ出力しました'

function saveFile({ blob, filename }: ReportDownload) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

export default function ReportExportPage() {
  const initial = defaultReportPeriod()
  const [type, setType] = useState<ReportType | ''>('')
  const [from, setFrom] = useState(initial.from)
  const [to, setTo] = useState(initial.to)
  const [format, setFormat] = useState<ReportFormat>('csv')
  const [inputError, setInputError] = useState<string | null>(null)
  const [emptyNotice, setEmptyNotice] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  const download = useMutation({
    mutationFn: (args: { type: ReportType; from: string; to: string; format: ReportFormat }) =>
      reportsApi.download(args.type, args.from, args.to, args.format),
    onSuccess: (result, args) => {
      saveFile(result)
      setEmptyNotice(result.recordCount === 0 ? emptyMessage(args.type) : null)
    },
    onError: () => setFailed(true),
  })

  const submit = () => {
    setEmptyNotice(null)
    setFailed(false)
    if (type === '') return setInputError('出力する種類を選択してください')
    if (from === '') return setInputError('開始年月を入力してください')
    if (to === '') return setInputError('終了年月を入力してください')
    // 判定順はサーバー・設計(4.11.1)に揃える: 年範囲 → 開始>終了 → 上限
    if (!isYearInRange(from) || !isYearInRange(to)) {
      return setInputError(`期間の年は${REPORT_MIN_YEAR}〜${REPORT_MAX_YEAR}の範囲で指定してください`)
    }
    if (from > to) return setInputError('開始年月は終了年月以前を指定してください')
    if (monthCount(from, to) > REPORT_MAX_MONTHS) {
      return setInputError(`期間は最大${REPORT_MAX_MONTHS}か月(10年)以内で指定してください`)
    }
    setInputError(null)
    // PDFは月次損益集計レポートのみ。他の種類はCSV固定
    download.mutate({ type, from, to, format: type === 'monthly-pl' ? format : 'csv' })
  }

  return (
    <Box>
      <AppHeader backTo="/" backLabel="← ホームへ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          レポート出力
        </Typography>
        <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
          <Alert severity="info" icon={false} sx={{ mb: 2, py: 0, fontSize: 12 }}>
            CSV出力はバックアップの代わりにはなりません。
          </Alert>
          <Typography sx={sectionTitleSx}>1. 出力する種類</Typography>
          <RadioGroup value={type} onChange={(e) => setType(e.target.value as ReportType)}>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1.25 }}>
              {REPORT_TYPES.map((t) => (
                <Box
                  key={t.value}
                  sx={{
                    border: '1px solid',
                    borderColor: type === t.value ? 'primary.main' : '#dde1e6',
                    backgroundColor: type === t.value ? '#eef4f7' : undefined,
                    borderRadius: '4px',
                    px: 1.5,
                    py: 0.5,
                  }}
                >
                  <FormControlLabel
                    value={t.value}
                    control={<Radio size="small" />}
                    sx={{ alignItems: 'flex-start', m: 0, width: '100%' }}
                    label={
                      <Box sx={{ pt: 0.75 }}>
                        <Typography component="span" sx={{ fontWeight: 600, display: 'block' }}>
                          {t.name}
                        </Typography>
                        <Typography component="span" sx={{ fontSize: 12, color: 'text.secondary', display: 'block' }}>
                          {t.formats} / 期間の基準: {t.basis}
                        </Typography>
                      </Box>
                    }
                  />
                </Box>
              ))}
            </Box>
          </RadioGroup>

          <Typography sx={{ ...sectionTitleSx, mt: 3 }}>2. 対象期間</Typography>
          <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
            <TextField
              label="開始年月"
              type="month"
              size="small"
              InputLabelProps={{ shrink: true }}
              value={from}
              onChange={(e) => setFrom(e.target.value)}
            />
            <TextField
              label="終了年月"
              type="month"
              size="small"
              InputLabelProps={{ shrink: true }}
              value={to}
              onChange={(e) => setTo(e.target.value)}
            />
            {type === 'monthly-pl' && (
              <TextField
                select
                label="出力形式"
                size="small"
                sx={{ minWidth: 140 }}
                value={format}
                onChange={(e) => setFormat(e.target.value as ReportFormat)}
              >
                <MenuItem value="pdf">PDF</MenuItem>
                <MenuItem value="csv">CSV</MenuItem>
              </TextField>
            )}
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: 12, mt: 1 }}>
            既定は現在月を含む直近12ヶ月です。出力形式は月次損益集計レポート選択時のみ表示され、他の種類はCSV固定です。
          </Typography>
          {inputError && (
            <Typography color="error" sx={{ fontSize: 12, mt: 1 }}>
              {inputError}
            </Typography>
          )}
          <Box sx={{ mt: 2 }}>
            <Button variant="contained" onClick={submit} disabled={download.isPending}>
              出力
            </Button>
          </Box>
        </Card>

        {emptyNotice !== null && (
          <Alert severity="success" icon={false}>
            {emptyNotice}
          </Alert>
        )}
        {failed && <Alert severity="warning">出力に失敗しました</Alert>}
      </Container>
    </Box>
  )
}

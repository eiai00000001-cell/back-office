import {
  Box,
  Button,
  IconButton,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
} from '@mui/material'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import { TAX_CATEGORY_LABELS, type ItemInput, type TaxCategory } from '../types'
import { calculateItemAmount, calculateTotals } from '../utils/taxCalculation'
import { formatCurrency } from '../utils/format'

const TAX_SUBTOTAL_LABELS: Record<TaxCategory, string> = {
  STANDARD_10: '小計(標準10%)',
  NON_TAXABLE: '小計(非課税)',
  OUT_OF_SCOPE: '小計(不課税)',
}

interface ItemsEditorProps {
  items: ItemInput[]
  onChange: (items: ItemInput[]) => void
}

const emptyItem = (): ItemInput => ({
  item_name: '',
  quantity: 1,
  unit_price: 0,
  tax_category: 'STANDARD_10',
})

export default function ItemsEditor({ items, onChange }: ItemsEditorProps) {
  const totals = calculateTotals(items)

  const updateItem = (index: number, patch: Partial<ItemInput>) => {
    const next = items.map((item, i) => (i === index ? { ...item, ...patch } : item))
    onChange(next)
  }

  const removeItem = (index: number) => {
    onChange(items.filter((_, i) => i !== index))
  }

  const addItem = () => {
    onChange([...items, emptyItem()])
  }

  return (
    <Box>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>品目名</TableCell>
            <TableCell sx={{ width: 110 }}>数量</TableCell>
            <TableCell sx={{ width: 130 }}>単価</TableCell>
            <TableCell sx={{ width: 140 }}>税区分</TableCell>
            <TableCell sx={{ width: 120 }} align="right">
              金額
            </TableCell>
            <TableCell sx={{ width: 60 }} align="center">
              操作
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((item, index) => (
            <TableRow key={index}>
              <TableCell>
                <TextField
                  size="small"
                  fullWidth
                  value={item.item_name}
                  onChange={(e) => updateItem(index, { item_name: e.target.value })}
                  inputProps={{ maxLength: 100 }}
                />
              </TableCell>
              <TableCell>
                <TextField
                  size="small"
                  type="number"
                  fullWidth
                  value={item.quantity}
                  onChange={(e) => updateItem(index, { quantity: Number(e.target.value) })}
                  inputProps={{ step: '0.01' }}
                />
              </TableCell>
              <TableCell>
                <TextField
                  size="small"
                  type="number"
                  fullWidth
                  value={item.unit_price}
                  onChange={(e) => updateItem(index, { unit_price: Number(e.target.value) })}
                />
              </TableCell>
              <TableCell>
                <TextField
                  size="small"
                  select
                  fullWidth
                  value={item.tax_category}
                  onChange={(e) => updateItem(index, { tax_category: e.target.value as TaxCategory })}
                >
                  {Object.entries(TAX_CATEGORY_LABELS).map(([value, label]) => (
                    <MenuItem key={value} value={value}>
                      {label}
                    </MenuItem>
                  ))}
                </TextField>
              </TableCell>
              <TableCell align="right">{formatCurrency(calculateItemAmount(item.quantity, item.unit_price))}</TableCell>
              <TableCell align="center">
                <IconButton size="small" aria-label="削除" onClick={() => removeItem(index)}>
                  <DeleteOutlineIcon fontSize="small" color="error" />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Button sx={{ mt: 1 }} variant="outlined" size="small" onClick={addItem}>
        明細行を追加
      </Button>

      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
        <Table size="small" sx={{ width: 'auto', minWidth: 340 }}>
          <TableBody>
            {(Object.keys(totals.subtotalByTax) as TaxCategory[]).map((taxCategory) => (
              <TableRow key={taxCategory}>
                <TableCell sx={{ border: 'none' }}>{TAX_SUBTOTAL_LABELS[taxCategory]}</TableCell>
                <TableCell sx={{ border: 'none' }} align="right">
                  {formatCurrency(totals.subtotalByTax[taxCategory] ?? 0)}
                </TableCell>
              </TableRow>
            ))}
            {totals.subtotalByTax.STANDARD_10 !== undefined && (
              <TableRow>
                <TableCell sx={{ border: 'none' }}>消費税額(標準10%)</TableCell>
                <TableCell sx={{ border: 'none' }} align="right">
                  {formatCurrency(totals.taxAmount)}
                </TableCell>
              </TableRow>
            )}
            <TableRow>
              <TableCell sx={{ borderTop: '1px solid #dde1e6', fontWeight: 700, fontSize: 16 }}>合計金額</TableCell>
              <TableCell sx={{ borderTop: '1px solid #dde1e6', fontWeight: 700, fontSize: 16 }} align="right">
                {formatCurrency(totals.totalAmount)}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Box>
    </Box>
  )
}

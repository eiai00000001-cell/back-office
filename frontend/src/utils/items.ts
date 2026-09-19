import type { ItemInput, ItemResponse } from '../types'

// APIレスポンスの品目明細をフォーム用(ItemInput)へ変換する。
// バックエンド(Pydantic v2)はDecimal型のquantityを文字列("1.00")でJSON化するため、
// 数値へ正規化してから編集・検証・再計算・保存に使う(不具合#1)。
// quantityはNUMERIC(10,2)のためdoubleで桁が崩れない。保存時はnumberで送り、サーバー側で再度Decimal検証される。
export function toItemInputs(items: ItemResponse[]): ItemInput[] {
  return items.map((item) => ({
    id: item.id,
    item_name: item.item_name,
    quantity: Number(item.quantity),
    unit_price: Number(item.unit_price),
    tax_category: item.tax_category,
    clientKey: String(item.id),
  }))
}

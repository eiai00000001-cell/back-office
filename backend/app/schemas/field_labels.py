"""422メッセージ(必須欠落・文字数超過)に用いる項目名(画面表示ラベル)の対応表。管理箇所はここのみ。"""

# リクエストボディのフィールド名 -> 画面ラベル
FIELD_LABELS: dict[str, str] = {
    "name": "名称",  # 取引先。氏名・案件名は PATH_LABEL_OVERRIDES で上書き
    "postal_code": "郵便番号",
    "address": "住所",
    "contact_person": "担当者名",
    "contact_info": "連絡先",
    "business_name": "屋号",
    "invoice_registration_number": "登録番号",
    "client_id": "取引先",
    "project_id": "案件",
    "issue_date": "発行日",
    "due_date": "支払期限",
    "expiry_date": "有効期限",
    "items": "明細",
    "item_name": "品目名",
    "quantity": "数量",
    "unit_price": "単価",
    "tax_category": "税区分",
    "remarks": "備考",
    "status": "ステータス",
    "description": "概要メモ",
    "expense_date": "発生日",
    "account_category": "勘定科目",
    "amount": "金額",
    "payee": "支払先",
    "payment_method": "支払方法",
    "memo": "メモ",
    "payment_date": "入金日",
    "category": "種別",
    "is_recurring": "毎年繰り返し",
    "source_type": "通知の種類",
    "source_id": "通知の対象",
}

# (リクエストパスの部分文字列, フィールド名) -> 画面ラベル。同名フィールドで画面ラベルが異なるもの。
PATH_LABEL_OVERRIDES: dict[tuple[str, str], str] = {
    ("/company-profile", "name"): "氏名",
    ("/projects", "name"): "案件名",
    ("/projects", "due_date"): "納期",
    ("/deadlines", "due_date"): "期限日",
    ("/payments", "amount"): "入金額",
    ("/payments", "remarks"): "備考",
}


def resolve_label(path: str, field: str) -> str | None:
    for (path_part, name), label in PATH_LABEL_OVERRIDES.items():
        if name == field and path_part in path:
            return label
    return FIELD_LABELS.get(field)

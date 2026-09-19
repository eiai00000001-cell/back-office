"""422メッセージの日本語化(必須項目の欠落 / 文字数超過)。"""
import pytest

ITEM = {"item_name": "作業", "quantity": 1, "unit_price": 100, "tax_category": "STANDARD_10"}


def _cid(app_client):
    return app_client.post("/api/clients", json={"name": "サンプル商事"}).json()["id"]


def _detail(r):
    assert r.status_code == 422
    return r.json()["detail"]


@pytest.mark.parametrize(
    "path,method,body,expected",
    [
        ("/api/clients", "post", {}, "名称は必須です"),
        ("/api/company-profile", "put", {}, "氏名は必須です"),
        ("/api/projects", "post", {}, "案件名は必須です"),
        ("/api/expenses", "post", {}, "発生日は必須です"),
        ("/api/expenses", "post", {"expense_date": "2026-09-01"}, "勘定科目は必須です"),
        ("/api/expenses", "post", {"expense_date": "2026-09-01", "account_category": "消耗品費"}, "金額は必須です"),
        ("/api/invoices", "post", {}, "取引先は必須です"),
        ("/api/invoices", "post", {"client_id": 1}, "明細は必須です"),
        ("/api/invoices", "post", {"client_id": 1, "items": [{}]}, "品目名は必須です"),
        (
            "/api/invoices",
            "post",
            {"client_id": 1, "items": [{"item_name": "a"}]},
            "数量は必須です",
        ),
        ("/api/quotes", "post", {}, "取引先は必須です"),
    ],
)
def test_missing_field_is_japanese(app_client, path, method, body, expected):
    assert _detail(getattr(app_client, method)(path, json=body)) == expected


def test_missing_payment_fields(app_client):
    cid = _cid(app_client)
    inv = app_client.post(
        "/api/invoices",
        json={"client_id": cid, "issue_date": "2026-09-01", "due_date": "2026-09-30", "items": [ITEM]},
    ).json()
    r = app_client.post(f"/api/invoices/{inv['id']}/payments", json={})
    assert _detail(r) == "入金日は必須です"
    r = app_client.post(f"/api/invoices/{inv['id']}/payments", json={"payment_date": "2026-09-05"})
    assert _detail(r) == "入金額は必須です"


def test_missing_status_change(app_client):
    p = app_client.post("/api/projects", json={"name": "P"}).json()
    r = app_client.patch(f"/api/projects/{p['id']}/status", json={})
    assert _detail(r) == "ステータスは必須です"


def test_empty_body_is_japanese(app_client):
    r = app_client.post("/api/clients", content=b"", headers={"content-type": "application/json"})
    detail = _detail(r)
    assert "Field required" not in detail and "required" not in detail
    assert detail == "入力内容を確認してください"


@pytest.mark.parametrize(
    "path,method,field,limit,label",
    [
        ("/api/clients", "post", "name", 100, "名称"),
        ("/api/clients", "post", "postal_code", 8, "郵便番号"),
        ("/api/clients", "post", "address", 200, "住所"),
        ("/api/clients", "post", "contact_person", 50, "担当者名"),
        ("/api/clients", "post", "contact_info", 200, "連絡先"),
        ("/api/company-profile", "put", "name", 50, "氏名"),
        ("/api/company-profile", "put", "business_name", 100, "屋号"),
        ("/api/company-profile", "put", "address", 200, "住所"),
        ("/api/company-profile", "put", "contact_info", 200, "連絡先"),
        ("/api/projects", "post", "description", 1000, "概要メモ"),
    ],
)
def test_too_long_simple_bodies(app_client, path, method, field, limit, label):
    base = {"name": "サンプル"}
    if path == "/api/projects":
        base = {"name": "P"}
    body = {**base, field: "あ" * (limit + 1)}
    assert _detail(getattr(app_client, method)(path, json=body)) == f"{label}は{limit}文字以内で入力してください"


def test_too_long_documents_and_expense_payment(app_client):
    cid = _cid(app_client)
    long1000 = "あ" * 1001
    inv_body = {"client_id": cid, "issue_date": "2026-09-01", "due_date": "2026-09-30", "items": [ITEM]}
    assert _detail(app_client.post("/api/invoices", json={**inv_body, "remarks": long1000})) == (
        "備考は1000文字以内で入力してください"
    )
    q_body = {"client_id": cid, "issue_date": "2026-09-01", "expiry_date": "2026-09-30", "items": [ITEM]}
    assert _detail(app_client.post("/api/quotes", json={**q_body, "remarks": long1000})) == (
        "備考は1000文字以内で入力してください"
    )
    exp = {"expense_date": "2026-09-05", "account_category": "消耗品費", "amount": 1000}
    assert _detail(app_client.post("/api/expenses", json={**exp, "payee": "あ" * 101})) == (
        "支払先は100文字以内で入力してください"
    )
    assert _detail(app_client.post("/api/expenses", json={**exp, "memo": "あ" * 501})) == (
        "メモは500文字以内で入力してください"
    )
    inv = app_client.post("/api/invoices", json=inv_body).json()
    r = app_client.post(
        f"/api/invoices/{inv['id']}/payments",
        json={"payment_date": "2026-09-05", "amount": 100, "remarks": "あ" * 201},
    )
    assert _detail(r) == "備考は200文字以内で入力してください"


def test_too_long_item_name(app_client):
    cid = _cid(app_client)
    item = {**ITEM, "item_name": "あ" * 101}
    r = app_client.post(
        "/api/invoices",
        json={"client_id": cid, "issue_date": "2026-09-01", "due_date": "2026-09-30", "items": [item]},
    )
    assert _detail(r) == "品目名は100文字以内で入力してください"


def test_existing_japanese_messages_unchanged(app_client):
    assert _detail(app_client.post("/api/projects", json={"name": "あ" * 101})) == (
        "案件名は100文字以内で入力してください"
    )
    assert _detail(app_client.post("/api/clients", json={"name": " "})) == "名称を入力してください"
    assert _detail(app_client.post("/api/projects", json={"name": "P", "due_date": "x"})) == (
        "納期は日付(YYYY-MM-DD)で入力してください"
    )

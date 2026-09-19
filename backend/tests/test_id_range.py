"""ID入力(ボディ・パス・クエリ)の範囲検証(テスト結果報告書 不具合#2)。
SQLite INTEGERの範囲外(例: 2^70)を渡しても500にならず422を返すこと。"""
import pytest

HUGE = 2**70


def _client_id(app_client):
    return app_client.post("/api/clients", json={"name": "サンプル商事"}).json()["id"]


@pytest.mark.parametrize("kind", ["invoices", "quotes", "expenses"])
def test_link_project_with_huge_id_returns_422(app_client, kind):
    cid = _client_id(app_client)
    if kind == "expenses":
        body = {"expense_date": "2026-09-05", "account_category": "消耗品費", "amount": 1000}
    else:
        body = {
            "client_id": cid,
            "issue_date": "2026-09-01",
            "items": [{"item_name": "作業", "quantity": 1, "unit_price": 100, "tax_category": "STANDARD_10"}],
        }
        body["due_date" if kind == "invoices" else "expiry_date"] = "2026-09-30"
    doc = app_client.post(f"/api/{kind}", json=body).json()
    r = app_client.put(f"/api/{kind}/{doc['id']}/project", json={"project_id": HUGE})
    assert r.status_code == 422
    assert r.json()["detail"] == "IDの値が正しくありません"


@pytest.mark.parametrize("value", [0, -1, HUGE])
def test_link_project_rejects_out_of_range_values(app_client, value):
    cid = _client_id(app_client)
    inv = app_client.post(
        "/api/invoices",
        json={
            "client_id": cid,
            "issue_date": "2026-09-01",
            "due_date": "2026-09-30",
            "items": [{"item_name": "作業", "quantity": 1, "unit_price": 100, "tax_category": "STANDARD_10"}],
        },
    ).json()
    r = app_client.put(f"/api/invoices/{inv['id']}/project", json={"project_id": value})
    assert r.status_code == 422
    assert r.json()["detail"] == "IDの値が正しくありません"


def test_body_client_id_and_project_id_huge_return_422(app_client):
    item = {"item_name": "作業", "quantity": 1, "unit_price": 100, "tax_category": "STANDARD_10"}
    base = {"issue_date": "2026-09-01", "due_date": "2026-09-30", "items": [item]}
    assert app_client.post("/api/invoices", json={**base, "client_id": HUGE}).status_code == 422
    cid = _client_id(app_client)
    assert app_client.post("/api/invoices", json={**base, "client_id": cid, "project_id": HUGE}).status_code == 422
    assert app_client.post("/api/projects", json={"name": "P", "client_id": HUGE}).status_code == 422


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", f"/api/clients/{HUGE}"),
        ("get", f"/api/invoices/{HUGE}"),
        ("get", f"/api/quotes/{HUGE}"),
        ("get", f"/api/expenses/{HUGE}"),
        ("get", f"/api/projects/{HUGE}"),
        ("delete", f"/api/invoices/{HUGE}"),
        ("delete", f"/api/payments/{HUGE}"),
        ("get", f"/api/invoices?client_id={HUGE}"),
        ("get", f"/api/quotes?client_id={HUGE}"),
        ("get", f"/api/projects?client_id={HUGE}"),
    ],
)
def test_path_and_query_huge_ids_return_422(app_client, method, path):
    r = getattr(app_client, method)(path)
    assert r.status_code == 422
    assert r.json()["detail"] == "IDの値が正しくありません"


@pytest.mark.parametrize("value", [0, -5])
def test_path_zero_and_negative_ids_return_japanese_422(app_client, value):
    r = app_client.get(f"/api/clients/{value}")
    assert r.status_code == 422
    assert r.json()["detail"] == "IDの値が正しくありません"


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/clients/abc"),
        ("get", "/api/invoices/abc"),
        ("delete", "/api/payments/abc"),
        ("get", "/api/invoices?client_id=abc"),
        ("get", "/api/projects?client_id=abc"),
        ("get", "/api/clients/1.5"),
    ],
)
def test_non_numeric_path_and_query_ids_return_japanese_422(app_client, method, path):
    r = getattr(app_client, method)(path)
    assert r.status_code == 422
    assert r.json()["detail"] == "IDの値が正しくありません"


@pytest.mark.parametrize("value", ["abc", None, [1], {"a": 1}, 1.5])
def test_non_numeric_body_ids_return_japanese_422(app_client, value):
    item = {"item_name": "作業", "quantity": 1, "unit_price": 100, "tax_category": "STANDARD_10"}
    base = {"issue_date": "2026-09-01", "due_date": "2026-09-30", "items": [item]}
    r = app_client.post("/api/invoices", json={**base, "client_id": _client_id(app_client), "project_id": value})
    if value is None:
        assert r.status_code in (200, 201)  # project_idは任意
        return
    assert r.status_code == 422
    assert r.json()["detail"] == "IDの値が正しくありません"
    r = app_client.post("/api/projects", json={"name": "P", "client_id": value})
    assert r.status_code == 422
    assert r.json()["detail"] == "IDの値が正しくありません"


def test_non_id_type_error_message_unchanged(app_client):
    r = app_client.post("/api/clients", json={"name": ["x"]})
    assert r.status_code == 422
    assert r.json()["detail"] != "IDの値が正しくありません"

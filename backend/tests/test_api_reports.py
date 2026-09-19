"""レポート出力API(F-10)。詳細設計書4.11.1章・7章。"""
import csv
import io
from datetime import date
from urllib.parse import unquote


def _seed(app_client):
    cid = app_client.post("/api/clients", json={"name": "サンプル商事"}).json()["id"]
    app_client.post(
        "/api/invoices",
        json={"client_id": cid, "issue_date": "2026-09-01", "due_date": "2026-09-30",
              "items": [{"item_name": "作業", "quantity": 1, "unit_price": 10000, "tax_category": "STANDARD_10"}]},
    )
    app_client.post("/api/expenses", json={"expense_date": "2026-09-05", "account_category": "消耗品費", "amount": 1000})


def _get(app_client, kind, **params):
    return app_client.get(f"/api/reports/{kind}", params=params)


def test_csv_response_headers_and_body(app_client):
    _seed(app_client)
    r = _get(app_client, "invoices", period_from="2026-08", period_to="2026-09")
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/csv; charset=utf-8"
    disposition = r.headers["content-disposition"]
    assert disposition.startswith("attachment; filename*=UTF-8''")
    assert unquote(disposition.split("''", 1)[1]) == "請求書一覧_202608-202609.csv"
    assert r.headers["x-record-count"] == "1"
    assert r.content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert rows[1][0] == "2026-0001" and rows[1][7] == "11000"


def test_empty_period_returns_header_only_with_count_zero(app_client):
    r = _get(app_client, "expenses", period_from="2020-01", period_to="2020-12")
    assert r.status_code == 200
    assert r.headers["x-record-count"] == "0"
    assert len(r.content.decode("utf-8-sig").strip().split("\r\n")) == 1


def test_all_seven_types_return_200(app_client):
    _seed(app_client)
    for kind in ("invoices", "payments", "quotes", "expenses", "monthly-pl", "projects", "accounting-export"):
        r = _get(app_client, kind, period_from="2026-08", period_to="2026-09")
        assert r.status_code == 200, kind
        assert "x-record-count" in r.headers, kind


def test_monthly_pl_pdf(app_client):
    _seed(app_client)
    r = _get(app_client, "monthly-pl", period_from="2026-08", period_to="2026-09", format="pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert unquote(r.headers["content-disposition"].split("''", 1)[1]) == "月次損益集計レポート_202608-202609.pdf"
    assert r.headers["x-record-count"] == "1"


def test_pdf_for_other_type_is_422(app_client):
    r = _get(app_client, "invoices", period_from="2026-08", period_to="2026-09", format="pdf")
    assert r.status_code == 422
    assert r.json()["detail"] == "この種類はCSVのみ出力できます"


def test_start_after_end_is_422(app_client):
    r = _get(app_client, "invoices", period_from="2026-10", period_to="2026-09")
    assert r.status_code == 422
    assert r.json()["detail"] == "開始年月は終了年月以前を指定してください"


def test_invalid_period_format_is_422(app_client):
    for bad in ("2026-13", "202609", "2026-9", "abc", "2026-09-01"):
        r = _get(app_client, "invoices", period_from=bad, period_to="2026-09")
        assert r.status_code == 422, bad
        assert r.json()["detail"] == "年月はYYYY-MM形式で指定してください"


def test_invalid_format_value_is_422(app_client):
    assert _get(app_client, "invoices", format="xlsx").status_code == 422


def test_unknown_type_is_404(app_client):
    assert _get(app_client, "unknown").status_code == 404


def test_default_period_is_last_12_months(app_client):
    _seed(app_client)
    today = date.today()
    r = _get(app_client, "monthly-pl")
    assert r.status_code == 200
    filename = unquote(r.headers["content-disposition"].split("''", 1)[1])
    assert filename.endswith(f"{today.year:04d}{today.month:02d}.csv")
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert len({row[0] for row in rows[1:]}) == 12


def test_formula_injection_is_neutralised(app_client):
    app_client.post("/api/expenses", json={"expense_date": "2026-09-05", "account_category": "雑費", "amount": 100, "memo": "=1+1"})
    r = _get(app_client, "expenses", period_from="2026-09", period_to="2026-09")
    assert "'=1+1" in r.content.decode("utf-8-sig")


def test_report_is_read_only(app_client):
    _seed(app_client)
    before = app_client.get("/api/invoices").json()
    _get(app_client, "accounting-export", period_from="2026-09", period_to="2026-09")
    assert app_client.get("/api/invoices").json() == before


MSG_YEAR = "期間の年は2000〜2099の範囲で指定してください"
MSG_MONTHS = "期間は最大120か月(10年)以内で指定してください"


def test_year_out_of_range_is_422_not_500(app_client):
    for bad in ("0000-01", "1999-12", "2100-01", "9999-12"):
        for key in ("period_from", "period_to"):
            params = {"period_from": "2026-01", "period_to": "2026-09"}
            params[key] = bad
            r = _get(app_client, "invoices", **params)
            assert r.status_code == 422, (key, bad)
            assert r.json()["detail"] == MSG_YEAR


def test_year_boundaries_2000_and_2099_are_accepted(app_client):
    assert _get(app_client, "invoices", period_from="2000-01", period_to="2000-12").status_code == 200
    assert _get(app_client, "invoices", period_from="2099-01", period_to="2099-12").status_code == 200


def test_year_range_applies_to_pdf_and_all_types(app_client):
    for kind in ("invoices", "payments", "quotes", "expenses", "monthly-pl", "projects", "accounting-export"):
        r = _get(app_client, kind, period_from="0000-01", period_to="2026-09")
        assert r.status_code == 422 and r.json()["detail"] == MSG_YEAR, kind
    r = _get(app_client, "monthly-pl", period_from="0000-01", period_to="2026-09", format="pdf")
    assert r.status_code == 422 and r.json()["detail"] == MSG_YEAR


def test_120_months_ok_and_121_months_rejected(app_client):
    assert _get(app_client, "invoices", period_from="2000-01", period_to="2009-12").status_code == 200
    r = _get(app_client, "invoices", period_from="2000-01", period_to="2010-01")
    assert r.status_code == 422 and r.json()["detail"] == MSG_MONTHS


def test_over_limit_pdf_does_not_generate(app_client):
    r = _get(app_client, "monthly-pl", period_from="2000-01", period_to="2010-01", format="pdf")
    assert r.status_code == 422 and r.json()["detail"] == MSG_MONTHS


def test_single_side_specified_is_checked_after_completion(app_client):
    r = _get(app_client, "invoices", period_from="2000-01")
    assert r.status_code == 422 and r.json()["detail"] == MSG_MONTHS
    # 設計書4.11.1は「開始>終了」としているが、補完した開始(現在月-11か月)は2099-12より前のため上限超過となる
    r = _get(app_client, "invoices", period_to="2099-12")
    assert r.status_code == 422 and r.json()["detail"] == MSG_MONTHS


def test_reverse_order_reports_order_message_not_limit(app_client):
    r = _get(app_client, "invoices", period_from="2010-01", period_to="2000-01")
    assert r.json()["detail"] == "開始年月は終了年月以前を指定してください"


def test_year_check_precedes_limit_and_format_checks(app_client):
    r = _get(app_client, "unknown", period_from="0000-01", period_to="2099-12")
    assert r.status_code == 422 and r.json()["detail"] == MSG_YEAR
    r = _get(app_client, "unknown", period_from="2000-01", period_to="2010-01")
    assert r.status_code == 422 and r.json()["detail"] == MSG_MONTHS

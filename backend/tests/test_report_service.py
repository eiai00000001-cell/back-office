"""レポート出力(F-10)。詳細設計書4.11章。ReportServiceと種類別レポート作成のテスト。"""
import csv
import io
from datetime import date

import pytest

from app.exceptions import UnprocessableError
from app.models.client import Client
from app.models.expense import Expense
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.project import Project
from app.models.quote import Quote
from app.repositories.company_profile_repository import CompanyProfileRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.report_repository import ReportRepository
from app.services.financial_aggregation_service import FinancialAggregationService
from app.services.payment_service import PaymentService
from app.services.pdf_generation_service import PdfGenerationService
from app.services.report_service import ReportService, build_report_service
from tests.conftest import now_iso

FROM, TO = "2026-08-01", "2026-09-30"


def rows_of(file) -> list[list[str]]:
    assert file.content.startswith(b"\xef\xbb\xbf")
    return list(csv.reader(io.StringIO(file.content.decode("utf-8-sig"), newline="")))


@pytest.fixture()
def svc(db_session) -> ReportService:
    return build_report_service(db_session)


@pytest.fixture()
def seeded(db_session):
    c1 = Client(name="サンプル商事", created_at=now_iso(), updated_at=now_iso())
    c2 = Client(name="=悪意ある名前", created_at=now_iso(), updated_at=now_iso())
    db_session.add_all([c1, c2])
    db_session.flush()
    p1 = Project(name="サイト制作", client_id=c1.id, status="IN_PROGRESS", due_date="2026-09-15", created_at=now_iso(), updated_at=now_iso())
    p2 = Project(name="納期のみ", status="NOT_STARTED", due_date="2026-08-20", created_at=now_iso(), updated_at=now_iso())
    p3 = Project(name="請求のみ", client_id=c2.id, status="DONE", due_date=None, created_at=now_iso(), updated_at=now_iso())
    p4 = Project(name="範囲外", status="DONE", due_date="2026-12-01", created_at=now_iso(), updated_at=now_iso())
    db_session.add_all([p1, p2, p3, p4])
    db_session.flush()

    def inv(number, client, issue, total, tax, project=None, due="2026-10-31"):
        i = Invoice(invoice_number=number, client_id=client.id, issue_date=issue, due_date=due, subtotal_amount=total - tax,
                    tax_amount=tax, total_amount=total, project_id=project.id if project else None,
                    created_at=now_iso(), updated_at=now_iso())
        db_session.add(i)
        return i

    i1 = inv("2026-0002", c1, "2026-09-05", 11000, 1000, p1)
    i2 = inv("2026-0001", c1, "2026-08-10", 22000, 2000)
    i3 = inv("2026-0003", c2, "2026-08-10", 5500, 500, p3)
    inv("2026-0004", c1, None, 999, 0)  # 発行日未設定は出力対象外
    inv("2026-0005", c1, "2026-07-31", 111, 0)  # 期間外
    db_session.flush()
    db_session.add_all([
        Payment(invoice_id=i1.id, payment_date="2026-09-20", amount=4000, remarks="=内金", created_at=now_iso()),
        Payment(invoice_id=i1.id, payment_date="2026-09-01", amount=1000, remarks=None, created_at=now_iso()),
        Payment(invoice_id=i2.id, payment_date="2026-08-31", amount=22000, remarks="全額", created_at=now_iso()),
        Payment(invoice_id=i2.id, payment_date="2026-10-01", amount=1, created_at=now_iso()),  # 期間外
    ])

    def quote(number, client, issue, total, status, project=None):
        q = Quote(quote_number=number, client_id=client.id, issue_date=issue, expiry_date="2026-12-31", status=status,
                  subtotal_amount=total, tax_amount=0, total_amount=total, project_id=project.id if project else None,
                  created_at=now_iso(), updated_at=now_iso())
        db_session.add(q)

    quote("2026-0002", c1, "2026-09-01", 3300, "CONFIRMED", p1)
    quote("2026-0001", c1, "2026-08-15", 1100, "DRAFT")
    quote("2026-0003", c1, None, 10, "DRAFT")
    quote("2026-0004", c1, "2026-10-01", 20, "DRAFT")

    def exp(date_, cat, amount, tax="STANDARD_10", payee=None, method=None, memo=None, project=None):
        db_session.add(Expense(expense_date=date_, account_category=cat, amount=amount, tax_category=tax, payee=payee,
                               payment_method=method, memo=memo, project_id=project.id if project else None,
                               created_at=now_iso(), updated_at=now_iso()))

    exp("2026-09-02", "通信費", 3000, payee="通信会社", method="CREDIT_CARD", memo="回線", project=p1)
    exp("2026-08-05", "雑費", 500, tax="NON_TAXABLE", memo="-メモ")
    exp("2026-08-05", "通信費", 700, tax="NOT_APPLICABLE", method="CASH")
    exp("2026-07-31", "雑費", 1)
    db_session.commit()
    return {"p1": p1, "p2": p2, "p3": p3, "i1": i1, "i2": i2, "i3": i3}


class TestValidation:
    def test_unknown_type(self, svc):
        with pytest.raises(Exception) as exc:
            svc.generate("nope", FROM, TO, "csv")
        assert "nope" in str(exc.value) or "見つかりません" in str(exc.value)

    def test_pdf_only_for_monthly_pl(self, svc):
        with pytest.raises(UnprocessableError, match="この種類はCSVのみ出力できます"):
            svc.generate("invoices", FROM, TO, "pdf")

    def test_from_after_to(self, svc):
        with pytest.raises(UnprocessableError, match="開始年月は終了年月以前を指定してください"):
            svc.generate("invoices", TO, FROM, "csv")

    def test_invalid_format(self, svc):
        with pytest.raises(UnprocessableError):
            svc.generate("invoices", FROM, TO, "xlsx")


class TestInvoices:
    def test_header_rows_order_and_labels(self, svc, seeded):
        f = svc.generate("invoices", FROM, TO, "csv")
        r = rows_of(f)
        assert r[0] == ["請求書番号", "取引先", "案件", "発行日", "支払期限", "小計", "消費税額", "合計", "入金ステータス"]
        assert r[1:] == [
            ["2026-0001", "サンプル商事", "", "2026-08-10", "2026-10-31", "20000", "2000", "22000", "入金済み"],
            ["2026-0003", "'=悪意ある名前", "請求のみ", "2026-08-10", "2026-10-31", "5000", "500", "5500", "未入金"],
            ["2026-0002", "サンプル商事", "サイト制作", "2026-09-05", "2026-10-31", "10000", "1000", "11000", "一部入金"],
        ]
        assert f.record_count == 3
        assert f.filename == "請求書一覧_202608-202609.csv"
        assert f.content_type.startswith("text/csv")

    def test_empty_period_header_only(self, svc, seeded):
        f = svc.generate("invoices", "2020-01-01", "2020-01-31", "csv")
        assert len(rows_of(f)) == 1 and f.record_count == 0


class TestPayments:
    def test_rows(self, svc, seeded):
        r = rows_of(svc.generate("payments", FROM, TO, "csv"))
        assert r[0] == ["請求書番号", "入金日", "入金額", "備考"]
        assert r[1:] == [
            ["2026-0001", "2026-08-31", "22000", "全額"],
            ["2026-0002", "2026-09-01", "1000", ""],
            ["2026-0002", "2026-09-20", "4000", "'=内金"],
        ]


class TestQuotes:
    def test_rows(self, svc, seeded):
        f = svc.generate("quotes", FROM, TO, "csv")
        r = rows_of(f)
        assert r[0] == ["見積書番号", "取引先", "案件", "発行日", "有効期限", "合計", "ステータス"]
        assert r[1:] == [
            ["2026-0001", "サンプル商事", "", "2026-08-15", "2026-12-31", "1100", "作成中"],
            ["2026-0002", "サンプル商事", "サイト制作", "2026-09-01", "2026-12-31", "3300", "確定"],
        ]
        assert f.filename.startswith("見積書一覧_")


class TestExpenses:
    def test_rows(self, svc, seeded):
        r = rows_of(svc.generate("expenses", FROM, TO, "csv"))
        assert r[0] == ["発生日", "勘定科目", "金額", "税区分", "支払先", "支払方法", "メモ"]
        assert r[1:] == [
            ["2026-08-05", "雑費", "500", "非課税", "", "", "'-メモ"],
            ["2026-08-05", "通信費", "700", "対象外", "", "現金", ""],
            ["2026-09-02", "通信費", "3000", "標準10%", "通信会社", "クレジットカード", "回線"],
        ]


class TestProjectSummary:
    def test_target_projects_and_counts(self, svc, seeded):
        r = rows_of(svc.generate("projects", FROM, TO, "csv"))
        assert r[0] == ["案件名", "取引先", "ステータス", "納期", "見積件数", "見積金額", "請求件数", "請求金額"]
        assert r[1:] == [
            ["納期のみ", "", "未着手", "2026-08-20", "0", "0", "0", "0"],
            ["サイト制作", "サンプル商事", "進行中", "2026-09-15", "1", "3300", "1", "11000"],
            ["請求のみ", "'=悪意ある名前", "完了", "", "0", "0", "1", "5500"],
        ]

    def test_totals_match_list_reports(self, svc, seeded):
        summary = rows_of(svc.generate("projects", FROM, TO, "csv"))[1:]
        inv_by_project = {}
        for row in rows_of(svc.generate("invoices", FROM, TO, "csv"))[1:]:
            if row[2]:
                inv_by_project[row[2]] = inv_by_project.get(row[2], 0) + int(row[7])
        for row in summary:
            assert inv_by_project.get(row[0], 0) == int(row[7])


class TestAccountingExport:
    def test_rows_sorted_and_columns(self, svc, seeded):
        r = rows_of(svc.generate("accounting-export", FROM, TO, "csv"))
        assert r[0] == ["区分", "日付", "勘定科目", "取引先・支払先", "摘要", "金額", "うち消費税額", "税区分", "書類番号"]
        assert r[1:] == [
            ["経費", "2026-08-05", "雑費", "", "'-メモ", "500", "", "非課税", ""],
            ["経費", "2026-08-05", "通信費", "", "", "700", "", "対象外", ""],
            ["売上", "2026-08-10", "売上高", "サンプル商事", "2026-0001", "22000", "2000", "", "2026-0001"],
            ["売上", "2026-08-10", "売上高", "'=悪意ある名前", "2026-0003 / 請求のみ", "5500", "500", "", "2026-0003"],
            ["経費", "2026-09-02", "通信費", "通信会社", "回線", "3000", "", "標準10%", ""],
            ["売上", "2026-09-05", "売上高", "サンプル商事", "2026-0002 / サイト制作", "11000", "1000", "", "2026-0002"],
        ]

    def test_totals_match_aggregation(self, svc, seeded, db_session):
        r = rows_of(svc.generate("accounting-export", FROM, TO, "csv"))[1:]
        agg = FinancialAggregationService(InvoiceRepository(db_session), PaymentRepository(db_session), ExpenseRepository(db_session))
        assert sum(int(x[5]) for x in r if x[0] == "売上") == sum(agg.monthly_sales(FROM, TO).values())
        assert sum(int(x[5]) for x in r if x[0] == "経費") == sum(agg.monthly_expenses(FROM, TO).values())


class TestMonthlyPl:
    def test_csv_vertical_format(self, svc, seeded):
        f = svc.generate("monthly-pl", FROM, TO, "csv")
        r = rows_of(f)
        assert r[0] == ["年月", "区分", "勘定科目", "金額"]
        assert r[1:] == [
            ["2026-08", "売上", "", "27500"],
            ["2026-08", "経費", "通信費", "700"],
            ["2026-08", "経費", "雑費", "500"],
            ["2026-08", "経費合計", "", "1200"],
            ["2026-08", "損益", "", "26300"],
            ["2026-09", "売上", "", "11000"],
            ["2026-09", "経費", "通信費", "3000"],
            ["2026-09", "経費合計", "", "3000"],
            ["2026-09", "損益", "", "8000"],
        ]
        assert f.record_count == 2
        assert f.filename == "月次損益集計レポート_202608-202609.csv"

    def test_empty_months_are_zero_filled_and_count_zero(self, svc):
        f = svc.generate("monthly-pl", "2026-01-01", "2026-02-28", "csv")
        r = rows_of(f)
        assert r[1:] == [
            ["2026-01", "売上", "", "0"], ["2026-01", "経費合計", "", "0"], ["2026-01", "損益", "", "0"],
            ["2026-02", "売上", "", "0"], ["2026-02", "経費合計", "", "0"], ["2026-02", "損益", "", "0"],
        ]
        assert f.record_count == 0

    def test_negative_profit_is_output_as_negative_number(self, svc, db_session):
        db_session.add(Expense(expense_date="2026-01-05", account_category="雑費", amount=12000, tax_category="STANDARD_10",
                               created_at=now_iso(), updated_at=now_iso()))
        db_session.commit()
        r = rows_of(svc.generate("monthly-pl", "2026-01-01", "2026-01-31", "csv"))
        assert ["2026-01", "損益", "", "-12000"] in r

    def test_pdf(self, svc, seeded):
        f = svc.generate("monthly-pl", FROM, TO, "pdf")
        assert f.content.startswith(b"%PDF")
        assert f.content_type == "application/pdf"
        assert f.filename == "月次損益集計レポート_202608-202609.pdf"
        assert f.record_count == 2

    def test_pdf_empty_data(self, svc):
        f = svc.generate("monthly-pl", "2026-01-01", "2026-02-28", "pdf")
        assert f.content.startswith(b"%PDF") and f.record_count == 0

    def test_pdf_render_receives_expected_data(self, seeded, db_session):
        captured = {}

        class Spy(PdfGenerationService):
            def render_monthly_pl_report_pdf(self, report):
                captured["report"] = report
                return b"%PDF-spy"

        service = build_report_service(db_session, pdf_service=Spy(CompanyProfileRepository(db_session)))
        service.generate("monthly-pl", FROM, TO, "pdf")
        report = captured["report"]
        assert [m.month for m in report.months] == ["2026-08", "2026-09"]
        assert report.total_sales == 38500 and report.total_expense == 4200 and report.total_profit == 34300
        assert dict(report.category_totals) == {"通信費": 3700, "雑費": 500}

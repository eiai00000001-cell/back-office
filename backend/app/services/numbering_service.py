"""採番ロジック(詳細設計書4.1.1)。請求書番号・見積書番号は別カウンタ。"""
from datetime import date
from typing import Literal

from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.quote_repository import QuoteRepository

Target = Literal["invoice", "quote"]


class NumberingService:
    def __init__(self, invoice_repository: InvoiceRepository, quote_repository: QuoteRepository):
        self.invoice_repository = invoice_repository
        self.quote_repository = quote_repository

    def generate_number(self, target: Target) -> str:
        year = date.today().year
        if target == "invoice":
            max_seq = self.invoice_repository.max_number_seq(year)
        elif target == "quote":
            max_seq = self.quote_repository.max_number_seq(year)
        else:
            raise ValueError(f"unknown numbering target: {target}")
        next_seq = max_seq + 1
        return f"{year}-{next_seq:04d}"
